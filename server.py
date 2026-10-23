"""Server thống nhất cho ba game ôn tập (chỉ dùng thư viện chuẩn).

Chạy:  python server.py
  rồi mở http://localhost:8000

- Matching:     http://localhost:8000/matching.html
- Fill Blank:   http://localhost:8000/fill_blank.html
- Quiz:         http://localhost:8000/quiz.html
"""
import json
import html
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from games import matching, fill_blank, quiz, final_test

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
WEB_DIR = ROOT / "web"

# game_id -> instance (lưu trong RAM)
MATCHING_GAMES: dict[str, matching.MatchingGame] = {}
FILL_GAMES: dict[str, fill_blank.FillBlankGame] = {}
QUIZ_GAMES: dict[str, quiz.EnglishQuizGame] = {}
FINAL_TEST_GAMES: dict[str, quiz.EnglishQuizGame] = {}
FLOW_LOCK = threading.Lock()
FLOW_STATE = {
    "fill_blank_done": False,
    "matching_done": False,
    "quiz_done": False,
    "final_test_done": False,
}
FLOW_CHAPTER: dict | None = None
FLOW_RESULTS: dict[str, dict] = {}
ACTIVE_FILL_GAME_ID: str | None = None
ACTIVE_MATCHING_GAME_ID: str | None = None
ACTIVE_QUIZ_GAME_ID: str | None = None
ACTIVE_FINAL_TEST_GAME_ID: str | None = None
ACTIVE_MATCHING_REVIEW_ONLY = False
ACTIVE_QUIZ_REVIEW_ONLY = False
ACTIVE_FINAL_TEST_ITEMS: dict[str, dict] = {}


def _record_flow_part(game_name: str, data: dict) -> dict:
    """Merge one selected game source into the current single-user chapter."""
    global FLOW_CHAPTER
    if not isinstance(data, dict):
        raise ValueError("Dữ liệu chương không đúng định dạng.")
    subject = data.get("subject")
    title = data.get("chapter_title")
    if not isinstance(subject, str) or not subject.strip():
        raise ValueError("Dữ liệu thiếu subject hợp lệ.")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Dữ liệu thiếu chapter_title hợp lệ.")
    part = next(
        (part for part in data.get("parts", []) if isinstance(part, dict) and part.get("game") == game_name),
        None,
    )
    if part is None:
        raise ValueError(f"Không tìm thấy phần '{game_name}' trong dữ liệu.")
    with FLOW_LOCK:
        if FLOW_CHAPTER is None or game_name == "fill_blank":
            chapter = {"subject": subject, "chapter_title": title, "parts": []}
        else:
            chapter = FLOW_CHAPTER
            if chapter["subject"] != subject or chapter["chapter_title"] != title:
                raise ValueError("Các game phải dùng cùng môn học và chương.")
            chapter = {**chapter, "parts": list(chapter["parts"])}
        chapter["parts"] = [existing for existing in chapter["parts"] if existing.get("game") != game_name]
        chapter["parts"].append(part)
        FLOW_CHAPTER = chapter
        return chapter


# ---------- Matching ----------
def matching_sample_files() -> list[str]:
    return sorted(p.name for p in DATA_DIR.glob("*matching*.json"))


def quiz_sample_files() -> list[str]:
    return sorted(p.name for p in DATA_DIR.glob("*quiz*.json"))


def _require_matching_unlocked() -> None:
    with FLOW_LOCK:
        if not FLOW_STATE["fill_blank_done"]:
            raise ValueError("Bạn cần hoàn thành game điền chỗ trống trước.")


def _require_quiz_unlocked() -> None:
    with FLOW_LOCK:
        if not FLOW_STATE["matching_done"]:
            raise ValueError("Bạn cần hoàn thành game nối từ trước.")


def matching_api_new(body: dict) -> dict:
    """Tạo ván mới từ file mẫu {file} hoặc JSON tải lên {data}; only_ids = ôn lại câu sai."""
    global ACTIVE_MATCHING_GAME_ID, ACTIVE_MATCHING_REVIEW_ONLY
    global ACTIVE_QUIZ_GAME_ID, ACTIVE_QUIZ_REVIEW_ONLY, ACTIVE_FINAL_TEST_GAME_ID
    _require_matching_unlocked()
    if "data" in body:
        data = body["data"]
    else:
        name = body.get("file")
        if name not in matching_sample_files():
            raise ValueError("File không tồn tại.")
        data = json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
    items = matching.get_matching_items(data)
    if body.get("only_ids"):
        items = [it for it in items if it["id"] in body["only_ids"]]
    game = matching.MatchingGame(items)
    if not body.get("only_ids"):
        _record_flow_part("matching", data)
    if len(MATCHING_GAMES) > 200:
        MATCHING_GAMES.pop(next(iter(MATCHING_GAMES)))
    MATCHING_GAMES[game.id] = game
    review_only = bool(body.get("only_ids"))
    with FLOW_LOCK:
        ACTIVE_MATCHING_GAME_ID = game.id
        ACTIVE_MATCHING_REVIEW_ONLY = review_only
        if not review_only:
            FLOW_STATE["matching_done"] = False
            FLOW_STATE["quiz_done"] = False
            FLOW_STATE["final_test_done"] = False
            ACTIVE_QUIZ_GAME_ID = None
            ACTIVE_QUIZ_REVIEW_ONLY = False
            ACTIVE_FINAL_TEST_GAME_ID = None
            FLOW_RESULTS.pop("matching", None)
            FLOW_RESULTS.pop("quiz", None)
            FLOW_RESULTS.pop("final_test", None)
    return {
        **game.public_view(),
        "title": data.get("chapter_title", ""),
        "subject": data.get("subject", ""),
    }


def matching_api_check(body: dict) -> dict:
    _require_matching_unlocked()
    game = MATCHING_GAMES.get(body.get("game_id"))
    if game is None:
        raise ValueError("Ván chơi không còn tồn tại, hãy tải lại trang.")
    with FLOW_LOCK:
        if game.id != ACTIVE_MATCHING_GAME_ID:
            raise ValueError("Ván nối từ đã hết hiệu lực, hãy tải lại trang.")
    result = game.check(body.get("pairs"))
    with FLOW_LOCK:
        if game.id == ACTIVE_MATCHING_GAME_ID and not ACTIVE_MATCHING_REVIEW_ONLY:
            FLOW_STATE["matching_done"] = True
            FLOW_RESULTS["matching"] = result
    return result


# ---------- Quiz ----------
def quiz_api_new(body: dict) -> dict:
    """Tạo ván quiz từ file mẫu {file} hoặc JSON tải lên {data}."""
    global ACTIVE_QUIZ_GAME_ID, ACTIVE_QUIZ_REVIEW_ONLY, ACTIVE_FINAL_TEST_GAME_ID
    _require_quiz_unlocked()
    if "data" in body:
        data = body["data"]
    else:
        name = body.get("file")
        if name not in quiz_sample_files():
            raise ValueError("File trắc nghiệm không tồn tại.")
        data = json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
    items = quiz.get_quiz_items(data)
    only_ids = body.get("only_ids")
    if only_ids:
        items = [item for item in items if item["id"] in only_ids]
    game = quiz.EnglishQuizGame(items)
    if not only_ids:
        _record_flow_part("quiz", data)
    if len(QUIZ_GAMES) > 200:
        QUIZ_GAMES.pop(next(iter(QUIZ_GAMES)))
    QUIZ_GAMES[game.id] = game
    review_only = bool(only_ids)
    with FLOW_LOCK:
        ACTIVE_QUIZ_GAME_ID = game.id
        ACTIVE_QUIZ_REVIEW_ONLY = review_only
        if not review_only:
            FLOW_STATE["quiz_done"] = False
            FLOW_STATE["final_test_done"] = False
            ACTIVE_FINAL_TEST_GAME_ID = None
            FLOW_RESULTS.pop("quiz", None)
            FLOW_RESULTS.pop("final_test", None)
    return {**game.public_view(), "title": data.get("chapter_title", "Quiz"),
            "subject": data.get("subject", "")}


def quiz_api_check(body: dict) -> dict:
    _require_quiz_unlocked()
    game = QUIZ_GAMES.get(body.get("game_id"))
    if game is None:
        raise ValueError("Ván chơi không còn tồn tại, hãy tải lại trang.")
    with FLOW_LOCK:
        if game.id != ACTIVE_QUIZ_GAME_ID:
            raise ValueError("Ván trắc nghiệm đã hết hiệu lực, hãy tải lại trang.")
    return game.check_one(body.get("qid"), body.get("idx"))


def quiz_api_result(body: dict) -> dict:
    _require_quiz_unlocked()
    game = QUIZ_GAMES.get(body.get("game_id"))
    if game is None:
        raise ValueError("Ván chơi không còn tồn tại, hãy tải lại trang.")
    result = game.result()
    with FLOW_LOCK:
        if game.id == ACTIVE_QUIZ_GAME_ID and not ACTIVE_QUIZ_REVIEW_ONLY:
            FLOW_STATE["quiz_done"] = True
            FLOW_RESULTS["quiz"] = result
    return result


# ---------- Final Test ----------
def _require_final_test_unlocked() -> None:
    with FLOW_LOCK:
        if not FLOW_STATE["quiz_done"]:
            raise ValueError("Bạn cần hoàn thành cả ba game trước.")


def final_test_api_new(body: dict | None = None) -> dict:
    """Create the final quiz from the three source parts in the active chapter."""
    global ACTIVE_FINAL_TEST_GAME_ID, ACTIVE_FINAL_TEST_ITEMS
    _require_final_test_unlocked()
    with FLOW_LOCK:
        chapter = FLOW_CHAPTER
    if chapter is None:
        raise ValueError("Không có dữ liệu chương cho bài kiểm tra cuối.")
    items = final_test.build_final_quiz(chapter)
    game = quiz.EnglishQuizGame(items, allow_variable_options=True)
    if len(FINAL_TEST_GAMES) > 200:
        FINAL_TEST_GAMES.pop(next(iter(FINAL_TEST_GAMES)))
    FINAL_TEST_GAMES[game.id] = game
    with FLOW_LOCK:
        ACTIVE_FINAL_TEST_GAME_ID = game.id
        ACTIVE_FINAL_TEST_ITEMS = {item["id"]: item for item in items}
        FLOW_STATE["final_test_done"] = False
        FLOW_RESULTS.pop("final_test", None)
    return {
        **game.public_view(),
        "title": chapter["chapter_title"],
        "subject": chapter["subject"],
    }


def final_test_api_check(body: dict) -> dict:
    _require_final_test_unlocked()
    game = FINAL_TEST_GAMES.get(body.get("game_id"))
    if game is None:
        raise ValueError("Ván kiểm tra cuối không còn tồn tại, hãy tải lại trang.")
    with FLOW_LOCK:
        if game.id != ACTIVE_FINAL_TEST_GAME_ID:
            raise ValueError("Ván kiểm tra cuối đã hết hiệu lực, hãy tải lại trang.")
    return game.check_one(body.get("qid"), body.get("idx"))


def final_test_api_result(body: dict) -> dict:
    _require_final_test_unlocked()
    game = FINAL_TEST_GAMES.get(body.get("game_id"))
    if game is None:
        raise ValueError("Ván kiểm tra cuối không còn tồn tại, hãy tải lại trang.")
    result = game.result()
    with FLOW_LOCK:
        if game.id != ACTIVE_FINAL_TEST_GAME_ID:
            raise ValueError("Ván kiểm tra cuối đã hết hiệu lực, hãy tải lại trang.")
        for review in result["review"]:
            source = ACTIVE_FINAL_TEST_ITEMS[review["id"]]
            review["source_game"] = source["source_game"]
            review["source_id"] = source["source_id"]
        result["grade_10"] = final_test.calculate_grade_10(result["score"], result["total"])
        FLOW_STATE["final_test_done"] = True
        FLOW_RESULTS["final_test"] = result
    return result


# ---------- Fill Blank ----------
def fill_sample_files() -> list[str]:
    """Các file *fill_blank*.json trong data/ (kể cả thư mục con), trả về đường dẫn tương đối."""
    return sorted(
        p.relative_to(DATA_DIR).as_posix()
        for p in DATA_DIR.rglob("*fill_blank*.json")
    )


def fill_api_new(body: dict) -> dict:
    """Tạo ván mới từ file mẫu {file} hoặc JSON tải lên {data}; only_ids = ôn lại câu sai."""
    global ACTIVE_FILL_GAME_ID
    if "data" in body:
        data = body["data"]
    else:
        name = body.get("file")
        if name not in fill_sample_files():
            raise ValueError("File không tồn tại.")
        data = json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
    items = fill_blank.get_fill_items(data)
    if body.get("only_ids"):
        items = [it for it in items if it["id"] in body["only_ids"]]
    game = fill_blank.FillBlankGame(items)
    if not body.get("only_ids"):
        _record_flow_part("fill_blank", data)
    if len(FILL_GAMES) > 200:
        FILL_GAMES.pop(next(iter(FILL_GAMES)))
    FILL_GAMES[game.id] = game
    with FLOW_LOCK:
        if not body.get("only_ids"):
            FLOW_STATE["fill_blank_done"] = False
            FLOW_STATE["matching_done"] = False
            FLOW_STATE["quiz_done"] = False
            FLOW_STATE["final_test_done"] = False
            ACTIVE_FILL_GAME_ID = game.id
            global ACTIVE_MATCHING_GAME_ID, ACTIVE_QUIZ_GAME_ID
            global ACTIVE_MATCHING_REVIEW_ONLY, ACTIVE_QUIZ_REVIEW_ONLY
            global ACTIVE_FINAL_TEST_GAME_ID, ACTIVE_FINAL_TEST_ITEMS
            ACTIVE_MATCHING_GAME_ID = None
            ACTIVE_QUIZ_GAME_ID = None
            ACTIVE_FINAL_TEST_GAME_ID = None
            ACTIVE_FINAL_TEST_ITEMS = {}
            ACTIVE_MATCHING_REVIEW_ONLY = False
            ACTIVE_QUIZ_REVIEW_ONLY = False
            FLOW_RESULTS.clear()
    return {
        **game.public_view(),
        "title": data.get("chapter_title", ""),
        "subject": data.get("subject", ""),
    }


def _fill_game(body: dict) -> fill_blank.FillBlankGame:
    game = FILL_GAMES.get(body.get("game_id"))
    if game is None:
        raise ValueError("Ván chơi không còn tồn tại, hãy tải lại trang.")
    return game


def fill_api_check(body: dict) -> dict:
    return _fill_game(body).check_one(body.get("qid"), body.get("idx"))


def fill_api_result(body: dict) -> dict:
    game = _fill_game(body)
    result = game.result()
    with FLOW_LOCK:
        if game.id == ACTIVE_FILL_GAME_ID:
            FLOW_STATE["fill_blank_done"] = True
            FLOW_RESULTS["fill_blank"] = result
    return result


# ---------- HTTP Handler ----------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send(self, code: int, body, ctype="application/json; charset=utf-8"):
        raw = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_file(self, path: Path, ctype: str):
        if not path.is_file():
            return self._send(404, {"error": "Not found"})
        self._send(200, path.read_bytes(), ctype)

    def _redirect(self, location: str):
        self.send_response(303)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path in ("/", "/index.html"):
            with FLOW_LOCK:
                if FLOW_STATE["final_test_done"]:
                    rows = []
                    for key, label in (
                        ("fill_blank", "Điền chỗ trống"),
                        ("matching", "Nối từ"),
                        ("quiz", "Trắc nghiệm"),
                        ("final_test", "Bài kiểm tra cuối"),
                    ):
                        result = FLOW_RESULTS.get(key)
                        if result:
                            value = (
                                f'{result["grade_10"]:.2f}/10'
                                if key == "final_test"
                                else f'{result["score"]}/{result["total"]}'
                            )
                            rows.append(f"<li>{label}: {value}</li>")
                    wrong_rows = []
                    final_result = FLOW_RESULTS.get("final_test", {})
                    for review in final_result.get("review", []):
                        if not review["ok"]:
                            source = html.escape(
                                f'{review["source_game"]} / {review["source_id"]}'
                            )
                            wrong_rows.append(f"<li>{source}</li>")
                    summary = (
                        "<!doctype html><html lang='vi'><meta charset='utf-8'>"
                        "<title>Tổng kết</title><body><h1>Hoàn thành lượt ôn tập!</h1>"
                        "<h2>Kết quả</h2><ul>" + "".join(rows) + "</ul>"
                        "<h2>Câu sai trong bài kiểm tra cuối</h2><ul>"
                        + ("".join(wrong_rows) or "<li>Không có câu sai.</li>")
                        + "</ul></body></html>"
                    )
                    return self._send(200, summary.encode("utf-8"), "text/html; charset=utf-8")
                if FLOW_STATE["quiz_done"]:
                    next_game = "final_test"
                else:
                    next_game = (
                        "quiz" if FLOW_STATE["matching_done"]
                        else "matching" if FLOW_STATE["fill_blank_done"]
                        else "fill_blank"
                    )
            return self._redirect(f"/{next_game}.html")

        if path == "/matching.html":
            try:
                _require_matching_unlocked()
            except ValueError:
                return self._redirect("/")
            return self._send_file(WEB_DIR / "matching.html", "text/html; charset=utf-8")
        if path == "/quiz.html":
            try:
                _require_quiz_unlocked()
            except ValueError:
                return self._redirect("/")
            return self._send_file(WEB_DIR / "quiz.html", "text/html; charset=utf-8")
        if path == "/final_test.html":
            try:
                _require_final_test_unlocked()
            except ValueError:
                return self._redirect("/")
            return self._send_file(WEB_DIR / "final_test.html", "text/html; charset=utf-8")
        if path in ("/fill_blank.html", "/fill_blank"):
            return self._send_file(WEB_DIR / "fill_blank.html", "text/html; charset=utf-8")

        if path == "/api/matching/files":
            return self._send(200, {"files": matching_sample_files()})
        if path == "/api/quiz/files":
            return self._send(200, {"files": quiz_sample_files()})
        if path == "/api/fill_blank/files":
            return self._send(200, {"files": fill_sample_files()})
        # Tương thích cũ: /api/files — suy ra loại game từ Referer
        if path == "/api/files":
            ref = self.headers.get("Referer", "")
            if "fill_blank" in ref:
                return self._send(200, {"files": fill_sample_files()})
            if "matching" in ref:
                return self._send(200, {"files": matching_sample_files()})
            return self._send(200, {
                "matching": matching_sample_files(),
                "fill_blank": fill_sample_files(),
            })

        self._send(404, {"error": "Not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        routes = {
            "/api/matching/new": matching_api_new,
            "/api/matching/check": matching_api_check,
            "/api/quiz/new": quiz_api_new,
            "/api/quiz/check": quiz_api_check,
            "/api/quiz/result": quiz_api_result,
            "/api/final_test/new": final_test_api_new,
            "/api/final_test/check": final_test_api_check,
            "/api/final_test/result": final_test_api_result,
            "/api/fill_blank/new": fill_api_new,
            "/api/fill_blank/check": fill_api_check,
            "/api/fill_blank/result": fill_api_result,
        }
        if path not in routes:
            return self._send(404, {"error": "Not found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            self._send(200, routes[path](body))
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            self._send(400, {"error": str(e)})


if __name__ == "__main__":
    host, port = "127.0.0.1", 8000
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Edu Game server: http://{host}:{port}")
    print(f"  - Trang chủ:   http://{host}:{port}/")
    print(f"  - Matching:    http://{host}:{port}/matching.html")
    print(f"  - Fill Blank:  http://{host}:{port}/fill_blank.html")
    print(f"  - Quiz:        http://{host}:{port}/quiz.html")
    print("  (Ctrl+C để dừng)")
    try:
        webbrowser.open(f"http://{host}:{port}/")
    except Exception:
        pass
    server.serve_forever()
