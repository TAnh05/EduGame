"""Server thống nhất cho game Matching + Fill Blank (chỉ dùng thư viện chuẩn).

Chạy:  python server.py
  rồi mở http://localhost:8000

- Matching:     http://localhost:8000/matching.html
- Fill Blank:   http://localhost:8000/fill_blank.html
"""
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from games import matching, fill_blank

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
WEB_DIR = ROOT / "web"

# game_id -> instance (lưu trong RAM)
MATCHING_GAMES: dict[str, matching.MatchingGame] = {}
FILL_GAMES: dict[str, fill_blank.FillBlankGame] = {}


# ---------- Matching ----------
def matching_sample_files() -> list[str]:
    return sorted(p.name for p in DATA_DIR.glob("*matching*.json"))


def matching_api_new(body: dict) -> dict:
    """Tạo ván mới từ file mẫu {file} hoặc JSON tải lên {data}; only_ids = ôn lại câu sai."""
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
    if len(MATCHING_GAMES) > 200:
        MATCHING_GAMES.pop(next(iter(MATCHING_GAMES)))
    MATCHING_GAMES[game.id] = game
    return {**game.public_view(), "title": data.get("chapter_title", "")}


def matching_api_check(body: dict) -> dict:
    game = MATCHING_GAMES.get(body.get("game_id"))
    if game is None:
        raise ValueError("Ván chơi không còn tồn tại, hãy tải lại trang.")
    return game.check(body.get("pairs"))


# ---------- Fill Blank ----------
def fill_sample_files() -> list[str]:
    """Các file *fill_blank*.json trong data/ (kể cả thư mục con), trả về đường dẫn tương đối."""
    return sorted(
        p.relative_to(DATA_DIR).as_posix()
        for p in DATA_DIR.rglob("*fill_blank*.json")
    )


def fill_api_new(body: dict) -> dict:
    """Tạo ván mới từ file mẫu {file} hoặc JSON tải lên {data}; only_ids = ôn lại câu sai."""
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
    if len(FILL_GAMES) > 200:
        FILL_GAMES.pop(next(iter(FILL_GAMES)))
    FILL_GAMES[game.id] = game
    return {**game.public_view(), "title": data.get("chapter_title", "")}


def _fill_game(body: dict) -> fill_blank.FillBlankGame:
    game = FILL_GAMES.get(body.get("game_id"))
    if game is None:
        raise ValueError("Ván chơi không còn tồn tại, hãy tải lại trang.")
    return game


def fill_api_check(body: dict) -> dict:
    return _fill_game(body).check_one(body.get("qid"), body.get("idx"))


def fill_api_result(body: dict) -> dict:
    return _fill_game(body).result()


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

    def do_GET(self):
        path = urlparse(self.path).path

        if path in ("/", "/index.html"):
            return self._send_file(WEB_DIR / "index.html", "text/html; charset=utf-8")

        if path == "/matching.html":
            return self._send_file(WEB_DIR / "matching.html", "text/html; charset=utf-8")
        if path in ("/fill_blank.html", "/fill_blank"):
            return self._send_file(WEB_DIR / "fill_blank.html", "text/html; charset=utf-8")

        if path == "/api/matching/files":
            return self._send(200, {"files": matching_sample_files()})
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
    print("  (Ctrl+C để dừng)")
    try:
        webbrowser.open(f"http://{host}:{port}/")
    except Exception:
        pass
    server.serve_forever()
