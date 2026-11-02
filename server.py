"""HTTP server for the four educational games, backed by SQLite."""
from __future__ import annotations

import html
import json
import os
import secrets
import threading
import time
import webbrowser
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from attempt_manager import AttemptManager, default_database_path
from games import final_test, fill_blank, matching, quiz

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
WEB_DIR = ROOT / "web"
SESSION_COOKIE = "edu_game_session"
SESSION_COOKIE_MAX_AGE = 30 * 24 * 60 * 60
MAX_REQUEST_BODY_BYTES = 2 * 1024 * 1024


def _environment_flag(name: str, default: bool | None) -> bool | None:
    value = os.environ.get(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in ("1", "true", "yes", "on"):
        return True
    if normalized in ("0", "false", "no", "off"):
        return False
    raise RuntimeError(f"{name} must be a boolean value.")


def _requests_per_minute() -> int:
    value = os.environ.get("EDUGAME_MAX_REQUESTS_PER_MINUTE", "120")
    try:
        limit = int(value)
    except ValueError as error:
        raise RuntimeError("EDUGAME_MAX_REQUESTS_PER_MINUTE must be a positive integer.") from error
    if limit < 1:
        raise RuntimeError("EDUGAME_MAX_REQUESTS_PER_MINUTE must be a positive integer.")
    return limit


TRUST_PROXY = bool(_environment_flag("EDUGAME_TRUST_PROXY", False))
SECURE_COOKIE = _environment_flag("EDUGAME_COOKIE_SECURE", None)
MAX_REQUESTS_PER_MINUTE = _requests_per_minute()
manager = AttemptManager(default_database_path(ROOT))

# These compatibility views are used by the original in-process unit tests.
# HTTP requests always load and commit game state through SQLite.
MATCHING_GAMES: dict[str, matching.MatchingGame] = {}
FILL_GAMES: dict[str, fill_blank.FillBlankGame] = {}
QUIZ_GAMES: dict[str, quiz.EnglishQuizGame] = {}
FINAL_TEST_GAMES: dict[str, quiz.EnglishQuizGame] = {}
FLOW_STATE = {"fill_blank_done": False, "matching_done": False,
              "quiz_done": False, "final_test_done": False}
FLOW_CHAPTER: dict | None = None
FLOW_RESULTS: dict[str, dict] = {}
ACTIVE_FILL_GAME_ID: str | None = None
ACTIVE_MATCHING_GAME_ID: str | None = None
ACTIVE_QUIZ_GAME_ID: str | None = None
ACTIVE_FINAL_TEST_GAME_ID: str | None = None
ACTIVE_MATCHING_REVIEW_ONLY = False
ACTIVE_QUIZ_REVIEW_ONLY = False
ACTIVE_FINAL_TEST_ITEMS: dict[str, dict] = {}
_direct_session_id: str | None = None


class RequestRateLimiter:
    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = {}
        self._last_cleanup = time.monotonic()
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            requests = self._requests.setdefault(key, deque())
            while requests and requests[0] <= cutoff:
                requests.popleft()
            if now - self._last_cleanup >= self.window_seconds:
                for stale_key, timestamps in list(self._requests.items()):
                    while timestamps and timestamps[0] <= cutoff:
                        timestamps.popleft()
                    if not timestamps:
                        del self._requests[stale_key]
                self._last_cleanup = now
                requests = self._requests.setdefault(key, deque())
            if len(requests) >= self.limit:
                return False
            requests.append(now)
            return True


request_limiter = RequestRateLimiter(MAX_REQUESTS_PER_MINUTE)


class RequestTooLargeError(ValueError):
    pass


def configure_database(path: str | Path) -> None:
    """Replace the repository implementation, primarily for isolated test databases."""
    global manager
    manager = AttemptManager(path)


def reset_for_tests() -> str:
    """Create an isolated owner session for direct API-level tests."""
    global _direct_session_id, FLOW_CHAPTER, ACTIVE_FILL_GAME_ID
    global ACTIVE_MATCHING_GAME_ID, ACTIVE_QUIZ_GAME_ID, ACTIVE_FINAL_TEST_GAME_ID
    global ACTIVE_FINAL_TEST_ITEMS, ACTIVE_MATCHING_REVIEW_ONLY, ACTIVE_QUIZ_REVIEW_ONLY
    manager.reset()
    MATCHING_GAMES.clear()
    FILL_GAMES.clear()
    QUIZ_GAMES.clear()
    FINAL_TEST_GAMES.clear()
    FLOW_STATE.update(fill_blank_done=False, matching_done=False,
                      quiz_done=False, final_test_done=False)
    FLOW_RESULTS.clear()
    FLOW_CHAPTER = None
    ACTIVE_FILL_GAME_ID = None
    ACTIVE_MATCHING_GAME_ID = None
    ACTIVE_QUIZ_GAME_ID = None
    ACTIVE_FINAL_TEST_GAME_ID = None
    ACTIVE_FINAL_TEST_ITEMS = {}
    ACTIVE_MATCHING_REVIEW_ONLY = False
    ACTIVE_QUIZ_REVIEW_ONLY = False
    _direct_session_id = create_session()
    return _direct_session_id


def create_session() -> str:
    with manager.transaction() as db:
        return manager.create_session(db, secrets.token_hex(32))


def _session(session_id: str | None) -> str:
    resolved = session_id or _direct_session_id
    if not resolved:
        raise PermissionError("Phiên không hợp lệ hoặc đã hết hạn.")
    return resolved


def _json(value) -> dict:
    if isinstance(value, str):
        return json.loads(value)
    return value


def _flow(row) -> tuple[dict, dict]:
    chapter = _json(row["chapter_json"])
    flow = _json(row["flow_json"])
    return chapter, flow


def _sync_compat(chapter: dict | None, flow: dict) -> None:
    global FLOW_CHAPTER, ACTIVE_FILL_GAME_ID, ACTIVE_MATCHING_GAME_ID
    global ACTIVE_QUIZ_GAME_ID, ACTIVE_FINAL_TEST_GAME_ID
    if _direct_session_id is None:
        return
    FLOW_CHAPTER = chapter
    for kind, done in flow["done"].items():
        FLOW_STATE[f"{kind}_done"] = done
    FLOW_RESULTS.clear()
    FLOW_RESULTS.update(flow["results"])
    ACTIVE_FILL_GAME_ID = flow["games"].get("fill_blank")
    ACTIVE_MATCHING_GAME_ID = flow["games"].get("matching")
    ACTIVE_QUIZ_GAME_ID = flow["games"].get("quiz")
    ACTIVE_FINAL_TEST_GAME_ID = flow["games"].get("final_test")


def _resolve(db, session_id: str, attempt_id: str | None = None):
    session = manager.get_session(db, session_id)
    if session is None:
        raise PermissionError("Phiên không hợp lệ hoặc đã hết hạn.")
    attempt = manager.owned_attempt(db, session_id, attempt_id)
    chapter, flow = _flow(attempt)
    return attempt, chapter, flow


def _new_attempt(db, session_id: str, chapter: dict | None = None):
    session = manager.get_session(db, session_id)
    if session is None:
        raise PermissionError("Phiên không hợp lệ hoặc đã hết hạn.")
    attempt_id = manager.create_attempt(db, session_id, chapter)
    attempt = manager.owned_attempt(db, session_id, attempt_id)
    return attempt, *_flow(attempt)


def _chapter_part(data: dict, game_name: str) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Dữ liệu chương không đúng định dạng.")
    subject, title = data.get("subject"), data.get("chapter_title")
    if not isinstance(subject, str) or not subject.strip():
        raise ValueError("Dữ liệu thiếu subject hợp lệ.")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Dữ liệu thiếu chapter_title hợp lệ.")
    parts = data.get("parts")
    part = next((p for p in parts or [] if isinstance(p, dict) and p.get("game") == game_name), None)
    if part is None:
        raise ValueError(f"Không tìm thấy phần '{game_name}' trong dữ liệu.")
    return part


def _merge_part(chapter: dict | None, data: dict, game_name: str) -> dict:
    part = _chapter_part(data, game_name)
    subject, title = data["subject"].strip(), data["chapter_title"].strip()
    if chapter is None:
        chapter = {"subject": subject, "chapter_title": title, "parts": []}
    elif chapter["subject"] != subject or chapter["chapter_title"] != title:
        raise ValueError("Các game phải dùng cùng môn học và chương.")
    parts = [p for p in chapter["parts"] if p.get("game") != game_name]
    parts.append(part)
    return {**chapter, "parts": parts}


def _read_game_state(db, attempt_id: str, game_id: str, kind: str):
    row = manager.load_game(db, attempt_id, game_id, kind)
    return row, json.loads(row["state_json"])


def _restore_game(kind: str, state: dict):
    if kind == "fill_blank":
        cls = fill_blank.FillBlankGame
        cache = FILL_GAMES
    elif kind == "matching":
        cls = matching.MatchingGame
        cache = MATCHING_GAMES
    else:
        cls = quiz.EnglishQuizGame
        cache = FINAL_TEST_GAMES if kind == "final_test" else QUIZ_GAMES
    game = cls.__new__(cls)
    game.id = state["id"]
    game.items = state["items"]
    game._check_lock = threading.Lock()
    if kind == "matching":
        game.order = state["order"]
        game._result = state.get("result")
    else:
        game.questions = state["questions"]
        game.chosen = state["chosen"]
        if kind != "fill_blank":
            game.allow_variable_options = state.get("allow_variable_options", False)
    if _direct_session_id is not None:
        cache[game.id] = game
    return game


def _game_state(kind: str, game, extra: dict | None = None) -> dict:
    state = {"id": game.id, "items": game.items}
    if kind == "matching":
        state.update(order=game.order, result=game._result)
    else:
        state.update(questions=game.questions, chosen=game.chosen)
        if kind != "fill_blank":
            state["allow_variable_options"] = getattr(game, "allow_variable_options", False)
    if extra:
        state.update(extra)
    return state


def _view(kind: str, game, attempt_id: str, chapter: dict, state: dict) -> dict:
    payload = game.public_view()
    payload.update({
        "attempt_id": attempt_id,
        "chapter_id": chapter.get("chapter_id"),
        "title": chapter.get("chapter_title", ""),
        "subject": chapter.get("subject", ""),
    })
    if kind in ("fill_blank", "quiz", "final_test"):
        progress = {}
        for question in game.questions:
            qid = question["id"]
            if qid in game.chosen:
                progress[qid] = {
                    "idx": game.chosen[qid],
                    "ok": game.chosen[qid] == question["correct"],
                    "correct_idx": question["correct"],
                    "correct_text": question["options"][question["correct"]],
                }
        payload["progress"] = progress
    if kind == "matching":
        payload["pairs"] = state.get("draft", {})
        if state.get("result"):
            payload["result"] = state["result"]
    return payload


def _ensure_chapter_id(chapter: dict) -> dict:
    if "chapter_id" not in chapter:
        chapter = {**chapter, "chapter_id": secrets.token_hex(16)}
    return chapter


def _sample_data(body: dict, game_name: str) -> dict:
    if "data" in body:
        data = body["data"]
    else:
        files = {
            "fill_blank": fill_sample_files,
            "matching": matching_sample_files,
            "quiz": quiz_sample_files,
        }[game_name]()
        name = body.get("file")
        if name not in files:
            raise ValueError("File không tồn tại.")
        data = json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
    _chapter_part(data, game_name)
    return data


def _start_game(kind: str, body: dict, session_id: str | None = None) -> dict:
    session_id = _session(session_id)
    only_ids = body.get("only_ids") or []
    with manager.transaction() as db:
        session = manager.get_session(db, session_id)
        if session is None:
            raise PermissionError("Phiên không hợp lệ hoặc đã hết hạn.")
        active_id = body.get("attempt_id")
        if not active_id and session_id == _direct_session_id:
            active_id = session["active_attempt_id"]
        if kind == "fill_blank":
            data = _sample_data(body, kind)
            option_items = fill_blank.get_fill_items(data)
            items = option_items
            if only_ids:
                items = [item for item in items if item["id"] in only_ids]
            if not active_id or body.get("restart"):
                attempt, chapter, flow = _new_attempt(db, session_id)
                chapter = _ensure_chapter_id(_merge_part(None, data, kind))
                manager.save_flow(db, attempt["id"], chapter, flow)
            else:
                attempt, chapter, flow = _resolve(db, session_id, active_id)
                if not only_ids and flow["games"].get(kind) and not body.get("restart"):
                    _, state = _read_game_state(db, attempt["id"], flow["games"][kind], kind)
                    game = _restore_game(kind, state)
                    _sync_compat(chapter, flow)
                    return _view(kind, game, attempt["id"], chapter, state)
                if not only_ids and body.get("restart"):
                    manager.delete_attempt_games(db, attempt["id"])
                    chapter = _ensure_chapter_id(_merge_part(None, data, kind))
                    flow = {"done": {k: False for k in ("fill_blank", "matching", "quiz", "final_test")},
                            "results": {}, "games": {}, "review_games": {}}
                elif not only_ids:
                    chapter = _ensure_chapter_id(_merge_part(chapter, data, kind))
            game = fill_blank.FillBlankGame(
                items, option_items=option_items if only_ids else None)
        else:
            if not active_id:
                if kind == "matching":
                    raise ValueError("Bạn cần hoàn thành game điền chỗ trống trước.")
                raise ValueError("Bạn cần hoàn thành game nối từ trước.")
            attempt, chapter, flow = _resolve(db, session_id, active_id)
            required = {"matching": "fill_blank", "quiz": "matching"}.get(kind)
            if required and not flow["done"][required]:
                raise ValueError(
                    "Bạn cần hoàn thành game điền chỗ trống trước."
                    if kind == "matching" else "Bạn cần hoàn thành game nối từ trước."
                )
            data = _sample_data(body, kind)
            if not only_ids and flow["games"].get(kind) and not body.get("restart"):
                _, current_state = _read_game_state(
                    db, attempt["id"], flow["games"][kind], kind)
                if (chapter.get("subject") != data.get("subject")
                        or chapter.get("chapter_title") != data.get("chapter_title")):
                    raise ValueError("Các game phải dùng cùng môn học và chương.")
                game = _restore_game(kind, current_state)
                _sync_compat(chapter, flow)
                return _view(kind, game, attempt["id"], chapter, current_state)
            items = (matching.get_matching_items(data) if kind == "matching"
                     else quiz.get_quiz_items(data))
            if only_ids:
                items = [item for item in items if item["id"] in only_ids]
            if kind == "matching":
                game = matching.MatchingGame(items)
            else:
                game = quiz.EnglishQuizGame(items)
            if not only_ids:
                chapter = _ensure_chapter_id(_merge_part(chapter, data, kind))
                downstream = ("quiz", "final_test") if kind == "matching" else ("final_test",)
                for later in downstream:
                    flow["done"][later] = False
                    flow["results"].pop(later, None)
                    old_id = flow["games"].pop(later, None)
                    if old_id:
                        manager.delete_game(db, old_id)

        review_only = bool(only_ids)
        if not review_only:
            flow["done"][kind] = False
            flow["results"].pop(kind, None)
            old_review = flow["review_games"].pop(kind, None)
            if old_review:
                manager.delete_game(db, old_review)
            previous = flow["games"].get(kind)
            if previous:
                manager.delete_game(db, previous)
        else:
            previous_review = flow["review_games"].get(kind)
            if previous_review:
                manager.delete_game(db, previous_review)
        state = _game_state(kind, game)
        _restore_game(kind, state)
        manager.store_game(db, attempt["id"], kind, state, review_only)
        if review_only:
            flow["review_games"][kind] = game.id
        else:
            flow["games"][kind] = game.id
        manager.save_flow(db, attempt["id"], chapter, flow)
        _sync_compat(chapter, flow)
        return _view(kind, game, attempt["id"], chapter, state)


def matching_sample_files() -> list[str]:
    return sorted(p.name for p in DATA_DIR.glob("*matching*.json"))


def quiz_sample_files() -> list[str]:
    return sorted(p.name for p in DATA_DIR.glob("*quiz*.json"))


def fill_sample_files() -> list[str]:
    return sorted(p.relative_to(DATA_DIR).as_posix()
                  for p in DATA_DIR.rglob("*fill_blank*.json"))


def fill_api_new(body: dict, session_id: str | None = None) -> dict:
    return _start_game("fill_blank", body, session_id)


def matching_api_new(body: dict, session_id: str | None = None) -> dict:
    return _start_game("matching", body, session_id)


def quiz_api_new(body: dict, session_id: str | None = None) -> dict:
    return _start_game("quiz", body, session_id)


def _final_test_result_payload(game) -> dict:
    """Build a complete, traceable final result before persisting completion.

    Both the final answer submission and the result endpoint use this payload,
    so the summary page works even when the browser never calls /result.
    """
    result = game.result()
    sources = {item["id"]: item for item in game.items}
    for review in result["review"]:
        source = sources[review["id"]]
        review["source_game"] = source["source_game"]
        review["source_id"] = source["source_id"]
    result["grade_10"] = final_test.calculate_grade_10(result["score"], result["total"])
    return result


def _check_game(kind: str, body: dict, session_id: str | None = None) -> dict:
    session_id = _session(session_id)
    with manager.transaction() as db:
        attempt, chapter, flow = _resolve(db, session_id, body.get("attempt_id"))
        row, state = _read_game_state(db, attempt["id"], body.get("game_id"), kind)
        active_id = (flow["review_games"].get(kind) if row["review_only"]
                     else flow["games"].get(kind))
        if active_id != body.get("game_id"):
            raise PermissionError("Ván chơi đã hết hiệu lực trong lượt ôn tập này.")
        game = _restore_game(kind, state)
        result = (game.check(body.get("pairs")) if kind == "matching"
                  else game.check_one(body.get("qid"), body.get("idx")))
        manager.update_game(db, game.id, _game_state(kind, game, {
            **({"draft": state.get("draft", {})} if kind == "matching" else {}),
        }))
        if not row["review_only"]:
            if kind == "matching":
                flow["done"][kind] = True
                flow["results"][kind] = result
            elif len(game.chosen) == len(game.questions):
                flow["done"][kind] = True
                flow["results"][kind] = (
                    _final_test_result_payload(game) if kind == "final_test"
                    else game.result()
                )
            manager.save_flow(db, attempt["id"], chapter, flow)
        _sync_compat(chapter, flow)
        return result


def fill_api_check(body: dict, session_id: str | None = None) -> dict:
    return _check_game("fill_blank", body, session_id)


def matching_api_check(body: dict, session_id: str | None = None) -> dict:
    return _check_game("matching", body, session_id)


def quiz_api_check(body: dict, session_id: str | None = None) -> dict:
    return _check_game("quiz", body, session_id)


def final_test_api_check(body: dict, session_id: str | None = None) -> dict:
    return _check_game("final_test", body, session_id)


def _game_result(kind: str, body: dict, session_id: str | None = None) -> dict:
    session_id = _session(session_id)
    with manager.transaction() as db:
        attempt, chapter, flow = _resolve(db, session_id, body.get("attempt_id"))
        row, state = _read_game_state(db, attempt["id"], body.get("game_id"), kind)
        active_id = (flow["review_games"].get(kind) if row["review_only"]
                     else flow["games"].get(kind))
        if active_id != body.get("game_id"):
            raise PermissionError("Ván chơi đã hết hiệu lực trong lượt ôn tập này.")
        game = _restore_game(kind, state)
        result = (_final_test_result_payload(game) if kind == "final_test"
                  else game.result())
        if not row["review_only"]:
            flow["done"][kind] = True
            flow["results"][kind] = result
            manager.save_flow(db, attempt["id"], chapter, flow)
        _sync_compat(chapter, flow)
        return result


def fill_api_result(body: dict, session_id: str | None = None) -> dict:
    return _game_result("fill_blank", body, session_id)


def quiz_api_result(body: dict, session_id: str | None = None) -> dict:
    return _game_result("quiz", body, session_id)


def final_test_api_result(body: dict, session_id: str | None = None) -> dict:
    return _game_result("final_test", body, session_id)


def final_test_api_new(body: dict | None = None, session_id: str | None = None) -> dict:
    session_id = _session(session_id)
    body = body or {}
    with manager.transaction() as db:
        session = manager.get_session(db, session_id)
        if session is None:
            raise PermissionError("Phiên không hợp lệ hoặc đã hết hạn.")
        if not session["active_attempt_id"] and session_id == _direct_session_id:
            raise ValueError("Bạn cần hoàn thành cả ba game trước.")
        attempt, chapter, flow = _resolve(db, session_id, body.get("attempt_id"))
        if not flow["done"]["quiz"]:
            raise ValueError("Bạn cần hoàn thành cả ba game trước.")
        if flow["done"]["final_test"]:
            raise ValueError("Bài kiểm tra đã hoàn thành; hãy xem tổng kết.")
        active_id = flow["games"].get("final_test")
        if active_id:
            _, state = _read_game_state(db, attempt["id"], active_id, "final_test")
            game = _restore_game("final_test", state)
            _sync_compat(chapter, flow)
            return _view("final_test", game, attempt["id"], chapter, state)
        items = final_test.build_final_quiz(chapter)
        game = quiz.EnglishQuizGame(items, allow_variable_options=True)
        state = _game_state("final_test", game)
        _restore_game("final_test", state)
        manager.store_game(db, attempt["id"], "final_test", state)
        flow["games"]["final_test"] = game.id
        manager.save_flow(db, attempt["id"], chapter, flow)
        _sync_compat(chapter, flow)
        return _view("final_test", game, attempt["id"], chapter, state)


def _save_matching_progress(body: dict, session_id: str) -> dict:
    with manager.transaction() as db:
        attempt, chapter, flow = _resolve(db, session_id, body.get("attempt_id"))
        row, state = _read_game_state(db, attempt["id"], body.get("game_id"), "matching")
        active_id = (flow["review_games"].get("matching") if row["review_only"]
                     else flow["games"].get("matching"))
        if active_id != body.get("game_id"):
            raise PermissionError("Ván nối từ đã hết hiệu lực trong lượt ôn tập này.")
        if row["review_only"]:
            state["draft"] = body.get("pairs", {})
        else:
            if not flow["done"]["fill_blank"]:
                raise ValueError("Bạn cần hoàn thành game điền chỗ trống trước.")
            state["draft"] = body.get("pairs", {})
        if not isinstance(state["draft"], dict):
            raise ValueError("Dữ liệu tiến độ nối từ không hợp lệ.")
        valid_ids = {item["id"] for item in state["items"]}
        values = list(state["draft"].values())
        if (not set(state["draft"]).issubset(valid_ids)
                or any(not isinstance(value, int) or isinstance(value, bool)
                       or not 0 <= value < len(state["order"]) for value in values)
                or len(values) != len(set(values))):
            raise ValueError("Dữ liệu tiến độ nối từ không hợp lệ.")
        manager.update_game(db, body["game_id"], state)
        _restore_game("matching", state)
        _sync_compat(chapter, flow)
        return {"saved": True}


def _session_state(session_id: str, attempt_id: str | None = None) -> dict:
    with manager.read_transaction() as db:
        session = manager.get_session(db, session_id)
        if session is None:
            raise PermissionError("Phiên không hợp lệ hoặc đã hết hạn.")
        selected_attempt_id = attempt_id
        if not selected_attempt_id and session_id == _direct_session_id:
            selected_attempt_id = session["active_attempt_id"]
        if not selected_attempt_id:
            return {"attempt": None}
        attempt, chapter, flow = _resolve(db, session_id, selected_attempt_id)
        # A newly-created attempt has no chapter until a game loads its data.
        chapter = chapter or {}
        current_games = {}
        review_games = {}
        for kind, game_id in flow["games"].items():
            _, state = _read_game_state(db, attempt["id"], game_id, kind)
            game = _restore_game(kind, state)
            current_games[kind] = _view(kind, game, attempt["id"], chapter, state)
        for kind, game_id in flow["review_games"].items():
            _, state = _read_game_state(db, attempt["id"], game_id, kind)
            game = _restore_game(kind, state)
            review_games[kind] = _view(kind, game, attempt["id"], chapter, state)
        _sync_compat(chapter, flow)
        return {
            "attempt": {
                "attempt_id": attempt["id"], "chapter_id": chapter.get("chapter_id"),
                "chapter_title": chapter.get("chapter_title"), "subject": chapter.get("subject"),
                "done": flow["done"], "results": flow["results"], "games": current_games,
                "review_games": review_games,
            }
        }


def _create_attempt(session_id: str, data: dict) -> dict:
    title = data.get("chapter_title", "")
    subject = data.get("subject", "")
    if title or subject:
        if not isinstance(title, str) or not title.strip() or not isinstance(subject, str) or not subject.strip():
            raise ValueError("Chương mới cần subject và chapter_title hợp lệ.")
        chapter = {"chapter_id": secrets.token_hex(16), "subject": subject,
                   "chapter_title": title, "parts": []}
    else:
        chapter = None
    with manager.transaction() as db:
        if manager.get_session(db, session_id) is None:
            raise PermissionError("Phiên không hợp lệ hoặc đã hết hạn.")
        attempt, chapter_data, _ = _new_attempt(db, session_id, chapter)
        return {"attempt_id": attempt["id"], "chapter_id":
                chapter_data.get("chapter_id") if chapter_data else None}


def _list_attempts(session_id: str) -> dict:
    with manager.read_transaction() as db:
        if manager.get_session(db, session_id) is None:
            raise PermissionError("Phiên không hợp lệ hoặc đã hết hạn.")
        rows = manager.list_attempts(db, session_id)
        return {"attempts": [{
            "attempt_id": row["id"],
            "chapter_id": (json.loads(row["chapter_json"]) or {}).get("chapter_id"),
            "chapter_title": (json.loads(row["chapter_json"]) or {}).get("chapter_title"),
            "subject": (json.loads(row["chapter_json"]) or {}).get("subject"),
            "done": json.loads(row["flow_json"])["done"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        } for row in rows]}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass

    def _secure_cookie(self) -> bool:
        if SECURE_COOKIE is not None:
            return SECURE_COOKIE
        return TRUST_PROXY and self.headers.get("X-Forwarded-Proto", "").lower() == "https"

    def _cookie_session(self) -> str | None:
        cookie = self.headers.get("Cookie", "")
        for segment in cookie.split(";"):
            name, separator, value = segment.strip().partition("=")
            if name == SESSION_COOKIE and separator:
                return value
        return None

    def _ensure_session(self) -> tuple[str, bool]:
        existing = self._cookie_session()
        with manager.transaction() as db:
            row = manager.get_session(db, existing)
            if row:
                return existing, False
            if existing:
                return "", False
            return manager.create_session(db), True

    def _send(self, code: int, body, ctype="application/json; charset=utf-8",
              set_cookie: str | None = None, extra_headers: dict[str, str] | None = None):
        raw = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        if set_cookie:
            secure = "; Secure" if self._secure_cookie() else ""
            self.send_header("Set-Cookie",
                             f"{SESSION_COOKIE}={set_cookie}; Path=/; HttpOnly; SameSite=Lax;"
                             f" Max-Age={SESSION_COOKIE_MAX_AGE}{secure}")
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(raw)

    def _send_file(self, path: Path, ctype: str):
        if not path.is_file():
            return self._send(404, {"error": "Not found"})
        return self._send(200, path.read_bytes(), ctype)

    def _redirect(self, location: str, cookie: str | None = None):
        self.send_response(303)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        if cookie:
            secure = "; Secure" if self._secure_cookie() else ""
            self.send_header("Set-Cookie",
                             f"{SESSION_COOKIE}={cookie}; Path=/; HttpOnly; SameSite=Lax;"
                             f" Max-Age={SESSION_COOKIE_MAX_AGE}{secure}")
        self.end_headers()

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query = parse_qs(parsed_url.query)
        requested_attempt_id = query.get("attempt_id", [None])[0]
        if path not in ("/", "/index.html", "/api/session",
                        "/api/attempts",
                        "/api/matching/files", "/api/quiz/files", "/api/fill_blank/files",
                        "/api/files") and not path.endswith(".html"):
            return self._send(404, {"error": "Not found"})
        session_id, created = self._ensure_session()
        if not session_id:
            return self._send(401, {"error": "Phiên không hợp lệ hoặc đã hết hạn."})
        cookie = session_id if created else None
        if path in ("/api/matching/files", "/api/files"):
            return self._send(200, {"files": matching_sample_files()}, set_cookie=cookie)
        if path == "/api/quiz/files":
            return self._send(200, {"files": quiz_sample_files()}, set_cookie=cookie)
        if path == "/api/fill_blank/files":
            return self._send(200, {"files": fill_sample_files()}, set_cookie=cookie)
        if path == "/api/session":
            try:
                state = _session_state(session_id, requested_attempt_id)
            except PermissionError as error:
                return self._send(403, {"error": str(error)}, set_cookie=cookie)
            return self._send(200, state, set_cookie=cookie)
        if path == "/api/attempts":
            try:
                attempts = _list_attempts(session_id)
            except PermissionError as error:
                return self._send(403, {"error": str(error)}, set_cookie=cookie)
            return self._send(200, attempts, set_cookie=cookie)
        if path in ("/", "/index.html"):
            if not requested_attempt_id:
                return self._redirect("/fill_blank.html", session_id if created else None)
            try:
                state = _session_state(session_id, requested_attempt_id)["attempt"]
            except PermissionError as error:
                return self._send(403, {"error": str(error)}, set_cookie=cookie)
            if state is None:
                return self._redirect("/fill_blank.html", session_id if created else None)
            if state["done"]["final_test"]:
                rows = []
                labels = {"fill_blank": "Điền chỗ trống", "matching": "Nối từ",
                          "quiz": "Trắc nghiệm", "final_test": "Bài kiểm tra cuối"}
                for key, result in state["results"].items():
                    score = (f'{result["grade_10"]:.2f}/10' if key == "final_test"
                             else f'{result["score"]}/{result["total"]}')
                    rows.append(f"<li>{labels[key]}: {score}</li>")
                wrong = []
                for review in state["results"]["final_test"].get("review", []):
                    if not review["ok"]:
                        source = html.escape(f'{review["source_game"]} / {review["source_id"]}')
                        wrong.append(f"<li>{source}</li>")
                page = ("<!doctype html><html lang='vi'><meta charset='utf-8'><title>Tổng kết</title>"
                        "<body><h1>Hoàn thành lượt ôn tập!</h1><h2>Kết quả</h2><ul>"
                        + "".join(rows) + "</ul><h2>Câu sai trong bài kiểm tra cuối</h2><ul>"
                        + ("".join(wrong) or "<li>Không có câu sai.</li>")
                        + "</ul></body></html>")
                return self._send(200, page.encode("utf-8"), "text/html; charset=utf-8",
                                  set_cookie=cookie)
            next_page = ("final_test" if state["done"]["quiz"] else
                         "quiz" if state["done"]["matching"] else
                         "matching" if state["done"]["fill_blank"] else "fill_blank")
            return self._redirect(
                f"/{next_page}.html?attempt_id={requested_attempt_id}",
                session_id if created else None)
        page = path.lstrip("/")
        if page not in ("fill_blank.html", "matching.html", "quiz.html", "final_test.html"):
            return self._send(404, {"error": "Not found"}, set_cookie=cookie)
        if page == "fill_blank.html" and requested_attempt_id:
            try:
                _session_state(session_id, requested_attempt_id)
            except PermissionError as error:
                return self._send(403, {"error": str(error)}, set_cookie=cookie)
        if page != "fill_blank.html":
            if not requested_attempt_id:
                return self._redirect("/fill_blank.html", session_id if created else None)
            try:
                attempt = _session_state(session_id, requested_attempt_id)["attempt"]
            except PermissionError as error:
                return self._send(403, {"error": str(error)}, set_cookie=cookie)
            if page == "final_test.html" and attempt and attempt["done"]["final_test"]:
                return self._redirect(
                    f"/?attempt_id={requested_attempt_id}", session_id if created else None)
            step = {"matching.html": "fill_blank", "quiz.html": "matching",
                    "final_test.html": "quiz"}[page]
            if attempt is None or not attempt["done"][step]:
                return self._redirect(
                    f"/?attempt_id={requested_attempt_id}", session_id if created else None)
        return self._send_file(WEB_DIR / page, "text/html; charset=utf-8") if not cookie else (
            self._send_file_with_cookie(WEB_DIR / page, cookie))

    def _send_file_with_cookie(self, path: Path, cookie: str):
        if not path.is_file():
            return self._send(404, {"error": "Not found"}, set_cookie=cookie)
        return self._send(200, path.read_bytes(), "text/html; charset=utf-8", set_cookie=cookie)

    def do_POST(self):
        session_id = self._cookie_session()
        rate_key = f"session:{session_id}" if session_id else f"ip:{self.client_address[0]}"
        if not request_limiter.allow(rate_key):
            return self._send(
                429, {"error": "Đã vượt quá số request cho phép. Vui lòng thử lại sau."},
                extra_headers={"Retry-After": "60"})
        if not session_id:
            return self._send(401, {"error": "Phiên không hợp lệ hoặc đã hết hạn."})
        try:
            transfer_encoding = self.headers.get("Transfer-Encoding", "").strip().lower()
            if transfer_encoding and transfer_encoding != "identity":
                raise ValueError("Transfer-Encoding không được hỗ trợ.")
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as error:
                raise ValueError("Content-Length không hợp lệ.") from error
            if length < 0:
                raise ValueError("Content-Length không hợp lệ.")
            if length > MAX_REQUEST_BODY_BYTES:
                raise RequestTooLargeError("Request vượt quá giới hạn kích thước cho phép.")
            raw_body = self.rfile.read(length)
            if len(raw_body) != length:
                raise ValueError("Request body không đầy đủ.")
            body = json.loads(raw_body or b"{}")
            if not isinstance(body, dict):
                raise ValueError("Request body phải là JSON object.")
            path = urlparse(self.path).path
            routes = {
                "/api/attempts/new": lambda: _create_attempt(session_id, body),
                "/api/fill_blank/new": lambda: fill_api_new(body, session_id),
                "/api/fill_blank/check": lambda: fill_api_check(body, session_id),
                "/api/fill_blank/result": lambda: fill_api_result(body, session_id),
                "/api/matching/new": lambda: matching_api_new(body, session_id),
                "/api/matching/check": lambda: matching_api_check(body, session_id),
                "/api/matching/progress": lambda: _save_matching_progress(body, session_id),
                "/api/quiz/new": lambda: quiz_api_new(body, session_id),
                "/api/quiz/check": lambda: quiz_api_check(body, session_id),
                "/api/quiz/result": lambda: quiz_api_result(body, session_id),
                "/api/final_test/new": lambda: final_test_api_new(body, session_id),
                "/api/final_test/check": lambda: final_test_api_check(body, session_id),
                "/api/final_test/result": lambda: final_test_api_result(body, session_id),
            }
            if path not in routes:
                return self._send(404, {"error": "Not found"})
            self._send(200, routes[path]())
        except RequestTooLargeError as error:
            self._send(413, {"error": str(error)})
        except PermissionError as error:
            self._send(403, {"error": str(error)})
        except LookupError as error:
            self._send(409, {"error": str(error)})
        except (ValueError, KeyError, TypeError, AttributeError) as error:
            self._send(400, {"error": str(error)})


if __name__ == "__main__":
    host, port = "127.0.0.1", 8000
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Edu Game server: http://{host}:{port}")
    print("  (Ctrl+C để dừng)")
    if os.environ.get("EDUGAME_NO_BROWSER") != "1":
        try:
            webbrowser.open(f"http://{host}:{port}/")
        except OSError:
            pass
    httpd.serve_forever()
