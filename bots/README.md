# Starter bots

Each folder holds a complete, runnable bot that uses only the standard library
(C++ additionally needs libcurl). They all work the same way:

1. check the token (`GET /api/v1/bot/me`),
2. register for open tournaments,
3. loop: `GET /api/v1/bot/turn?wait=25` → `decide(state)` → `POST /api/v1/bot/action`.

Change `decide()` to make your bot smarter. Everything else is plumbing.

| Language | Run |
|---|---|
| Python 3.8+ | `python3 python/bot.py [practice]` |
| Java 17+ | `java java/Bot.java [practice]` |
| Go 1.21+ | `cd go && go run . [practice]` |
| C++17 + libcurl | `cd cpp && make && ./bot [practice]` |
| Node.js 18+ | `node javascript/bot.mjs [practice]` |

Set `POKER_TOKEN` (your token) and `POKER_URL` (default `http://localhost:8000`) first.
The full guide is on the website under **Docs** (English + Deutsch).
