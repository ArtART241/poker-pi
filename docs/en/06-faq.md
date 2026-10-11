# FAQ

## Requests fail with `401 Unauthorized`

- The header must be exactly `Authorization: Bearer <token>`: the word `Bearer`, one space, the token.
- When the token is read from an environment variable, the variable has to be set in the environment
  the bot is started from.
- Copied tokens sometimes include a trailing space or line break.
- A token that was replaced (`rotate-token`) no longer works; the organizer can provide the new one.

## `GET /turn` takes a long time and returns nothing

This is expected. The request waits up to 25 seconds for a turn and returns `204` (empty) if none
opens. Turns only exist while the bot is seated:
- **Tournament**: only after it has started (see the lobby). Before that, every poll returns `204`.
- **Practice**: after `POST /api/v1/bot/practice`.

`GET /api/v1/bot/me` lists the tables the bot is currently seated at under `tables`.

## The HTTP client aborts after 10 or 30 seconds

The client's default timeout is shorter than the long-poll. It should be set to at least 30
(preferably 40) seconds for `GET /turn`, or a shorter wait such as `?wait=10` can be used.

## `422` with "cannot check"

Another player has bet, so the options are `call`, `raise` or `fold`. `legal.check` shows whether
checking is possible.

## `422` with "raise amount ... is out of range"

`amount` is the **total** bet on the current street (raise *to*), and it has to lie between
`legal.raise.min` and `legal.raise.max`. When `legal.raise` is `null`, raising is not possible.

## `422` with "Invalid request: ..."

The request is malformed; `detail` names the field, e.g. `body.turn_id: Field required`. The body is
not valid JSON, or a field is missing or has the wrong type. Typical causes are a missing
`Content-Type: application/json` header, JSON assembled by hand with a syntax error, or `amount`
sent as a decimal number or as a string with spaces.

## `409 Conflict`

The turn is over: it was answered already, or the 15 seconds passed. The bot can simply continue
with the next `GET /turn`. If this happens often, the duration of `decide` is worth measuring.

## `429 Too Many Requests`

The bot sends more than 60 requests per second that achieve nothing (empty polls or errors), most
likely by calling `/turn` with `wait=0` in a loop or by retrying errors without a pause. Using
`wait=25` and pausing 1 to 2 seconds after errors avoids it.

## `403`, `1020` or an HTML page instead of JSON

The site is served through Cloudflare, which occasionally blocks requests that look like attack
tools. Setting a descriptive `User-Agent` header usually helps. If the problem persists, the
organizer should be told which HTTP library is in use.

## Certificate errors

- Some runtimes ship their own certificate store that can be outdated; updating the runtime or its
  certificate package usually fixes this.
- Networks with TLS-intercepting proxies (some company or university networks) can cause this as
  well; another network helps to confirm it.
- Disabling certificate verification is not a fix.

## The bot works locally but not against the server

- `POKER_URL` (or its equivalent) should be `https://poker.example.com`, with `https` and
  without a trailing `/api`.
- `curl https://poker.example.com/api/v1/health` from the same machine should return
  `{"status":"ok"}`.
- Behind a proxy, most HTTP libraries honour the `HTTPS_PROXY` environment variable.

## Log output appears late or not at all

Many runtimes buffer standard output when it is redirected to a file or pipe. Flushing after each
line, or enabling line buffering, makes the output appear immediately.

## Why are opponents' cards not visible?

Poker is a game of hidden information. Opponent cards appear in the `showdown` event at the end of a
hand and in the full hand history afterwards (`GET /api/v1/bot/hands/{id}`), never during a hand.

## Are machine learning, LLMs or large lookup tables allowed?

Yes, as long as the bot answers within 15 seconds and runs on the participant's own hardware.
Training on the public hand histories is allowed.

## Can one person run several bots?

Several bots per person are possible (each needs its own token), but only **one bot per person
per tournament**, and bots must not cooperate.

## What happens if a bot crashes during a tournament?

Its chips stay at the table. While it is gone, the server checks or folds for it, and it keeps
paying blinds. As soon as it polls again, it plays normally. A quick restart limits the losses.

## What happens if the server restarts?

Running tournaments resume from the last completed hand. The hand that was in progress is replayed
from the stacks it started with. Bots only need to keep polling.

## Where can a bot's past hands be reviewed?

- On the website under **Bots → name**, with a replay for every hand.
- Through the API with `GET /api/v1/bot/hands`.
- In the bot's own logs.

## Reporting bugs and suggestions

Bugs and ideas can be reported to the organizer, or as an issue or pull request in the repository.
