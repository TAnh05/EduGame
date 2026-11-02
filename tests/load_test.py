"""Reproducible end-to-end concurrent load test for the HTTP game flow."""
from __future__ import annotations

import argparse
from collections import Counter
import concurrent.futures
import ctypes
import http.client
import json
import math
import os
from pathlib import Path
import platform
import sqlite3
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import server


class Metrics:
    def __init__(self):
        self.lock = threading.Lock()
        self.latencies_ms: list[float] = []
        self.statuses: Counter[str] = Counter()
        self.request_failures = 0
        self.data_failures: list[str] = []

    def record_request(self, latency_ms: float, status: int | None):
        with self.lock:
            self.latencies_ms.append(latency_ms)
            self.statuses[str(status) if status is not None else "connection_error"] += 1
            if status is None or not 200 <= status < 300:
                self.request_failures += 1

    def record_data_failure(self, error: str):
        with self.lock:
            self.data_failures.append(error)


class LoadClient:
    def __init__(self, port: int, metrics: Metrics):
        self.port = port
        self.metrics = metrics
        self.cookie = ""

    def request(self, method: str, path: str, payload: dict | None = None):
        headers = {}
        body = None
        if self.cookie:
            headers["Cookie"] = self.cookie
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload)
        started = time.perf_counter()
        status = None
        connection = None
        try:
            connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            status = response.status
            raw = response.read()
            set_cookie = response.getheader("Set-Cookie")
            if set_cookie:
                self.cookie = set_cookie.split(";", 1)[0]
            content_type = response.getheader("Content-Type", "")
            data = json.loads(raw) if raw and "application/json" in content_type else raw
            connection.close()
            if not 200 <= status < 300:
                raise RuntimeError(f"{method} {path}: HTTP {status}: {data}")
            return data
        finally:
            if connection is not None:
                connection.close()
            self.metrics.record_request(
                (time.perf_counter() - started) * 1000, status)

    def get(self, path: str):
        return self.request("GET", path)

    def post(self, path: str, payload: dict):
        return self.request("POST", path, payload)


def _require(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


def play_one_client(port: int, metrics: Metrics) -> dict:
    client = LoadClient(port, metrics)
    client.get("/api/session")
    attempt_id = client.post("/api/attempts/new", {})["attempt_id"]

    fill = client.post("/api/fill_blank/new", {
        "attempt_id": attempt_id, "file": "sample_english_fill_blank.json",
    })
    fill_score = 0
    for question in fill["questions"]:
        response = client.post("/api/fill_blank/check", {
            "attempt_id": attempt_id, "game_id": fill["game_id"],
            "qid": question["id"], "idx": 0,
        })
        fill_score += int(response["ok"])
    fill_result = client.post("/api/fill_blank/result", {
        "attempt_id": attempt_id, "game_id": fill["game_id"],
    })
    _require(fill_result["score"] == fill_score, "Fill Blank score does not match answers.")

    matching = client.post("/api/matching/new", {
        "attempt_id": attempt_id, "file": "sample_english_matching.json",
    })
    pairs = {term["id"]: index for index, term in enumerate(matching["terms"])}
    matching_result = client.post("/api/matching/check", {
        "attempt_id": attempt_id, "game_id": matching["game_id"], "pairs": pairs,
    })
    _require(
        matching_result["score"] == sum(item["ok"] for item in matching_result["review"]),
        "Matching score does not match its saved review.",
    )

    quiz = client.post("/api/quiz/new", {
        "attempt_id": attempt_id, "file": "sample_english_quiz.json",
    })
    quiz_score = 0
    for question in quiz["questions"]:
        response = client.post("/api/quiz/check", {
            "attempt_id": attempt_id, "game_id": quiz["game_id"],
            "qid": question["id"], "idx": 0,
        })
        quiz_score += int(response["ok"])
    quiz_result = client.post("/api/quiz/result", {
        "attempt_id": attempt_id, "game_id": quiz["game_id"],
    })
    _require(quiz_result["score"] == quiz_score, "Quiz score does not match answers.")

    final = client.post("/api/final_test/new", {"attempt_id": attempt_id})
    final_score = 0
    for question in final["questions"]:
        response = client.post("/api/final_test/check", {
            "attempt_id": attempt_id, "game_id": final["game_id"],
            "qid": question["id"], "idx": 0,
        })
        final_score += int(response["ok"])
    final_result = client.post("/api/final_test/result", {
        "attempt_id": attempt_id, "game_id": final["game_id"],
    })
    _require(final_result["score"] == final_score, "Final Test score does not match answers.")
    _require(
        math.isclose(final_result["grade_10"], 10 * final_score / final_result["total"]),
        "Final Test grade is incorrect.",
    )

    state = client.get(f"/api/session?attempt_id={attempt_id}")["attempt"]
    _require(state["attempt_id"] == attempt_id, "Attempt lookup returned another tab's attempt.")
    _require(all(state["done"].values()), "Not all games were marked complete.")
    expected_scores = {
        "fill_blank": fill_score,
        "matching": matching_result["score"],
        "quiz": quiz_score,
        "final_test": final_score,
    }
    for kind, score in expected_scores.items():
        _require(state["results"][kind]["score"] == score, f"Stored {kind} score is incorrect.")
    game_ids = [fill["game_id"], matching["game_id"], quiz["game_id"], final["game_id"]]
    return {
        "attempt_id": attempt_id,
        "game_ids": game_ids,
        "scores": expected_scores,
    }


def audit_database(expected_players: list[dict]) -> dict:
    expected_by_attempt = {player["attempt_id"]: player for player in expected_players}
    db = server.manager.connect()
    try:
        sessions = db.execute("SELECT COUNT(*) AS count FROM sessions").fetchone()["count"]
        attempts = db.execute("SELECT id, session_id, flow_json FROM attempts").fetchall()
        game_count = db.execute("SELECT COUNT(*) AS count FROM games").fetchone()["count"]
        journal_mode = db.execute("PRAGMA journal_mode").fetchone()[0]
        _require(sessions == len(expected_players), "Session count differs from client count.")
        _require(len(attempts) == len(expected_players), "Attempt count differs from client count.")
        _require(game_count == 4 * len(expected_players), "Expected four games per attempt.")
        _require(len({row["session_id"] for row in attempts}) == len(expected_players),
                 "Client sessions were not isolated.")
        _require(journal_mode.lower() == "wal", f"SQLite journal mode is {journal_mode}, not WAL.")

        for row in attempts:
            expected = expected_by_attempt.get(row["id"])
            _require(expected is not None, "Database contains an unknown attempt.")
            flow = json.loads(row["flow_json"])
            for kind, score in expected["scores"].items():
                _require(flow["results"][kind]["score"] == score,
                         f"Persisted {kind} score differs from client result.")
            game_rows = db.execute(
                "SELECT kind, state_json FROM games WHERE attempt_id = ?", (row["id"],)
            ).fetchall()
            _require({game["kind"] for game in game_rows} == {
                "fill_blank", "matching", "quiz", "final_test",
            }, "Game snapshots are missing or duplicated.")
            for game_row in game_rows:
                state = json.loads(game_row["state_json"])
                if game_row["kind"] == "matching":
                    _require(state.get("result") is not None,
                             "Matching answer snapshot was not persisted.")
                else:
                    _require(len(state["chosen"]) == len(state["questions"]),
                             f"{game_row['kind']} answer snapshot is incomplete.")
        return {
            "sessions": sessions,
            "attempts": len(attempts),
            "game_snapshots": game_count,
            "journal_mode": journal_mode,
            "ownership_and_score_audit": "PASS",
        }
    finally:
        db.close()


def _total_memory_gb() -> float | None:
    if os.name == "nt":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return round(status.ullTotalPhys / (1024 ** 3), 2)
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        for line in meminfo.read_text(encoding="ascii").splitlines():
            if line.startswith("MemTotal:"):
                return round(int(line.split()[1]) / (1024 ** 2), 2)
    return None


def _percentile(samples: list[float], percentile: float) -> float:
    ordered = sorted(samples)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return round(ordered[index], 2)


def run_load_test(client_count: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="edugame-load-") as temp_dir:
        previous_manager = server.manager
        previous_limiter = server.request_limiter
        previous_direct_session = server._direct_session_id
        server.configure_database(Path(temp_dir) / "load.sqlite3")
        server.request_limiter = server.RequestRateLimiter(server.MAX_REQUESTS_PER_MINUTE)
        server._direct_session_id = None
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()
        metrics = Metrics()
        started = time.perf_counter()
        players = []
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=client_count) as pool:
                futures = [pool.submit(play_one_client, httpd.server_port, metrics)
                           for _ in range(client_count)]
                for future in concurrent.futures.as_completed(futures):
                    try:
                        players.append(future.result())
                    except Exception as error:
                        metrics.record_data_failure(f"{type(error).__name__}: {error}")
            elapsed = time.perf_counter() - started
            if not metrics.data_failures and not metrics.request_failures:
                audit = audit_database(players)
            else:
                audit = {"ownership_and_score_audit": "NOT RUN: request or data failure"}
            samples = metrics.latencies_ms
            requests = len(samples)
            return {
                "clients": client_count,
                "conditions": {
                    "server": "in-process ThreadingHTTPServer on 127.0.0.1",
                    "worker_threads": client_count,
                    "database": "temporary SQLite file; WAL; BEGIN IMMEDIATE for writes",
                    "requests_per_minute_per_session": server.MAX_REQUESTS_PER_MINUTE,
                    "request_body_limit_bytes": server.MAX_REQUEST_BODY_BYTES,
                    "workload": "complete four-game English sample chapter per client",
                },
                "results": {
                    "elapsed_seconds": round(elapsed, 2),
                    "requests": requests,
                    "throughput_requests_per_second": round(requests / elapsed, 2),
                    "error_requests": metrics.request_failures,
                    "error_rate_percent": round(
                        100 * metrics.request_failures / requests if requests else 0, 3),
                    "http_statuses": dict(metrics.statuses),
                    "latency_ms": {
                        "mean": round(sum(samples) / len(samples), 2) if samples else None,
                        "p50": _percentile(samples, 0.50) if samples else None,
                        "p95": _percentile(samples, 0.95) if samples else None,
                        "p99": _percentile(samples, 0.99) if samples else None,
                        "max": round(max(samples), 2) if samples else None,
                    },
                    "successful_clients": len(players),
                    "data_failures": metrics.data_failures,
                    "database_audit": audit,
                },
            }
        finally:
            httpd.shutdown()
            httpd.server_close()
            server_thread.join()
            server.manager = previous_manager
            server.request_limiter = previous_limiter
            server._direct_session_id = previous_direct_session


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--clients", type=int, nargs="+", default=[10, 50, 100],
        help="Concurrent client counts to test (default: 10 50 100).",
    )
    args = parser.parse_args()
    if any(count < 1 for count in args.clients):
        parser.error("client counts must be positive")
    report = {
        "machine": {
            "platform": platform.platform(),
            "processor": platform.processor() or "unreported by operating system",
            "logical_cpu_count": os.cpu_count(),
            "total_memory_gb": _total_memory_gb(),
            "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version,
        },
        "runs": [],
    }
    for count in args.clients:
        report["runs"].append(run_load_test(count))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if any(
        run["results"]["error_requests"]
        or run["results"]["data_failures"]
        or run["results"]["successful_clients"] != run["clients"]
        or run["results"]["database_audit"].get("ownership_and_score_audit") != "PASS"
        for run in report["runs"]
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
