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
        account = {"email": user["email"], "walletAddress": user["walletAddress"]}
        self.assertEqual(self.store.get_session(token), account)
        self.assertEqual(self.store.login("PERSON@example.com", "correct horse battery"), account)

        self.store.delete_session(token)
        self.assertIsNone(self.store.get_session(token))

    def test_reset_password_preserves_wallet_and_rotates_recovery_code(self):
        user = self.store.signup("person@example.com", "correct horse battery")
        old_token = self.store.create_session(user["email"])

        reset = self.store.reset_password(
            user["email"], user["recoveryCode"], "a newer correct password"
        )
        self.assertEqual(reset["walletAddress"], user["walletAddress"])
        self.assertNotEqual(reset["recoveryCode"], user["recoveryCode"])
        self.assertIsNone(self.store.get_session(old_token))
        with self.assertRaises(InvalidCredentialsError):
            self.store.login(user["email"], "correct horse battery")
        self.assertEqual(
            self.store.login(user["email"], "a newer correct password")["walletAddress"],
            user["walletAddress"],
        )
        with self.assertRaises(InvalidCredentialsError):
            self.store.reset_password(
                user["email"], user["recoveryCode"], "yet another correct password"
            )

    def test_reset_password_rejects_wrong_recovery_code(self):
        user = self.store.signup("person@example.com", "correct horse battery")
        with self.assertRaises(InvalidCredentialsError):
            self.store.reset_password(
                user["email"], "x" * len(user["recoveryCode"]), "a newer correct password"
            )

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