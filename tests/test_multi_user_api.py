import concurrent.futures
import http.client
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import server
from http.server import ThreadingHTTPServer


class APIClient:
    def __init__(self, port):
        self.port = port
        self.cookie = ""
        self.cookie_attributes = ""
        status, _, _ = self.get("/api/session")
        if status != 200 or not self.cookie:
            raise AssertionError("Could not establish an HTTP session")

    def request(self, method, path, payload=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        headers = {"Cookie": self.cookie}
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload)
        connection.request(method, path, body=body, headers=headers)
        response = connection.getresponse()
        raw = response.read()
        set_cookie = response.getheader("Set-Cookie")
        if set_cookie:
            self.cookie_attributes = set_cookie
            self.cookie = set_cookie.split(";", 1)[0]
        content_type = response.getheader("Content-Type", "")
        parsed = json.loads(raw) if raw and "application/json" in content_type else raw
        result = response.status, parsed, response.getheader("Location")
        connection.close()
        return result

    def get(self, path):
        return self.request("GET", path)

    def post(self, path, payload):
        return self.request("POST", path, payload)


class MultiUserAPITests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "attempts.sqlite3"
        server.configure_database(self.database_path)
        server.manager.reset()
        server.MATCHING_GAMES.clear()
        server.FILL_GAMES.clear()
        server.QUIZ_GAMES.clear()
        server.FINAL_TEST_GAMES.clear()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.clients = []

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join()
        self.temp_dir.cleanup()

    def client(self):
        client = APIClient(self.httpd.server_port)
        self.clients.append(client)
        return client

    def fill_new(self, client):
        status, data, _ = client.post(
            "/api/fill_blank/new", {"file": "sample_philosophy_fill_blank.json"})
        self.assertEqual(status, 200, data)
        return data

    def answer_fill(self, client, game, idx=0, question=None):
        question = question or game["questions"][0]
        return client.post("/api/fill_blank/check", {
            "attempt_id": game["attempt_id"], "game_id": game["game_id"],
            "qid": question["id"], "idx": idx,
        })

    def complete_fill(self, client, game):
        for question in game["questions"]:
            status, _, _ = self.answer_fill(client, game, 0, question)
            self.assertEqual(status, 200)
        status, result, _ = client.post("/api/fill_blank/result", {
            "attempt_id": game["attempt_id"], "game_id": game["game_id"],
        })
        self.assertEqual(status, 200, result)
        return result

    def complete_matching(self, client, attempt_id):
        status, game, _ = client.post("/api/matching/new", {
            "attempt_id": attempt_id, "file": "sample_philosophy_matching.json",
        })
        self.assertEqual(status, 200, game)
        pairs = {term["id"]: index for index, term in enumerate(game["terms"])}
        status, result, _ = client.post("/api/matching/check", {
            "attempt_id": attempt_id, "game_id": game["game_id"], "pairs": pairs,
        })
        self.assertEqual(status, 200, result)
        return game

    def complete_quiz(self, client, attempt_id):
        status, game, _ = client.post("/api/quiz/new", {
            "attempt_id": attempt_id, "file": "sample_philosophy_quiz.json",
        })
        self.assertEqual(status, 200, game)
        for question in game["questions"]:
            status, _, _ = client.post("/api/quiz/check", {
                "attempt_id": attempt_id, "game_id": game["game_id"],
                "qid": question["id"], "idx": 0,
            })
            self.assertEqual(status, 200)
        status, result, _ = client.post("/api/quiz/result", {
            "attempt_id": attempt_id, "game_id": game["game_id"],
        })
        self.assertEqual(status, 200, result)
        return game

    def complete_final(self, client, attempt_id):
        status, game, _ = client.post("/api/final_test/new", {"attempt_id": attempt_id})
        self.assertEqual(status, 200, game)
        for question in game["questions"]:
            status, _, _ = client.post("/api/final_test/check", {
                "attempt_id": attempt_id, "game_id": game["game_id"],
                "qid": question["id"], "idx": 0,
            })
            self.assertEqual(status, 200)
        status, result, _ = client.post("/api/final_test/result", {
            "attempt_id": attempt_id, "game_id": game["game_id"],
        })
        self.assertEqual(status, 200, result)
        return game, result

    def test_t01_simultaneous_fill_blank_games_are_isolated(self):
        player_a, player_b = self.client(), self.client()
        game_a, game_b = self.fill_new(player_a), self.fill_new(player_b)
        self.assertNotEqual(game_a["game_id"], game_b["game_id"])
        q_a, q_b = game_a["questions"][0], game_b["questions"][0]
        self.assertEqual(self.answer_fill(player_a, game_a, 0, q_a)[0], 200)
        self.assertEqual(self.answer_fill(player_b, game_b, 1, q_b)[0], 200)
        state_a = player_a.get(
            f"/api/session?attempt_id={game_a['attempt_id']}")[1]["attempt"]["games"]["fill_blank"]
        state_b = player_b.get(
            f"/api/session?attempt_id={game_b['attempt_id']}")[1]["attempt"]["games"]["fill_blank"]
        self.assertNotEqual(state_a["progress"][q_a["id"]]["idx"],
                            state_b["progress"][q_b["id"]]["idx"])

    def test_t02_only_completed_player_can_unlock_matching(self):
        player_a, player_b = self.client(), self.client()
        game_a, game_b = self.fill_new(player_a), self.fill_new(player_b)
        self.complete_fill(player_a, game_a)
        self.assertEqual(player_a.post("/api/matching/new", {
            "attempt_id": game_a["attempt_id"],
            "file": "sample_philosophy_matching.json",
        })[0], 200)
        self.assertEqual(player_b.post("/api/matching/new", {
            "file": "sample_philosophy_matching.json",
        })[0], 400)
        self.assertNotEqual(game_a["attempt_id"], game_b["attempt_id"])

    def test_t03_other_users_attempt_and_game_ids_are_denied(self):
        player_a, player_b = self.client(), self.client()
        game = self.fill_new(player_a)
        payload = {
            "attempt_id": game["attempt_id"], "game_id": game["game_id"],
            "qid": game["questions"][0]["id"], "idx": 0,
        }
        self.assertEqual(player_b.post("/api/fill_blank/check", payload)[0], 403)
        self.assertEqual(player_b.post("/api/fill_blank/new", {
            "attempt_id": game["attempt_id"], "file": "sample_philosophy_fill_blank.json",
        })[0], 403)

    def test_new_empty_attempt_can_be_loaded_before_starting_fill_blank(self):
        # Browser startup: GET files -> POST attempt -> GET attempt -> POST game.
        player = self.client()
        status, created, _ = player.post("/api/attempts/new", {})
        self.assertEqual(status, 200)
        attempt_id = created["attempt_id"]

        status, state, _ = player.get(f"/api/session?attempt_id={attempt_id}")
        self.assertEqual(status, 200)
        self.assertEqual(state["attempt"]["attempt_id"], attempt_id)
        self.assertIsNone(state["attempt"]["chapter_id"])
        self.assertIsNone(state["attempt"]["subject"])
        self.assertEqual(state["attempt"]["games"], {})

        status, game, _ = player.post("/api/fill_blank/new", {
            "attempt_id": attempt_id, "file": "sample_english_fill_blank.json",
        })
        self.assertEqual(status, 200)
        self.assertEqual(game["attempt_id"], attempt_id)
        self.assertTrue(game["questions"])

    def test_t04_same_user_can_keep_multiple_attempts_independent(self):
        player = self.client()
        first = self.fill_new(player)
        self.answer_fill(player, first, 0)
        status, second_attempt, _ = player.post("/api/attempts/new", {})
        self.assertEqual(status, 200)
        second = player.post("/api/fill_blank/new", {
            "attempt_id": second_attempt["attempt_id"],
            "file": "sample_english_fill_blank.json",
        })[1]
        self.assertNotEqual(first["attempt_id"], second["attempt_id"])
        self.assertNotEqual(first["game_id"], second["game_id"])
        attempts = player.get("/api/attempts")[1]["attempts"]
        self.assertEqual(len(attempts), 2)
        self.assertTrue(any(item["attempt_id"] == first["attempt_id"] for item in attempts))
        self.assertEqual({item["subject"] for item in attempts}, {"philosophy", "english"})

    def test_t05_reload_resumes_existing_game_and_answers(self):
        player = self.client()
        game = self.fill_new(player)
        question = game["questions"][0]
        self.answer_fill(player, game, 1, question)
        state = player.get(
            f"/api/session?attempt_id={game['attempt_id']}")[1]["attempt"]["games"]["fill_blank"]
        resumed = player.post("/api/fill_blank/new", {
            "attempt_id": game["attempt_id"], "file": "sample_philosophy_fill_blank.json",
        })[1]
        self.assertEqual(resumed["game_id"], game["game_id"])
        self.assertEqual(resumed["progress"], state["progress"])
        self.assertEqual(resumed["progress"][question["id"]]["idx"], 1)

    def test_t05a_shared_cookie_keeps_attempts_separate_per_tab_and_reload(self):
        player = self.client()
        attempt_a = player.post("/api/attempts/new", {})[1]["attempt_id"]
        game_a = player.post("/api/fill_blank/new", {
            "attempt_id": attempt_a, "file": "sample_philosophy_fill_blank.json",
        })[1]
        attempt_b = player.post("/api/attempts/new", {})[1]["attempt_id"]
        game_b = player.post("/api/fill_blank/new", {
            "attempt_id": attempt_b, "file": "sample_english_fill_blank.json",
        })[1]
        self.assertNotEqual(attempt_a, attempt_b)
        self.assertNotEqual(game_a["game_id"], game_b["game_id"])
        self.assertIsNone(player.get("/api/session")[1]["attempt"])

        self.answer_fill(player, game_a, 0)
        self.answer_fill(player, game_b, 1)
        state_a = player.get(f"/api/session?attempt_id={attempt_a}")[1]["attempt"]
        state_b = player.get(f"/api/session?attempt_id={attempt_b}")[1]["attempt"]
        self.assertEqual(state_a["attempt_id"], attempt_a)
        self.assertEqual(state_b["attempt_id"], attempt_b)
        self.assertEqual(
            state_a["games"]["fill_blank"]["progress"][game_a["questions"][0]["id"]]["idx"], 0)
        self.assertEqual(
            state_b["games"]["fill_blank"]["progress"][game_b["questions"][0]["id"]]["idx"], 1)

        resumed_a = player.post("/api/fill_blank/new", {
            "attempt_id": attempt_a, "file": "sample_philosophy_fill_blank.json",
        })[1]
        resumed_b = player.post("/api/fill_blank/new", {
            "attempt_id": attempt_b, "file": "sample_english_fill_blank.json",
        })[1]
        self.assertEqual(resumed_a["game_id"], game_a["game_id"])
        self.assertEqual(resumed_b["game_id"], game_b["game_id"])

    def test_t06_duplicate_answer_never_scores_twice(self):
        player = self.client()
        game = self.fill_new(player)
        question = game["questions"][0]
        payload = {"attempt_id": game["attempt_id"], "game_id": game["game_id"],
                   "qid": question["id"], "idx": 0}
        self.assertEqual(player.post("/api/fill_blank/check", payload)[1],
                         player.post("/api/fill_blank/check", payload)[1])
        for remaining in game["questions"][1:]:
            self.answer_fill(player, game, 0, remaining)
        state = player.get(
            f"/api/session?attempt_id={game['attempt_id']}")[1]["attempt"]["games"]["fill_blank"]
        score = player.post("/api/fill_blank/result", {
            "attempt_id": game["attempt_id"], "game_id": game["game_id"],
        })[1]["score"]
        expected = sum(1 for answer in state["progress"].values() if answer["ok"])
        self.assertEqual(score, expected)

    def test_t07_concurrent_submissions_for_one_question_are_atomic(self):
        player = self.client()
        game = self.fill_new(player)
        question = game["questions"][0]
        payloads = [dict(attempt_id=game["attempt_id"], game_id=game["game_id"],
                         qid=question["id"], idx=idx) for idx in (0, 1)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(
                lambda payload: player.post("/api/fill_blank/check", payload), payloads))
        self.assertEqual([response[0] for response in responses], [200, 200])
        self.assertEqual(responses[0][1], responses[1][1])
        for remaining in game["questions"][1:]:
            self.answer_fill(player, game, 0, remaining)
        result = player.post("/api/fill_blank/result", {
            "attempt_id": game["attempt_id"], "game_id": game["game_id"],
        })[1]
        state = player.get(
            f"/api/session?attempt_id={game['attempt_id']}")[1]["attempt"]["games"]["fill_blank"]
        expected = sum(1 for answer in state["progress"].values() if answer["ok"])
        self.assertEqual(result["score"], expected)

    def test_answer_snapshot_and_score_rollback_together(self):
        player = self.client()
        game = self.fill_new(player)
        question = game["questions"][0]
        session_id = player.cookie.partition("=")[2]
        payload = {
            "attempt_id": game["attempt_id"], "game_id": game["game_id"],
            "qid": question["id"], "idx": 0,
        }
        with mock.patch.object(server.manager, "save_flow", side_effect=RuntimeError("test rollback")):
            with self.assertRaisesRegex(RuntimeError, "test rollback"):
                server.fill_api_check(payload, session_id)

        restored = player.get(
            f"/api/session?attempt_id={game['attempt_id']}")[1]["attempt"]["games"]["fill_blank"]
        self.assertNotIn(question["id"], restored["progress"])
        self.assertEqual(player.post("/api/fill_blank/check", payload)[0], 200)
        for remaining in game["questions"][1:]:
            self.answer_fill(player, game, 0, remaining)
        result = player.post("/api/fill_blank/result", {
            "attempt_id": game["attempt_id"], "game_id": game["game_id"],
        })[1]
        state = player.get(
            f"/api/session?attempt_id={game['attempt_id']}")[1]["attempt"]["games"]["fill_blank"]
        self.assertEqual(
            result["score"], sum(1 for answer in state["progress"].values() if answer["ok"]))

    def test_review_game_does_not_change_completed_main_result(self):
        player = self.client()
        fill = self.fill_new(player)
        self.complete_fill(player, fill)
        main_game = self.complete_matching(player, fill["attempt_id"])
        before = player.get(
            f"/api/session?attempt_id={fill['attempt_id']}")[1]["attempt"]["results"]["matching"]
        review_id = main_game["terms"][0]["id"]
        status, review_game, _ = player.post("/api/matching/new", {
            "attempt_id": fill["attempt_id"],
            "file": "sample_philosophy_matching.json", "only_ids": [review_id],
        })
        self.assertEqual(status, 200, review_game)
        self.assertEqual(len(review_game["terms"]), 1)
        self.assertEqual(player.post("/api/matching/check", {
            "attempt_id": fill["attempt_id"], "game_id": review_game["game_id"],
            "pairs": {review_id: 0},
        })[0], 200)
        state = player.get(
            f"/api/session?attempt_id={fill['attempt_id']}")[1]["attempt"]
        self.assertEqual(state["results"]["matching"], before)
        self.assertTrue(state["done"]["matching"])

    def test_fill_blank_review_with_one_wrong_question_keeps_distractors(self):
        player = self.client()
        game = self.fill_new(player)
        first = game["questions"][0]
        with server.manager.transaction() as db:
            _, state = server._read_game_state(
                db, game["attempt_id"], game["game_id"], "fill_blank")
        correct_indices = {
            question["id"]: question["correct"] for question in state["questions"]
        }
        wrong_idx = (correct_indices[first["id"]] + 1) % len(first["options"])
        self.answer_fill(player, game, wrong_idx, first)
        for question in game["questions"][1:]:
            self.answer_fill(player, game, correct_indices[question["id"]], question)
        result = player.post("/api/fill_blank/result", {
            "attempt_id": game["attempt_id"], "game_id": game["game_id"],
        })[1]
        self.assertEqual(result["wrong"], [first["id"]])

        status, review, _ = player.post("/api/fill_blank/new", {
            "attempt_id": game["attempt_id"],
            "file": "sample_philosophy_fill_blank.json",
            "only_ids": result["wrong"],
        })
        self.assertEqual(status, 200, review)
        self.assertEqual(len(review["questions"]), 1)
        self.assertGreaterEqual(len(review["questions"][0]["options"]), 2)

    def test_t08_database_restart_restores_attempt_and_answers(self):
        player = self.client()
        game = self.fill_new(player)
        question = game["questions"][0]
        self.answer_fill(player, game, 0, question)
        old_httpd = self.httpd
        port = old_httpd.server_port
        old_httpd.shutdown()
        old_httpd.server_close()
        self.thread.join()
        code = (
            "from http.server import ThreadingHTTPServer; import server; "
            f"ThreadingHTTPServer(('127.0.0.1', {port}), server.Handler).serve_forever()"
        )
        environment = os.environ.copy()
        environment["EDUGAME_DB_PATH"] = str(self.database_path)
        environment["EDUGAME_NO_BROWSER"] = "1"
        process = subprocess.Popen(
            [sys.executable, "-c", code], cwd=server.ROOT, env=environment,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            player.port = port
            deadline = time.monotonic() + 10
            while True:
                if process.poll() is not None:
                    self.fail("Restarted server process exited before becoming ready")
                try:
                    status, state, _ = player.get(
                        f"/api/session?attempt_id={game['attempt_id']}")
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        self.fail("Restarted server process did not become ready")
                    time.sleep(0.1)
            self.assertEqual(status, 200)
            restored = state["attempt"]["games"]["fill_blank"]
            self.assertEqual(restored["game_id"], game["game_id"])
            self.assertEqual(restored["progress"][question["id"]]["idx"], 0)
        finally:
            process.terminate()
            process.wait(timeout=10)

    def test_t09_missing_or_expired_session_is_rejected(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.httpd.server_port)
        connection.request("POST", "/api/attempts/new", body="{}",
                          headers={"Content-Type": "application/json"})
        self.assertEqual(connection.getresponse().status, 401)
        connection.close()
        player = self.client()
        self.assertIn("HttpOnly", player.cookie_attributes)
        self.assertIn("SameSite=Lax", player.cookie_attributes)
        self.assertIn("Max-Age=2592000", player.cookie_attributes)
        session_id = player.cookie.partition("=")[2]
        with server.manager.transaction() as db:
            db.execute("UPDATE sessions SET expires_at = 0 WHERE id = ?", (session_id,))
        self.assertEqual(player.get("/api/session")[0], 401)
        self.assertEqual(player.get("/api/attempts")[0], 401)
        self.assertEqual(player.post("/api/attempts/new", {})[0], 403)
        new_player = self.client()
        self.assertIsNone(new_player.get("/api/session")[1]["attempt"])
        self.assertEqual(new_player.get("/api/attempts")[1]["attempts"], [])
        secure_connection = http.client.HTTPConnection(
            "127.0.0.1", self.httpd.server_port, timeout=15)
        with mock.patch.object(server, "TRUST_PROXY", True):
            secure_connection.request(
                "GET", "/api/session", headers={"X-Forwarded-Proto": "https"})
            secure_response = secure_connection.getresponse()
            secure_cookie = secure_response.getheader("Set-Cookie", "")
            secure_response.read()
        secure_connection.close()
        self.assertIn("Secure", secure_cookie)

    def test_request_body_size_limit_returns_413(self):
        player = self.client()
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.httpd.server_port, timeout=15)
        connection.putrequest("POST", "/api/attempts/new")
        connection.putheader("Cookie", player.cookie)
        connection.putheader("Content-Length", str(server.MAX_REQUEST_BODY_BYTES + 1))
        connection.endheaders()
        response = connection.getresponse()
        self.assertEqual(response.status, 413)
        self.assertIn("giới hạn", json.loads(response.read())["error"])
        connection.close()

    def test_per_session_request_rate_limit_returns_429(self):
        player = self.client()
        original_limiter = server.request_limiter
        server.request_limiter = server.RequestRateLimiter(2)
        try:
            self.assertEqual(player.post("/api/attempts/new", {})[0], 200)
            self.assertEqual(player.post("/api/attempts/new", {})[0], 200)
            status, body, _ = player.post("/api/attempts/new", {})
            self.assertEqual(status, 429, body)
        finally:
            server.request_limiter = original_limiter

    def test_all_game_apis_reject_another_sessions_attempt_and_game_ids(self):
        owner, other = self.client(), self.client()
        fill = self.fill_new(owner)
        attempt_id = fill["attempt_id"]
        self.complete_fill(owner, fill)
        matching = self.complete_matching(owner, attempt_id)
        quiz = self.complete_quiz(owner, attempt_id)
        final, _ = self.complete_final(owner, attempt_id)

        self.assertEqual(other.get(f"/api/session?attempt_id={attempt_id}")[0], 403)
        self.assertEqual(other.get(f"/fill_blank.html?attempt_id={attempt_id}")[0], 403)
        requests = [
            ("/api/fill_blank/new", {"attempt_id": attempt_id, "file": "sample_philosophy_fill_blank.json"}),
            ("/api/fill_blank/check", {"attempt_id": attempt_id, "game_id": fill["game_id"],
             "qid": fill["questions"][0]["id"], "idx": 0}),
            ("/api/fill_blank/result", {"attempt_id": attempt_id, "game_id": fill["game_id"]}),
            ("/api/matching/new", {"attempt_id": attempt_id, "file": "sample_philosophy_matching.json"}),
            ("/api/matching/check", {"attempt_id": attempt_id, "game_id": matching["game_id"], "pairs": {}}),
            ("/api/matching/progress", {"attempt_id": attempt_id, "game_id": matching["game_id"], "pairs": {}}),
            ("/api/quiz/new", {"attempt_id": attempt_id, "file": "sample_philosophy_quiz.json"}),
            ("/api/quiz/check", {"attempt_id": attempt_id, "game_id": quiz["game_id"],
             "qid": quiz["questions"][0]["id"], "idx": 0}),
            ("/api/quiz/result", {"attempt_id": attempt_id, "game_id": quiz["game_id"]}),
            ("/api/final_test/new", {"attempt_id": attempt_id}),
            ("/api/final_test/check", {"attempt_id": attempt_id, "game_id": final["game_id"],
             "qid": final["questions"][0]["id"], "idx": 0}),
            ("/api/final_test/result", {"attempt_id": attempt_id, "game_id": final["game_id"]}),
        ]
        for path, payload in requests:
            with self.subTest(path=path):
                self.assertEqual(other.post(path, payload)[0], 403)

    def test_replaced_game_cannot_complete_or_unlock_attempt(self):
        player = self.client()
        fill = self.fill_new(player)
        self.complete_fill(player, fill)
        first = self.complete_matching(player, fill["attempt_id"])
        replacement = player.post("/api/matching/new", {
            "attempt_id": fill["attempt_id"],
            "file": "sample_philosophy_matching.json", "restart": True,
        })[1]
        stale = player.post("/api/matching/check", {
            "attempt_id": fill["attempt_id"], "game_id": first["game_id"],
            "pairs": {},
        })
        self.assertEqual(stale[0], 403)
        self.assertNotEqual(replacement["game_id"], first["game_id"])
        self.assertEqual(player.post("/api/quiz/new", {
            "attempt_id": fill["attempt_id"],
            "file": "sample_philosophy_quiz.json",
        })[0], 400)

    def test_t10_many_clients_complete_full_flow_without_data_mixing(self):
        clients = [self.client() for _ in range(4)]

        def finish(client):
            fill = self.fill_new(client)
            fill_result = self.complete_fill(client, fill)
            matching_game = self.complete_matching(client, fill["attempt_id"])
            quiz_game = self.complete_quiz(client, fill["attempt_id"])
            final_game, final_result = self.complete_final(client, fill["attempt_id"])
            return (fill["attempt_id"], fill["game_id"], matching_game["game_id"],
                    quiz_game["game_id"], final_game["game_id"], fill_result, final_result)

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(finish, clients))
        for index in range(1, len(results[0]) - 2):
            ids = [row[index] for row in results]
            self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual(len({row[5]["total"] for row in results}), 1)
        self.assertTrue(all(row[6]["total"] > 0 for row in results))


if __name__ == "__main__":
    unittest.main()
