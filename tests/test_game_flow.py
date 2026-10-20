import http.client
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

import server


class GameFlowTests(unittest.TestCase):
    def setUp(self):
        server.MATCHING_GAMES.clear()
        server.FILL_GAMES.clear()
        server.QUIZ_GAMES.clear()
        server.FLOW_STATE.update({
            "fill_blank_done": False,
            "matching_done": False,
            "quiz_done": False,
        })
        server.ACTIVE_FILL_GAME_ID = None
        server.ACTIVE_MATCHING_GAME_ID = None
        server.ACTIVE_QUIZ_GAME_ID = None
        server.ACTIVE_MATCHING_REVIEW_ONLY = False
        server.ACTIVE_QUIZ_REVIEW_ONLY = False

    def complete_fill_blank(self):
        game_view = server.fill_api_new({"file": "sample_philosophy_fill_blank.json"})
        game = server.FILL_GAMES[game_view["game_id"]]
        question_by_id = {question["id"]: question for question in game.questions}
        for question in game_view["questions"]:
            server.fill_api_check({
                "game_id": game_view["game_id"],
                "qid": question["id"],
                "idx": question_by_id[question["id"]]["correct"],
            })
        return server.fill_api_result({"game_id": game_view["game_id"]})

    def complete_matching(self):
        game_view = server.matching_api_new(
            {"file": "sample_philosophy_matching.json"}
        )
        game = server.MATCHING_GAMES[game_view["game_id"]]
        pairs = {
            item["id"]: game.order.index(item["definition"])
            for item in game.items
        }
        return server.matching_api_check({
            "game_id": game_view["game_id"],
            "pairs": pairs,
        })

    def complete_quiz(self):
        game_view = server.quiz_api_new({"file": "sample_philosophy_quiz.json"})
        game = server.QUIZ_GAMES[game_view["game_id"]]
        for question in game.questions:
            server.quiz_api_check({
                "game_id": game_view["game_id"],
                "qid": question["id"],
                "idx": question["correct"],
            })
        return server.quiz_api_result({"game_id": game_view["game_id"]})

    def test_matching_is_locked_until_full_fill_blank_result(self):
        with self.assertRaisesRegex(ValueError, "hoàn thành game điền chỗ trống"):
            server.matching_api_new({"file": "sample_philosophy_matching.json"})

        self.assertGreater(self.complete_fill_blank()["total"], 0)
        matching_view = server.matching_api_new(
            {"file": "sample_philosophy_matching.json"}
        )
        self.assertGreater(len(matching_view["terms"]), 0)

    def test_incomplete_fill_blank_does_not_unlock_matching(self):
        game_view = server.fill_api_new({"file": "sample_philosophy_fill_blank.json"})
        with self.assertRaisesRegex(ValueError, "Chưa trả lời hết"):
            server.fill_api_result({"game_id": game_view["game_id"]})

        with self.assertRaisesRegex(ValueError, "hoàn thành game điền chỗ trống"):
            server.matching_api_new({"file": "sample_philosophy_matching.json"})

    def test_fill_blank_response_includes_subject_for_next_game(self):
        game_view = server.fill_api_new({"file": "sample_philosophy_fill_blank.json"})
        self.assertEqual(game_view["subject"], "philosophy")

    def test_quiz_is_locked_until_matching_is_completed(self):
        with self.assertRaisesRegex(ValueError, "hoàn thành game nối từ"):
            server.quiz_api_new({"file": "sample_philosophy_quiz.json"})

        self.complete_fill_blank()
        server.matching_api_new({"file": "sample_philosophy_matching.json"})
        with self.assertRaisesRegex(ValueError, "hoàn thành game nối từ"):
            server.quiz_api_new({"file": "sample_philosophy_quiz.json"})

        self.complete_matching()
        quiz_view = server.quiz_api_new({"file": "sample_philosophy_quiz.json"})
        self.assertGreater(len(quiz_view["questions"]), 0)
        self.assertEqual(quiz_view["subject"], "philosophy")

    def test_completed_quiz_finishes_game_flow(self):
        self.complete_fill_blank()
        self.complete_matching()
        result = self.complete_quiz()

        self.assertEqual(result["score"], result["total"])
        self.assertTrue(server.FLOW_STATE["quiz_done"])

    def test_quiz_api_only_lists_quiz_sample_files(self):
        self.assertEqual(
            server.quiz_sample_files(),
            ["sample_english_quiz.json", "sample_philosophy_quiz.json"],
        )

    def test_http_flow_redirects_and_serves_matching_after_completion(self):
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        connection = http.client.HTTPConnection("127.0.0.1", httpd.server_port)
        try:
            connection.request("GET", "/")
            response = connection.getresponse()
            self.assertEqual(response.status, 303)
            self.assertEqual(response.getheader("Location"), "/fill_blank.html")
            response.read()

            connection.request("GET", "/index.html")
            response = connection.getresponse()
            self.assertEqual(response.status, 303)
            self.assertEqual(response.getheader("Location"), "/fill_blank.html")
            response.read()

            connection.request("GET", "/matching.html")
            response = connection.getresponse()
            self.assertEqual(response.status, 303)
            self.assertEqual(response.getheader("Location"), "/")
            response.read()

            self.complete_fill_blank()
            connection.request("GET", "/matching.html")
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            response.read()

            connection.request("GET", "/quiz.html")
            response = connection.getresponse()
            self.assertEqual(response.status, 303)
            self.assertEqual(response.getheader("Location"), "/")
            response.read()

            self.complete_matching()
            connection.request("GET", "/quiz.html")
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            response.read()

            self.complete_quiz()
            connection.request("GET", "/")
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertIn("Đã hoàn thành 3 game", response.read().decode("utf-8"))
        finally:
            connection.close()
            httpd.shutdown()
            httpd.server_close()
            thread.join()

    def test_result_pages_provide_only_supported_continuation(self):
        root = Path(server.ROOT)
        fill_page = (root / "web" / "fill_blank.html").read_text(encoding="utf-8")
        matching_page = (root / "web" / "matching.html").read_text(encoding="utf-8")
        quiz_page = (root / "web" / "quiz.html").read_text(encoding="utf-8")

        self.assertIn('id="continue"', fill_page)
        self.assertIn('if (!reviewOnly)', fill_page)
        self.assertIn("window.location.href = `/matching.html?subject=", fill_page)
        self.assertIn("encodeURIComponent(game.subject)", fill_page)
        self.assertIn("'Tiếp tục'", matching_page)
        self.assertIn("`/quiz.html?subject=${encodeURIComponent(game.subject || '')}`", matching_page)
        self.assertIn("new URLSearchParams(window.location.search)", matching_page)
        self.assertIn('api("/api/quiz/files")', quiz_page)
        self.assertIn('api("/api/quiz/new"', quiz_page)

    def test_quiz_logic_rejects_invalid_answer_shapes(self):
        with self.assertRaisesRegex(ValueError, "đúng 4 phương án"):
            server.quiz.EnglishQuizGame([{
                "id": "q1",
                "q": "Question?",
                "options": ["A", "B"],
                "answer": 0,
            }])

        with self.assertRaisesRegex(ValueError, "chỉ số từ 0 đến 3"):
            server.quiz.EnglishQuizGame([{
                "id": "q1",
                "q": "Question?",
                "options": ["A", "B", "C", "D"],
                "answer": True,
            }])


if __name__ == "__main__":
    unittest.main()
