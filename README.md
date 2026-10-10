# poker-pi

A No-Limit Texas Hold'em tournament server where the players are **bots**: programs written in
any language, talking to the server over plain HTTP + JSON. Spectators watch the games
live in the browser, and every hand can be replayed afterwards.

```
bots (any language) ──HTTP──▶ poker-server (FastAPI) ──▶ SQLite
browsers ───────────HTTP/SSE──▶      │
                                     └─ serves the spectator website
```

## For bot authors

The documentation (English and German) is on the website under **Docs**, and in
[`docs/en`](docs/en) / [`docs/de`](docs/de). A bot needs a token from the organizer, an HTTP client
and a JSON parser; the language is up to the author.

The API in two calls:

```
GET  /api/v1/bot/turn?wait=25    → waits for a turn, returns the game state (204 = ask again)
POST /api/v1/bot/action          → {"turn_id": "...", "action": "fold|check|call|raise", "amount": 120}
```

There's a Swagger UI at `/docs` and the spec is in [`docs/openapi.yaml`](docs/openapi.yaml).

## Quick demo

```bash
scripts/demo.sh
```

This sets everything up on the first run, starts the server on http://localhost:8000, lets the
test bots in `bots/` play tournament after tournament, and stops everything on Ctrl+C.
`PACE=0.5 scripts/demo.sh` plays faster.

## For the admin

See [`docs/HOSTING.md`](docs/HOSTING.md): local development, the admin CLI, deploying on the
Raspberry Pi behind a Cloudflare Tunnel, and backups.

```bash
cd server && python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest
.venv/bin/python -m poker_pi.admin create-bot "MyBot" --owner Me
.venv/bin/python -m poker_pi.admin create-tournament --name "Test" --start "+5m"
.venv/bin/python -m poker_pi        # http://localhost:8000
```

Or with Docker: `docker compose up -d --build`.

## Repository layout

| Path | What |
|---|---|
| `server/poker_pi/engine/` | Pure poker rules: betting, side pots, showdown (no I/O) |
| `server/poker_pi/tables/` | Async table runner: turns, timeouts, pacing, house bots, live events |
| `server/poker_pi/tournament/` | Scheduling, blinds, eliminations, placements, practice tables |
| `server/poker_pi/api/` | FastAPI routes: bot API (bearer token) and public API (+ SSE stream) |
| `server/poker_pi/store/` | SQLite persistence |
| `server/poker_pi/admin.py` | Admin CLI |
| `server/tests/` | Engine tests (incl. property-based) and API integration tests |
| `web/` | Svelte spectator website (lobby, live table, replays, leaderboard, docs) |
| `bots/` | Simple Python test bots (used by the demo) |
| `docs/` | Bot author guide (en/de), hosting guide, openapi.yaml |
| `deploy/` | Compose file for the Pi with a Cloudflare Tunnel |
