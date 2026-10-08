import http.cookiejar
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from solders.pubkey import Pubkey

from tradeapp.accounts import AccountStore
from tradeapp.server import make_handler


class AuthApiTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        store = AccountStore(Path(self.temp_dir.name) / "accounts.sqlite3")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(store))
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()
        self.temp_dir.cleanup()

    def request(self, path, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json"} if data else {},
            method="POST" if data else "GET",
        )
        with self.opener.open(request) as response:
            return response.status, json.loads(response.read())

    def test_signup_session_and_logout(self):
        status, user = self.request("/api/auth/signup", {
            "email": "person@example.com",
            "password": "correct horse battery",
        })
        self.assertEqual(status, 201)
        self.assertEqual(str(Pubkey.from_string(user["walletAddress"])), user["walletAddress"])
        self.assertEqual(self.request("/api/auth/me"), (200, user))

        status, _ = self.request("/api/auth/logout", {})
        self.assertEqual(status, 200)
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request("/api/auth/me")
        self.assertEqual(error.exception.code, 401)
        error.exception.close()

    def test_invalid_login_does_not_create_session(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request("/api/auth/login", {
                "email": "person@example.com",
                "password": "correct horse battery",
            })
        self.assertEqual(error.exception.code, 401)
        error.exception.close()


if __name__ == "__main__":
    unittest.main()