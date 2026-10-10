# FAQ & troubleshooting

## My bot gets `401 Unauthorized`

- Is the header exactly `Authorization: Bearer <token>`? The word `Bearer`, a space, then the token.
- Is the environment variable set **in the same terminal** in which you start the bot? Check with
  `echo $POKER_TOKEN` (PowerShell: `echo $env:POKER_TOKEN`).
- No extra spaces or line breaks when copying?
- Was your token replaced (`rotate-token`)? Then the old one no longer works. Ask the organizer.

## `GET /turn` takes forever and then returns nothing

That's correct! It waits up to 25 seconds for your turn and answers `204` (empty) if nothing happens.
Your bot only gets turns when it sits at a table:
- **Tournament**: only once it has started. Check the lobby. Before that you'll only get `204`s.
- **Practice**: start one with `POST /api/v1/bot/practice` (or `python3 bot.py practice`).

`GET /api/v1/bot/me` shows in `tables` where your bot is currently seated.

## My HTTP library aborts after 10/30 seconds

Its default timeout is shorter than the long-poll. Set it to at least **30, better 40 seconds** for
`GET /turn`, or use a shorter wait like `?wait=10`.

## `422` with "cannot check"

Someone bet, so you have to `call`, `raise` or `fold`. Look at `legal.check`.

## `422` with "raise amount ... is out of range"

Remember, it's **raise TO**: `amount` is your *total* bet on this street. Use a value between
`legal.raise.min` and `legal.raise.max`. When `legal.raise` is `null`, you can't raise at all.

## `422` with `"type": "missing"` or `"json_invalid"`

The body isn't valid JSON or a field is missing. Typical causes:
- forgot `Content-Type: application/json`,
- built JSON by hand with a typo (use your JSON library!),
- sent `amount` as a string with spaces or as a decimal number.

## `409 Conflict`

The turn is over: your bot was too slow (more than 15 s), or it already answered. Simply continue
with the next `GET /turn`. If this happens often, measure how long `decide` takes.

## `429 Too Many Requests`

Your bot sends more than 60 requests per second that achieve nothing (empty polls or errors).
Most likely you're calling `/turn` with `wait=0` in a loop, or you're retrying an error without pausing. Use `wait=25` and `sleep` 1 to 2 s after errors.

## `403` / `1020` / an HTML page instead of JSON

The site sits behind Cloudflare, which sometimes blocks requests that look like attack tools. Set
your own `User-Agent` header (the starter bots do: `poker-pi-starter-bot/1.0`). If it keeps
happening, tell the organizer which language/library you use.

## SSL / certificate errors

- **Python on macOS** (python.org installer): run *"Install Certificates.command"* in
  `/Applications/Python 3.x/`.
- **Java**: update your JDK. Very old ones lack current root certificates.
- **Corporate/university network** with a TLS-intercepting proxy: try another network (e.g. your
  phone's hotspot).
- Never switch off certificate verification "to make it work". Fix the root cause.

## My bot works locally but not against the real server

- Is `POKER_URL` really `https://poker.example.com` (with `https`, without a trailing `/api`)?
- Does `curl https://poker.example.com/api/v1/health` work from that machine?
- Are you behind a proxy? Then set `HTTPS_PROXY` (most libraries honor it).

## I don't see my bot's output

Output to files/pipes is often buffered. Python: `python3 -u bot.py`. C++: `std::cout << std::unitbuf`
or `std::endl`. Java and Node print immediately.

## Why can't I see my opponents' cards?

Poker is a game of hidden information. You see opponent cards in the `showdown` event at the end of
a hand, and in the full hand history afterwards (`GET /api/v1/bot/hands/{id}`). Never during a hand.

## Can my bot use machine learning / an LLM / a huge lookup table?

Yes, as long as it answers within 15 seconds and runs on your own hardware. Training on the public
hand histories is allowed and encouraged.

## Can I run two bots?

You can own several bots (ask for more tokens), but only **one bot per person per tournament**, and
bots must not cooperate.

## My bot crashed in the middle of a tournament!

Restart it quickly. Your chips are still there. While your bot is gone, the server checks or folds for
it and it keeps paying blinds. As soon as it asks for a turn again, it plays normally.

## What happens if the server restarts?

Running tournaments resume automatically from the last completed hand. The hand that was being
played is replayed from scratch with the stacks from before it started. Your bot just keeps polling.

## Where can I see what my bot did?

- On the website: **Bots → your bot**, with all hands and a replay for each one.
- Via API: `GET /api/v1/bot/hands`.
- In your own logs (recommended!).

## I found a bug / have an idea

Tell the organizer, or open an issue or pull request in the repository. Server bugs are not a strategy.
