import tempfile
import unittest
from pathlib import Path

from solders.pubkey import Pubkey

from tradeapp.accounts import (
    AccountError,
    AccountStore,
    DuplicateAccountError,
    InvalidCredentialsError,
)


class AccountStoreTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = AccountStore(Path(self.temp_dir.name) / "accounts.sqlite3")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_signup_login_and_session(self):
        user = self.store.signup("Person@example.com", "correct horse battery")
        self.assertEqual(user["email"], "person@example.com")
        self.assertEqual(str(Pubkey.from_string(user["walletAddress"])), user["walletAddress"])

        token = self.store.create_session(user["email"])
        self.assertEqual(self.store.get_session(token), user)
        self.assertEqual(self.store.login("PERSON@example.com", "correct horse battery"), user)

        self.store.delete_session(token)
        self.assertIsNone(self.store.get_session(token))

    def test_duplicate_email_and_invalid_password(self):
        self.store.signup("person@example.com", "correct horse battery")
        with self.assertRaises(DuplicateAccountError):
            self.store.signup("PERSON@example.com", "another correct password")
        with self.assertRaises(InvalidCredentialsError):
            self.store.login("person@example.com", "incorrect horse battery")

    def test_signup_rejects_short_password(self):
        with self.assertRaises(AccountError):
            self.store.signup("person@example.com", "short")


if __name__ == "__main__":
    unittest.main()