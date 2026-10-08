"""HTTP server exposing the exchange as a JSON API plus a web UI.

Run with: python -m tradeapp.server [port]
"""
import json
import os
import sys
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .accounts import (
    AccountError,
    AccountStore,
    DuplicateAccountError,
    InvalidCredentialsError,
    SESSION_TTL,
)

INDEX = Path(__file__).parent / "static" / "index.html"


def make_handler(accounts):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype="application/json", headers=()):
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            for name, value in headers:
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(data)

        def _session_token(self):
            cookies = SimpleCookie()
            try:
                cookies.load(self.headers.get("Cookie", ""))
            except CookieError:
                return None
            cookie = cookies.get("tradeapp_session")
            return cookie.value if cookie else None

        def _session_cookie(self, token, max_age):
            secure = os.environ.get("TRADEAPP_COOKIE_SECURE", "").lower() in ("1", "true", "yes")
            value = (f"tradeapp_session={token}; Path=/; HttpOnly; SameSite=Strict; "
                     f"Max-Age={max_age}")
            if secure:
                value += "; Secure"
            return ("Set-Cookie", value)

        def _read_json(self):
            length = int(self.headers.get("Content-Length", 0))
            if length < 0 or length > 16_384:
                raise ValueError("request is too large")
            if self.headers.get_content_type() != "application/json":
                raise ValueError("content type must be application/json")
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError("invalid request")
            return body

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._send(200, INDEX.read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/auth/me":
                user = accounts.get_session(self._session_token())
                if user is None:
                    self._send(401, {"error": "sign in to continue"})
                else:
                    self._send(200, user)
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path == "/api/auth/logout":
                accounts.delete_session(self._session_token())
                expired_cookie = self._session_cookie("", 0)
                return self._send(200, {"ok": True}, headers=(expired_cookie,))
            if self.path not in ("/api/auth/signup", "/api/auth/login"):
                return self._send(404, {"error": "not found"})
            try:
                body = self._read_json()
                if self.path == "/api/auth/signup":
                    user = accounts.signup(body.get("email"), body.get("password"))
                    code = 201
                else:
                    user = accounts.login(body.get("email"), body.get("password"))
                    code = 200
                token = accounts.create_session(user["email"])
            except DuplicateAccountError as error:
                return self._send(409, {"error": str(error)})
            except InvalidCredentialsError as error:
                return self._send(401, {"error": str(error)})
            except (AccountError, ValueError, UnicodeDecodeError) as error:
                return self._send(400, {"error": str(error)})
            return self._send(code, user, headers=(self._session_cookie(token, SESSION_TTL),))

        def log_message(self, *args):
            pass

    return Handler


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    host = os.environ.get("TRADEAPP_HOST", "0.0.0.0")
    db_path = os.environ.get("TRADEAPP_DB", "tradeapp.sqlite3")
    accounts = AccountStore(db_path)
    server = ThreadingHTTPServer((host, port), make_handler(accounts))
    print(f"TradeApp running at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
