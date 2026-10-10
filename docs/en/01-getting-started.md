# Getting started

poker-pi runs No-Limit Texas Hold'em tournaments in which every player is a program. Each
participant writes a bot that connects to the server over HTTP, receives the game state whenever
a decision is due, and answers with an action: fold, check, call or raise. Spectators follow the
games live in the browser.

Any programming language works, as long as it can send HTTP requests and read and write JSON.
The server makes no assumptions about how a bot is implemented.

> The documentation assumes general programming experience but no background in web development.
> [HTTP basics](#/docs/web-basics) covers the few web concepts that are needed.

## Requirements

1. **A bot token.** The organizer issues one per bot. It is a long secret string such as
   `pk_3Jk9...` that identifies the bot, and should be treated like a password.
2. **An HTTP client and a JSON library** in the language of choice. Most languages include both
   in their standard library or in a widely used package.
3. **A machine that stays online** for the duration of a tournament. A laptop, a Raspberry Pi
   or a small server are all suitable.

Server address:

```
https://poker.example.com
```

## How a bot works

A bot repeats two requests for as long as it runs:

```
   bot                                           poker server
    |                                                 |
    |  GET /api/v1/bot/turn?wait=25  ---------------> |   is a decision due?
    |                                                 |   (the request is held open until
    |                                                 |    it is the bot's turn, max. 25 s)
    | <---------------  200 OK + game state (JSON)    |
    |                                                 |
    |  POST /api/v1/bot/action  ---------------------> |   {"turn_id": "...", "action": "call"}
    | <---------------  200 OK                        |
    |                                                 |
    |  GET /api/v1/bot/turn?wait=25  ---------------> |   ...and so on
```

If no decision is due within 25 seconds, the server answers with **204 No Content** (an empty
response), and the bot asks again. This is the entire protocol; everything else is optional.

In pseudocode:

```
loop forever:
    response = GET /api/v1/bot/turn?wait=25           (client timeout: 40 s)
    if response.status == 204: continue
    state  = parse JSON
    action = decide(state)                             (the bot's own logic)
    POST /api/v1/bot/action  { "turn_id": state.turn_id, ...action }
```

Every request carries the token in the header `Authorization: Bearer <token>`.

## Trying the API by hand

The steps below use `curl`, a command-line HTTP client that ships with macOS, Linux and
Windows 10/11 (in PowerShell it is called as `curl.exe`). They show exactly what a bot
exchanges with the server.

**1. Check the token.**

```bash
curl -H "Authorization: Bearer pk_TOKEN" https://poker.example.com/api/v1/bot/me
```

The answer contains the bot's name. `{"detail":"Invalid or revoked token."}` means the token was
not copied completely.

**2. Start a practice table** against built-in opponents (results do not count):

```bash
curl -X POST -H "Authorization: Bearer pk_TOKEN" https://poker.example.com/api/v1/bot/practice
```

The response includes a `watch_url` for following the table in the browser.

**3. Ask for a turn.**

```bash
curl -H "Authorization: Bearer pk_TOKEN" "https://poker.example.com/api/v1/bot/turn?wait=25"
```

The JSON contains the hole cards, the board, the pot and, most importantly, `legal`: the moves
that are allowed right now.

**4. Send an action** with the `turn_id` from step 3:

```bash
curl -X POST -H "Authorization: Bearer pk_TOKEN" -H "Content-Type: application/json" \
     -d '{"turn_id": "t_...", "action": "call"}' \
     https://poker.example.com/api/v1/bot/action
```

A decision has to arrive within 15 seconds, otherwise the server checks or folds on the bot's
behalf. Doing this by hand works but is tight; it is mainly useful to see the data.

<details>
<summary>curl options used above</summary>

- `-H "Name: value"` adds a request header (here: the token, and the body format).
- `-X POST` changes the method from the default `GET` to `POST`.
- `-d '...'` sends the given text as the request body.
</details>

<details>
<summary>Keeping the token out of the source code</summary>

A common approach is to read the token from an environment variable (for example `POKER_TOKEN`)
or from a configuration file that is excluded from version control. Anyone holding the token can
play as that bot, so it should not end up in a public repository. If a token leaks, the organizer
can issue a new one; the old token stops working immediately.
</details>

## Swagger UI

The server documents itself at [/docs](https://poker.example.com/docs). After clicking
*Authorize* and entering the token, every endpoint can be called from the browser with
*Try it out*. Each call also shows the equivalent `curl` command. The machine-readable
specification is available at [/openapi.yaml](https://poker.example.com/openapi.yaml).

## Practice and tournaments

- **Practice tables** (`POST /api/v1/bot/practice`) seat a bot against built-in opponents and can
  be started at any time. They are the intended way to test a bot.
- **Tournaments** are scheduled in advance and listed in the lobby. A bot signs up with
  `POST /api/v1/bot/tournaments/{id}/register` and only needs to be running and polling when the
  tournament starts. Turns arrive through the same `GET /turn` loop.

## House rules

- One bot per person per tournament.
- Bots must not share information or cooperate with each other.
- The server is a Raspberry Pi: bots should use the long-poll (`wait=25`) rather than polling in
  a tight loop. Requests that achieve nothing are limited to 60 per second.
- Tokens are personal and should be kept private.
- Server bugs should be reported rather than exploited.

## Further reading

- [HTTP basics](#/docs/web-basics): requests, JSON, status codes, bearer tokens and long polling.
- [Poker rules](#/docs/poker-rules): Texas Hold'em and the tournament format.
- [API reference](#/docs/api-reference): every endpoint and field.
- [Game loop & timeouts](#/docs/game-loop): pacing, time limits and failure handling.
- [Strategy notes](#/docs/strategy): ideas for better decisions.
- [FAQ](#/docs/faq): common errors and their causes.
