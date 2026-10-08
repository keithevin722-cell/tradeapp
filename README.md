# tradeapp

A Solana account and wallet-address prototype.

Install dependencies with `python -m pip install -r requirements.txt`, then run
`python -m tradeapp.server [port]` and open http://127.0.0.1:8000. Accounts are
stored in `tradeapp.sqlite3`; set `TRADEAPP_DB` to choose another database path.
The database is created with owner-only file permissions and is ignored by Git.

People can create an account with an email and a password of at least 12
characters, sign in, and view their generated Solana address. Passwords are
hashed, wallet secret keys are encrypted with a key derived from each user's
password, and session tokens are stored hashed. There is no password recovery;
losing the password means losing access to the encrypted wallet key. Set
`TRADEAPP_COOKIE_SECURE=1` when serving over HTTPS.

This is an initial prototype, not a production custody service. It does not
monitor deposits, connect to Solana RPC, or send transactions. Do not send real
funds to the displayed addresses. Production use needs security review, backup
and recovery design, and deployment behind HTTPS.

Run tests with `python -m unittest discover tests`.
