# tradeapp
A trading app

A simulated exchange for tokenized real-world assets (treasuries, real estate, gold, ...) with a web UI.

Run: `python -m tradeapp.server [port]` then open http://127.0.0.1:8000
Test: `python -m unittest discover tests`

API: `GET /api/state`, `POST /api/trade` with `{"side":"buy|sell","symbol":"GOLD","quantity":"1.5"}`.
