"""HTTP server exposing the exchange as a JSON API plus a web UI.

Run with: python -m tradeapp.server [port]
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .engine import Exchange, TradeError

INDEX = Path(__file__).parent / "static" / "index.html"


def make_handler(exchange):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype="application/json"):
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._send(200, INDEX.read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/state":
                self._send(200, exchange.snapshot())
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/api/trade":
                return self._send(404, {"error": "not found"})
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length) or b"{}")
                if not isinstance(body, dict):
                    raise TradeError("invalid request")
                rec = exchange.trade(body.get("side"), body.get("symbol"), body.get("quantity"))
            except (TradeError, ValueError) as e:
                return self._send(400, {"error": str(e)})
            self._send(200, {"trade": rec, "state": exchange.snapshot()})

        def log_message(self, *args):
            pass

    return Handler


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(Exchange()))
    print(f"TradeApp running at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
