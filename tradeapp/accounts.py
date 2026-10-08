"""Persistent user accounts and password-encrypted Solana keypairs."""
import hashlib
import hmac
import os
import secrets
import sqlite3
import time

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from solders.keypair import Keypair

PASSWORD_ITERATIONS = 600_000
SESSION_TTL = 7 * 24 * 60 * 60


class AccountError(ValueError):
    pass


class DuplicateAccountError(AccountError):
    pass


class InvalidCredentialsError(AccountError):
    pass


def _email(value):
    if not isinstance(value, str):
        raise AccountError("enter a valid email address")
    address = value.strip().lower()
    if (len(address) > 254 or address.count("@") != 1 or
            any(char.isspace() for char in address)):
        raise AccountError("enter a valid email address")
    local, domain = address.split("@")
    if not local or not domain or "." not in domain:
        raise AccountError("enter a valid email address")
    return address


def _password(value):
    if not isinstance(value, str) or not 12 <= len(value) <= 1024:
        raise AccountError("password must be between 12 and 1024 characters")
    return value


def _derive(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS, dklen=32
    )


class AccountStore:
    def __init__(self, path):
        self.path = os.fspath(path)
        if self.path != ":memory:":
            parent = os.path.dirname(os.path.abspath(self.path))
            os.makedirs(parent, exist_ok=True)
            descriptor = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
            os.close(descriptor)
            os.chmod(self.path, 0o600)
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    email TEXT PRIMARY KEY,
                    password_salt BLOB NOT NULL,
                    password_hash BLOB NOT NULL,
                    wallet_salt BLOB NOT NULL,
                    wallet_nonce BLOB NOT NULL,
                    encrypted_secret_key BLOB NOT NULL,
                    wallet_address TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    email TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                    expires_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires_at);
            """)

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def signup(self, email, password):
        email = _email(email)
        password = _password(password)

        password_salt = secrets.token_bytes(16)
        password_hash = _derive(password, password_salt)
        wallet_salt = secrets.token_bytes(16)
        wallet_key = _derive(password, wallet_salt)
        keypair = Keypair()
        nonce = secrets.token_bytes(12)
        encrypted_secret = AESGCM(wallet_key).encrypt(
            nonce, keypair.to_bytes(), email.encode("utf-8")
        )

        try:
            with self._connect() as connection:
                connection.execute(
                    """INSERT INTO users (
                        email, password_salt, password_hash, wallet_salt,
                        wallet_nonce, encrypted_secret_key, wallet_address, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (email, password_salt, password_hash, wallet_salt, nonce,
                     encrypted_secret, str(keypair.pubkey()), int(time.time())),
                )
        except sqlite3.IntegrityError as error:
            raise DuplicateAccountError("an account with this email already exists") from error

        return {"email": email, "walletAddress": str(keypair.pubkey())}

    def login(self, email, password):
        email = _email(email)
        password = _password(password)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT password_salt, password_hash FROM users WHERE email = ?",
                (email,),
            ).fetchone()

        salt = row["password_salt"] if row else bytes(16)
        expected = row["password_hash"] if row else bytes(32)
        actual = _derive(password, salt)
        if row is None or not hmac.compare_digest(actual, expected):
            raise InvalidCredentialsError("email or password is incorrect")
        return self.get_account(email)

    def get_account(self, email):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT email, wallet_address FROM users WHERE email = ?", (email,)
            ).fetchone()
        if row is None:
            return None
        return {"email": row["email"], "walletAddress": row["wallet_address"]}

    def create_session(self, email):
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
        expires_at = int(time.time()) + SESSION_TTL
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (int(time.time()),))
            connection.execute(
                "INSERT INTO sessions (token_hash, email, expires_at) VALUES (?, ?, ?)",
                (token_hash, email, expires_at),
            )
        return token

    def get_session(self, token):
        if not token:
            return None
        token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
        with self._connect() as connection:
            row = connection.execute(
                """SELECT users.email, users.wallet_address
                   FROM sessions JOIN users USING (email)
                   WHERE sessions.token_hash = ? AND sessions.expires_at > ?""",
                (token_hash, int(time.time())),
            ).fetchone()
        if row is None:
            return None
        return {"email": row["email"], "walletAddress": row["wallet_address"]}

    def delete_session(self, token):
        if not token:
            return
        token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
        with self._connect() as connection:
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))