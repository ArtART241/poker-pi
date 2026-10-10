# Game loop & timeouts

This page explains what happens over time: how fast the game runs, how long your bot may think, and
what happens when it's slow, crashes or loses its internet connection.

## The recommended bot structure

```
check the token:              GET  /api/v1/bot/me
(optional) register:          GET  /api/v1/bot/tournaments → POST .../register
loop forever:
    try:
        r = GET /api/v1/bot/turn?wait=25        (client timeout: 40 s)
    on network error:
        print the error, sleep 2 s, continue
    if r.status == 204: continue                (not your turn, ask again)
    if r.status != 200: print r.body, sleep 2 s, continue
    state  = parse r.body
    action = decide(state)                      ← your code
    r = POST /api/v1/bot/action {turn_id, ...action}
    if r.status == 422:                         (illegal move: print why, play safe)
        POST /api/v1/bot/action {turn_id, "check" if legal.check else "fold"}
```

All starter bots follow exactly this structure. You only have to replace `decide`.

## Time to think: 15 seconds

From the moment a turn opens, your bot has **15 seconds** to answer (`deadline_ms` tells you how many
milliseconds are left). That's plenty for most strategies, including a few thousand Monte Carlo
simulations.

If you don't answer in time:

1. The server acts for you: **check** if possible, otherwise **fold**. A `player_status` event with
   `"status": "timeout"` is logged.
2. After **3 timeouts in a row**, your bot is **sitting out**. It stays in the tournament, still pays
   blinds and antes, and is folded automatically, but the server only waits **3 seconds** for it
   instead of 15. As soon as your bot answers a turn in time, it's back (`"status": "back"`).

So a crashed bot slowly bleeds chips but never stalls the game for everyone else.

## Disconnected bots

If the server hasn't received **any request** from your bot for **60 seconds**, the bot counts as
**disconnected**. Then the server doesn't wait at all and checks or folds immediately. The moment
your bot sends a request again (e.g. `GET /turn`), it's connected again.

The website shows a bot's connection state with a green dot on the bots page and a label at the table.

> **Before a tournament starts**, make sure your bot is running and polling. A bot that's not
> connected when the tournament begins plays its first hands on autopilot (check/fold).

## Pacing: why tournaments are slow on purpose

Bots decide in milliseconds, which is far too fast for humans to watch. In tournaments the server
therefore waits:

- at least **2 seconds** between two actions,
- **1.5 seconds** before the flop, turn and river are dealt and before the pot is awarded,
- **4 seconds** between hands.

This waiting is **not** your thinking time. Your turn opens immediately and your 15 seconds start
right away. If you answer in 50 ms, the server just keeps your action until the 2 seconds have passed,
so you lose nothing by thinking. Your bot doesn't need to do anything special. It just means
`GET /turn` sometimes takes a little longer to come back.

Practice tables with `"speed": "fast"` have no pauses at all.

## Errors and retries

| Situation | What to do |
|---|---|
| Network error / timeout while waiting for a turn | Wait 1 to 2 seconds, then ask again. Turns don't get lost: if your turn opened in the meantime, the next `GET /turn` returns it immediately. |
| Network error while sending an action | Send **the same** action again. Duplicates are recognized and accepted. |
| `422` | Print `detail`, then send a safe action (check/fold). The turn is still open. |
| `409` | The turn is over. Just continue with the next `GET /turn`. |
| `401` | Wrong token. Stop and fix it. |
| `429` | Too many requests. Sleep a second. You're probably looping without `wait`. |
| `5xx` | Server problem. Wait a few seconds and continue. |

## Rate limit

Each bot may send at most **60 unproductive requests per second**: requests that achieve nothing,
like an empty `GET /turn` (the `204` answer) or a request that fails. Requests that deliver a turn
or an accepted action don't count, so a fast bot at a fast practice table is never slowed down.
You'll only hit the limit if your loop is broken, e.g. calling `/turn` with `wait=0` in a loop
without pausing, or resending a rejected action over and over.

## Several tables at once

A bot can sit at a tournament table and a practice table at the same time. `GET /turn` returns the
most urgent open turn from any table, and `table_id` / `tournament_id` in the state tell you where it
is. If you want to keep tables apart, run two loops, each with `?table_id=...`.

<details>
<summary>Why is there no websocket / push API for bots?</summary>

On purpose, to keep things simple. Long polling works with any HTTP library in any language, goes
through every firewall and proxy, and needs neither threads nor async code. Bots don't need more
than one decision every few seconds, so a push channel wouldn't make anything faster.

(Spectators in the browser do get a push stream, via Server-Sent Events, but it doesn't contain any
information your bot doesn't already get.)
</details>
