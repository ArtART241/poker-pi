# Getting started

Welcome to **poker-pi**! The players here aren't people. They're **programs**, and you write one of them.
Your bot connects to the poker server over the internet, gets told when it's its turn, and answers with
a move: fold, check, call or raise. Everyone else can watch the games live in the browser.

You can use **any programming language** that can send HTTP requests: Python, Java, Go, C++,
JavaScript, Rust, C#, Kotlin, and so on. If your language can talk to a website, it can play poker here.

> **Never done web programming?** No problem. The docs assume you know how to program but not how
> the web works. The page [HTTP & REST for beginners](#/docs/web-basics) explains everything you need.
> It's less than you think.

## What you need

1. **A bot token** from the organizer. It's a long secret string like `pk_3Jk9...`. It identifies your bot,
   like a password. Keep it secret.
2. **A programming language** of your choice, installed on your computer.
3. **A computer that stays online** while a tournament is running. Your laptop is fine, and so is
   a Raspberry Pi or a small server.

The server address is:

```
https://poker.example.com
```

## The idea in one picture

Your bot does only two things, over and over:

```
   your bot                                      poker server
      |                                               |
      |  GET /api/v1/bot/turn?wait=25  -------------> |   "Is it my turn?"
      |                                               |   (the server keeps the request open
      |                                               |    until it IS your turn, max 25 s)
      | <-------------  200 OK + game state (JSON)    |   "Yes! You have Ah Kd, pot is 60..."
      |                                               |
      |  POST /api/v1/bot/action  -------------------> |   {"turn_id": "...", "action": "call"}
      | <-------------  200 OK                        |   "Got it."
      |                                               |
      |  GET /api/v1/bot/turn?wait=25  -------------> |   ...and again
```

If it's not your turn within 25 seconds, the server answers **204 No Content** (an empty answer).
Then you simply ask again. That's the whole protocol.

## Quickstart (10 minutes)

### Step 1: Test your token

Open a terminal and run this (replace the token with yours):

```bash
curl -H "Authorization: Bearer pk_YOUR_TOKEN" https://poker.example.com/api/v1/bot/me
```

You should see something like `{"id":"b_...","name":"YourBot",...}`. If you get
`{"detail":"Invalid or revoked token."}`, check that you copied the whole token.

<details>
<summary>What is curl and do I have it?</summary>

`curl` is a small command line program that sends HTTP requests. It's preinstalled on macOS, Linux
and Windows 10/11 (in PowerShell type `curl.exe` instead of `curl`, because `curl` there is an alias
for something else).

- `-H "Name: value"` adds a **header** to the request. Here it sends your token.
- Without `-X` curl sends a `GET` request.
- `-X POST -d '{"a":1}' -H "Content-Type: application/json"` would send a POST with a JSON body.

You never need curl for your bot. It's just handy for trying things out.
</details>

### Step 2: Get a starter bot

The repository has a ready-to-run starter bot for **Python, Java, Go, C++ and JavaScript** in the
`bots/` folder. Each is a single file of about 150 lines and uses only the standard library
(C++ needs libcurl). Pick your language and copy that folder.

| Language | File | Run with |
|---|---|---|
| Python 3.8+ | `bots/python/bot.py` | `python3 bot.py` |
| Java 17+ | `bots/java/Bot.java` | `java Bot.java` |
| Go 1.21+ | `bots/go/main.go` | `go run .` |
| C++17 | `bots/cpp/bot.cpp` | `make && ./bot` |
| Node.js 18+ | `bots/javascript/bot.mjs` | `node bot.mjs` |

The [language guides](#/docs/language-guides) explain the setup for each language in detail.

### Step 3: Tell the bot your token

The starter bots read two **environment variables**:

- `POKER_TOKEN`: your token (required)
- `POKER_URL`: the server address (optional, `http://localhost:8000` if not set)

macOS / Linux:

```bash
export POKER_TOKEN="pk_YOUR_TOKEN"
export POKER_URL="https://poker.example.com"
```

Windows PowerShell:

```powershell
$env:POKER_TOKEN = "pk_YOUR_TOKEN"
$env:POKER_URL = "https://poker.example.com"
```

<details>
<summary>What is an environment variable, and why not just put the token in the code?</summary>

An environment variable is a named value that lives in your terminal session. Every program you start
from that terminal can read it (`os.environ` in Python, `System.getenv` in Java, `os.Getenv` in Go,
`std::getenv` in C++, `process.env` in Node).

Keeping the token out of the source code means you can share your code (on GitHub, say) without
leaking your token. Anyone who has your token can play **as your bot**.

The variables only last as long as the terminal window. Put the `export` lines into `~/.zshrc` /
`~/.bashrc` (macOS/Linux) to keep them, or use a `.env` file your program reads (and don't commit it!).

In an IDE (IntelliJ, VS Code, CLion, ...) you can set environment variables in the run configuration.
</details>

### Step 4: Practice against house bots

Start the bot with the `practice` argument:

```bash
python3 bot.py practice
```

This opens a **private practice table** against three built-in bots:

- **Randy Random** plays randomly.
- **Carl Callstation** calls everything.
- **Tina Tight** only plays good hands.

The bot prints a link like `https://poker.example.com/#/table/p_ab12cd`. Open it to watch your
bot play. Practice results don't count for anything, so break things as much as you like.

### Step 5: Join a tournament

Tournaments are scheduled in advance; you can see them in the **Lobby**. The starter bots
automatically register for every open tournament when they start, and they check for new ones every
5 minutes. To join, just keep your bot running until the tournament begins.

When the tournament starts, your turns arrive through the same `GET /turn` loop, so you don't need
any extra code.

### Step 6: Make it smart

Open the starter bot and find the function `decide(state)`. That's the only place you need to change.
It gets the full game state and returns an action. The starter strategy is deliberately dumb.
[Strategy tips](#/docs/strategy) has plenty of ideas.

## House rules

- **One bot per person per tournament.** You can have several bots, but only one of them
  may play in any given tournament.
- **No teamwork between bots.** Bots must not share information or work together (that's called
  "collusion" in poker).
- **Be nice to the server.** It's a Raspberry Pi. Use the long-poll (`wait=25`) and don't send
  hundreds of requests per second. Empty requests are limited to 60 per second.
- **Keep your token secret.** If it leaks, ask the organizer for a new one.
- **Bugs in the server** are not a strategy. Report them, and you get eternal glory.

## Where to go next

- [HTTP & REST for beginners](#/docs/web-basics): requests, JSON, status codes, bearer tokens and long polling.
- [Poker rules](#/docs/poker-rules): how Texas Hold'em and the tournaments work.
- [API reference](#/docs/api-reference): every endpoint and field.
- [Game loop & timeouts](#/docs/game-loop): what happens when your bot is slow or crashes.
- **Swagger UI** at [/docs](https://poker.example.com/docs): try every endpoint in the browser.
  Click *Authorize*, paste your token, then *Try it out*.
