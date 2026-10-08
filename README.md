# tradeapp

A Solana account and wallet-address prototype.

Install dependencies with `python -m pip install -r requirements.txt`, then run
`python -m tradeapp.server [port]` and open http://127.0.0.1:8000. Accounts are
stored in `tradeapp.sqlite3`; set `TRADEAPP_DB` to choose another database path.
The database is created with owner-only file permissions and is ignored by Git.

People can create an account with an email and a password of at least 12
characters, sign in, and view their generated Solana address. Passwords are
hashed, wallet secret keys are encrypted with a key derived from each user's
password, and session tokens are stored hashed. Signup emails a one-time
recovery code when SMTP is configured; otherwise the code is displayed once in
the browser. Users must keep the code private. It can reset the password,
preserves the same wallet, rotates the recovery code, and revokes existing
sessions. Users who lose both their password and recovery code cannot recover
the wallet. Existing accounts created before recovery codes were added do not
have recovery enabled. Set
`TRADEAPP_COOKIE_SECURE=1` when serving over HTTPS.

Configure `TRADEAPP_SMTP_HOST` and `TRADEAPP_SMTP_FROM` to send recovery emails.
Optional settings are `TRADEAPP_SMTP_PORT` (default `587`),
`TRADEAPP_SMTP_USERNAME`, `TRADEAPP_SMTP_PASSWORD`, and
`TRADEAPP_SMTP_SSL=1` for implicit TLS. SMTP uses STARTTLS by default. Keep
credentials in the deployment environment, not source control. If delivery is
unavailable, the code is shown once as a fallback and is not logged.

This is an initial prototype, not a production custody service. It does not
monitor deposits, connect to Solana RPC, or send transactions. Do not send real
funds to the displayed addresses. Production use needs security review, backup
and recovery design, and deployment behind HTTPS.

Run tests with `python -m unittest discover tests`.
