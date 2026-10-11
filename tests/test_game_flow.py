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
        server.FLOW_STATE["fill_blank_done"] = False
        server.ACTIVE_FILL_GAME_ID = None
        server.ACTIVE_MATCHING_GAME_ID = None

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
        finally:
            connection.close()
            httpd.shutdown()
            httpd.server_close()
            thread.join()

    def test_result_pages_provide_only_supported_continuation(self):
        root = Path(server.ROOT)
        fill_page = (root / "web" / "fill_blank.html").read_text(encoding="utf-8")
        matching_page = (root / "web" / "matching.html").read_text(encoding="utf-8")

        self.assertIn('id="continue"', fill_page)
        self.assertIn('if (!reviewOnly)', fill_page)
        self.assertIn("window.location.href = `/matching.html?subject=", fill_page)
        self.assertIn("encodeURIComponent(game.subject)", fill_page)
        self.assertIn("'Tiếp tục'", matching_page)
        self.assertIn("new URLSearchParams(window.location.search)", matching_page)
        self.assertIn("Bạn đã hoàn thành các game hiện có.", matching_page)
        self.assertIn("Game trắc nghiệm chưa được triển khai.", matching_page)


if __name__ == "__main__":
    unittest.main()
