"""Server nhỏ cho game Điền vào chỗ trống (chỉ dùng thư viện chuẩn, không cần cài thêm).

Chạy:  py server_fill_blank.py     rồi mở http://localhost:8001
Muốn gộp vào server.py của nhóm: chép api_new/api_check/api_result + 3 tuyến POST, 1 tuyến GET.
"""
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from games import fill_blank

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
GAMES: dict[str, fill_blank.FillBlankGame] = {}   # game_id -> ván đang chơi (lưu trong RAM)


def sample_files() -> list[str]:
    """Các file *fill_blank*.json trong data/ (kể cả data/by_game/), trả về đường dẫn tương đối."""
    return sorted(p.relative_to(DATA_DIR).as_posix() for p in DATA_DIR.rglob("*fill_blank*.json"))


def api_new(body: dict) -> dict:
    """Tạo ván mới từ file mẫu {file} hoặc JSON tải lên {data}; only_ids = ôn lại câu sai."""
    if "data" in body:
        data = body["data"]
    else:
        name = body.get("file")
        if name not in sample_files():          # chỉ cho đọc file trong danh sách (chống path traversal)
            raise ValueError("File không tồn tại.")
        data = json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
    items = fill_blank.get_fill_items(data)
    if body.get("only_ids"):
        items = [it for it in items if it["id"] in body["only_ids"]]
    game = fill_blank.FillBlankGame(items)
    if len(GAMES) > 200:
        GAMES.pop(next(iter(GAMES)))
    GAMES[game.id] = game
    return {**game.public_view(), "title": data.get("chapter_title", "")}


def _game(body: dict) -> fill_blank.FillBlankGame:
    game = GAMES.get(body.get("game_id"))
    if game is None:
        raise ValueError("Ván chơi không còn tồn tại, hãy tải lại trang.")
    return game


def api_check(body: dict) -> dict:
    return _game(body).check_one(body.get("qid"), body.get("idx"))


def api_result(body: dict) -> dict:
    return _game(body).result()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body, ctype="application/json; charset=utf-8"):
        raw = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, (ROOT / "web" / "fill_blank.html").read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/files":
            self._send(200, {"files": sample_files()})
        else:
            self._send(404, {"error": "Not found"})

    def do_POST(self):
        routes = {"/api/fill_blank/new": api_new, "/api/fill_blank/check": api_check,
                  "/api/fill_blank/result": api_result}
        if self.path not in routes:
            return self._send(404, {"error": "Not found"})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            self._send(200, routes[self.path](body))
        except (ValueError, KeyError, TypeError, AttributeError) as e:   # JSONDecodeError là ValueError
            self._send(400, {"error": str(e)})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8001), Handler)
    print("Game điền chỗ trống: http://localhost:8001  (Ctrl+C để dừng)")
    webbrowser.open("http://localhost:8001")
    server.serve_forever()
