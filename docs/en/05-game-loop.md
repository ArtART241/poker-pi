# Game loop & timeouts

This page describes the timing of the game: how fast it runs, how long a bot may take for a
decision, and what happens when a bot is slow, crashes or loses its connection.

## The recommended bot structure

```
check the token:              GET  /api/v1/bot/me
(optional) register:          GET  /api/v1/bot/tournaments → POST .../register
loop forever:
    try:
        r = GET /api/v1/bot/turn?wait=25        (client timeout: 40 s)
    on network error:
        print the error, sleep 2 s, continue
    if r.status == 204: continue                (no decision due, ask again)
    if r.status != 200: print r.body, sleep 2 s, continue
    state  = parse r.body
    action = decide(state)                      ← the bot's own logic
    r = POST /api/v1/bot/action {turn_id, ...action}
    if r.status == 422:                         (illegal move: print why, play safe)
        POST /api/v1/bot/action {turn_id, "check" if legal.check else "fold"}
```

Everything except `decide` is plumbing that rarely needs to change.

## Time to think: 15 seconds

From the moment a turn opens, a bot has **15 seconds** to answer (`deadline_ms` holds the remaining
milliseconds). This is sufficient for most strategies, including several thousand Monte Carlo
simulations.

If no answer arrives in time:

1. The server acts on the bot's behalf: **check** if possible, otherwise **fold**. A `player_status` event with
   `"status": "timeout"` is logged.
2. After **3 timeouts in a row**, the bot is **sitting out**. It stays in the tournament, still pays
   blinds and antes, and is folded automatically, but the server only waits **3 seconds** for it
   instead of 15. As soon as the bot answers a turn in time, it is back (`"status": "back"`).

A crashed bot therefore loses chips slowly but never stalls the game.

## Disconnected bots

If the server has not received **any request** from a bot for **60 seconds**, the bot counts as
**disconnected**. The server then no longer waits for it and checks or folds immediately. The next
request from the bot (e.g. `GET /turn`) marks it as connected again.

The website shows a bot's connection state with a green dot on the bots page and a label at the table.

> A bot should be running and polling **before a tournament starts**. A bot that is not connected
> at the start plays its first hands on autopilot (check/fold).

## Pacing: why tournaments are slow on purpose

Bots decide in milliseconds, which is too fast for spectators. In tournaments the server
therefore waits:

- at least **2 seconds** between two actions,
- **1.5 seconds** before the flop, turn and river are dealt and before the pot is awarded,
- **4 seconds** between hands.

These pauses do **not** reduce the decision time. A turn opens immediately and its 15 seconds start
right away; an answer that arrives after 50 ms is simply held until the 2 seconds have passed. No
special handling is required on the bot side; `GET /turn` merely returns a little later.

Practice tables with `"speed": "fast"` have no pauses at all.

## Errors and retries

| Situation | What to do |
|---|---|
| Network error / timeout while waiting for a turn | Wait 1 to 2 seconds, then ask again. Turns are not lost: an open turn is returned immediately by the next `GET /turn`. |
| Network error while sending an action | Send **the same** action again. Duplicates are recognized and accepted. |
| `422` | Print `detail`, then send a safe action (check/fold). The turn is still open. |
| `409` | The turn is over; continue with the next `GET /turn`. |
| `401` | Invalid token; retrying will not help. |
| `429` | Too many requests without effect, usually a loop without `wait`. Pause for a second. |
| `5xx` | Server problem. Wait a few seconds and continue. |

## Rate limit

Each bot may send at most **60 unproductive requests per second**: requests that achieve nothing,
like an empty `GET /turn` (the `204` answer) or a request that fails. Requests that deliver a turn
or an accepted action do not count, so a fast bot at a fast practice table is never slowed down.
The limit is only reached by a broken loop, e.g. calling `/turn` with `wait=0` in a loop
without pausing, or resending a rejected action over and over.

## Several tables at once

A bot can sit at a tournament table and a practice table at the same time. `GET /turn` returns the
most urgent open turn from any table; `table_id` / `tournament_id` in the state identify the table.
To keep tables apart, two loops can be run, each with `?table_id=...`.

<details>
<summary>Why is there no websocket / push API for bots?</summary>

Long polling works with any HTTP library, passes through firewalls and proxies, and needs neither
threads nor async code. Bots make at most one decision every few seconds, so a push channel would
not make anything faster.

(Spectators in the browser receive a push stream via Server-Sent Events, but it contains no
information beyond what bots already receive.)
</details>
