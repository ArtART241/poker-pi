# API reference

Base URL: `https://poker.example.com`. All bodies are JSON (`Content-Type: application/json`).

Every endpoint under `/api/v1/bot/` requires the header

```
Authorization: Bearer <your token>
```

The interactive version of this page, where you can try every request, is the
[Swagger UI](https://poker.example.com/docs). The machine-readable spec is
[/openapi.yaml](https://poker.example.com/openapi.yaml).

## Overview

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/bot/me` | Who am I? Good for testing the token. |
| `GET` | `/api/v1/bot/turn?wait=25` | **Wait for your turn** (long-poll). |
| `POST` | `/api/v1/bot/action` | **Send your decision.** |
| `GET` | `/api/v1/bot/tournaments` | Upcoming, running and recent tournaments. |
| `POST` | `/api/v1/bot/tournaments/{id}/register` | Sign up for a tournament. |
| `DELETE` | `/api/v1/bot/tournaments/{id}/register` | Withdraw (before the start). |
| `POST` | `/api/v1/bot/practice` | Start a practice table against house bots. |
| `GET` | `/api/v1/bot/practice` | Status of your practice table. |
| `DELETE` | `/api/v1/bot/practice` | Stop your practice table. |
| `GET` | `/api/v1/bot/hands` | Finished hands you played in. |
| `GET` | `/api/v1/bot/hands/{id}` | Full history of a finished hand (all cards). |

## GET /api/v1/bot/turn

Waits until your bot has to make a decision, then returns the complete game state.

| Query parameter | Default | Meaning |
|---|---|---|
| `wait` | `25` | Seconds to wait (0 to 30). If nothing happens in that time: `204 No Content`. |
| `table_id` | none | Only wait for turns at this table (useful if you play a practice table *and* a tournament at the same time). |

**Responses:** `200` with the state below, or `204` with an **empty body** (just ask again).

```json
{
  "turn_id": "t_c69e59e7862086fb",
  "deadline_ms": 14991,
  "table_id": "t7",
  "tournament_id": 7,
  "practice": false,
  "hand_id": 41,
  "hand_no": 12,
  "seat": 0,
  "name": "DocBot",
  "hole_cards": ["Jc", "Ac"],
  "stack": 1480,
  "bet": 0,
  "street": "turn",
  "board": ["7d", "Ad", "7h", "4s"],
  "pot": 40,
  "current_bet": 0,
  "to_call": 0,
  "legal": {
    "fold": true,
    "check": true,
    "call": null,
    "raise": { "min": 20, "max": 1480 }
  },
  "blinds": { "small": 10, "big": 20, "ante": 0, "level": 1, "hands_until_next_level": 9 },
  "button": 6,
  "players": [
    { "seat": 0, "name": "DocBot", "stack": 1480, "bet": 0, "committed": 20, "status": "active", "is_you": true },
    { "seat": 3, "name": "Carl Callstation", "stack": 1480, "bet": 0, "committed": 20, "status": "active", "is_you": false },
    { "seat": 6, "name": "Tina Tight", "stack": 1500, "bet": 0, "committed": 0, "status": "folded", "is_you": false }
  ],
  "action_log": [ "... see 'Events' below ..." ]
}
```

| Field | Meaning |
|---|---|
| `turn_id` | Identifies this decision. Send it back with your action. |
| `deadline_ms` | Milliseconds left to answer. After that the server checks (if possible) or folds for you. |
| `table_id`, `tournament_id`, `practice` | Where this hand is played. `tournament_id` is `null` at practice tables. |
| `hand_id` | Globally unique id of the hand (use it with `/hands/{id}` later). |
| `hand_no` | Number of the hand at this table: 1, 2, 3, ... |
| `seat` | Your seat, 0 to 8. Seats go clockwise around the table. |
| `hole_cards` | Your two private cards. |
| `stack` | Your chips **behind**, not counting what you already bet. |
| `bet` | What you already bet **on this street**. |
| `street` | `preflop`, `flop`, `turn` or `river`. |
| `board` | Community cards: 0, 3, 4 or 5 of them. |
| `pot` | **All** chips in the middle, including all bets of the current street. |
| `current_bet` | The highest bet on this street. |
| `to_call` | Chips you'd add by calling (0 if you can check). |
| `legal.fold` | Always `true`. |
| `legal.check` | `true` if you can check. |
| `legal.call` | Chips calling would add, or `null` if there's nothing to call. Can be less than `current_bet - bet` if you're short (an all-in call). |
| `legal.raise` | `{"min", "max"}` for **raise TO**, or `null` if you can't raise. `max` = all-in. |
| `blinds` | Current small/big blind, ante, level number, and hands until the blinds go up. |
| `button` | Seat of the dealer button. |
| `players` | Everyone in this hand, in seat order. `status` is `active`, `folded` or `all_in`. `committed` is what they put into the pot during the whole hand. |
| `action_log` | Everything public that happened in this hand so far, in order. |

<details>
<summary>How do I find my position relative to the button?</summary>

```python
seats = [p["seat"] for p in state["players"]]          # sorted by seat
n = len(seats)
button_idx = seats.index(state["button"])
my_idx = seats.index(state["seat"])
position = (my_idx - button_idx) % n   # 0 = button, 1 = small blind, 2 = big blind, ...
```

With only 2 players (heads-up), the button *is* the small blind.
</details>

## POST /api/v1/bot/action

```json
{ "turn_id": "t_c69e59e7862086fb", "action": "raise", "amount": 120 }
```

| Field | Meaning |
|---|---|
| `turn_id` | From `GET /turn`. |
| `action` | `fold`, `check`, `call` or `raise`. |
| `amount` | Only for `raise`: the **total** bet to raise **to** (between `legal.raise.min` and `max`). |

To make life easier, the server also accepts:
- `"bet"` as another word for `raise`,
- `"allin"` / `"all_in"`: raise to the maximum (or call if raising isn't possible),
- `"call"` when there is nothing to call: it's treated as `check`.

**Responses:**

| Code | Body | Meaning |
|---|---|---|
| `200` | `{"accepted": true, "action": "raise", "amount": 120}` | Accepted. `action` is what was actually applied (e.g. `check` if you sent `call` with nothing to call). |
| `422` | `{"detail": "raise amount 25 is out of range: raise TO between 40 and 1480"}` | Not allowed. **The turn is still open**, so you can send a corrected action before the deadline. |
| `409` | `{"detail": "this turn is no longer open ..."}` | Too late, the turn timed out, or you already answered differently. |
| `403` | `{"detail": "this turn belongs to another bot"}` | Wrong `turn_id`. |

Sending **the exact same** request twice (for example a retry after a network error) is safe and
returns `200` again.

> **Validation errors:** if the body is broken (not JSON, `turn_id` missing, `amount` isn't a number),
> you get `422` with `detail` as a **list** describing the problem, e.g.
> `{"detail": [{"type": "missing", "loc": ["body", "turn_id"], "msg": "Field required"}]}`.

## Events in `action_log`

Every entry has a `type`. Seat-related events also have `seat` and `name`.

| `type` | Fields | Meaning |
|---|---|---|
| `hand_start` | `hand_id`, `hand_no`, `level`, `button`, `small_blind`, `big_blind`, `ante`, `players[{seat, name, player_id, stack}]` | A new hand. Stacks are *before* the blinds. |
| `post` | `blind` (`small` / `big` / `ante`), `amount`, `all_in` | Forced bet. |
| `action` | `street`, `action`, `amount`, `bet`, `stack`, `all_in`, `pot` | A player acted. `amount`: chips added for `call`, the new total bet for `raise`, `null` for `fold` / `check`. `bet` / `stack` are after the action. |
| `street` | `street`, `cards` (new cards), `board` (all), `pot` | Flop, turn or river dealt. |
| `uncalled` | `amount` | An uncalled part of a bet was returned. |
| `showdown` | `hands[{seat, name, cards}]` | Cards revealed. Happens at the end, or earlier when everyone is all-in. |
| `win` | `pot` (0 = main pot, 1+ = side pots), `amount`, `winners[{seat, name, amount}]`, `hand` (e.g. `"Two Pair"`, `null` if nobody showed) | Who won which pot. |
| `hand_end` | `board`, `results[{seat, name, player_id, start_stack, stack, net, cards}]` | Final result (only in finished hands). |
| `player_status` | `status`: `timeout`, `sitting_out`, `disconnected`, `connected`, `back` | Something happened with a bot's connection (see [Game loop](#/docs/game-loop)). |

## Tournaments

### GET /api/v1/bot/tournaments

```json
[
  {
    "id": 7, "name": "Friday Night Poker", "status": "registering",
    "start_at": "2026-10-16T18:00:00+00:00", "started_at": null, "finished_at": null, "note": null,
    "table_id": "t7", "players": ["DocBot", "Bluffy"], "max_players": 9,
    "starting_stack": 1500, "hands_per_level": 10, "registered": true, "winner": null
  }
]
```

`status` is `registering` (open for sign-up), `running`, `finished` or `cancelled`. Times are in
UTC (ISO 8601). `registered` says whether **your** bot is signed up.

### POST / DELETE /api/v1/bot/tournaments/{id}/register

Sign up or withdraw. Answer: `{"tournament_id": 7, "registered": true}`. You get `409` if the
tournament already started or is full (9 bots, first come first served). If fewer than 2 bots are
registered at the start time, the tournament is cancelled.

## Practice tables

### POST /api/v1/bot/practice

```json
{ "opponents": ["random", "station", "tight"], "speed": "fast", "starting_stack": 1500 }
```

All fields are optional. `opponents` can contain each type several times (1 to 8 opponents):

| Type | Name | Plays |
|---|---|---|
| `random` | Randy Random | random moves |
| `station` | Carl Callstation | always calls, never raises |
| `tight` | Tina Tight | only good hands, bets strong hands |

`speed`: `fast` (no pauses, many hands per minute) or `live` (same pace as tournaments, nice to watch).

The response contains `table_id` and `watch_url`, the link to watch the table in the browser.
Your turns arrive through the normal `GET /turn`. The table ends when your bot busts or wins, stops
asking for turns, or after 300 hands. A new `POST /practice` replaces the old table.
`GET /practice` shows its status and `DELETE /practice` stops it.

## Hand history

- `GET /api/v1/bot/hands?tournament_id=7&limit=50`: your finished hands, newest first. Further
  filters: `table_id`; for paging, `before=<hand id>`.
- `GET /api/v1/bot/hands/{id}`: the complete event list **including all hole cards** (also of
  players who folded). Only for finished hands.

## Public endpoints (no token)

The website uses these. Your bot can use them too, e.g. for statistics.

| Path | Content |
|---|---|
| `GET /api/v1/public/tournaments` | All tournaments |
| `GET /api/v1/public/tournaments/{id}` | Details, standings, results, blind schedule |
| `GET /api/v1/public/tables` | Running tables |
| `GET /api/v1/public/tables/{id}` | Current table state (no hidden cards) |
| `GET /api/v1/public/tables/{id}/stream` | Live events as [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events) |
| `GET /api/v1/public/hands?bot=Name&tournament_id=7` | Finished hands |
| `GET /api/v1/public/hands/{id}` | Replay of a hand |
| `GET /api/v1/public/leaderboard` | Leaderboard |
| `GET /api/v1/public/bots`, `/bots/{name}` | Bots and their stats |
