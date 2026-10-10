# Test bots

Very simple bots, used to try out the server (and by `scripts/demo.sh`). They are not meant as
templates. A bot can be written in any language; the protocol is described in the docs.

| File | Behaviour |
|---|---|
| `caller.py` | checks or calls everything |
| `random_bot.py` | random legal action, small raises |
| `tight.py` | plays only pairs and two high cards |
| `aggressive.py` | raises the pot when unraised, all-in when short |

`pokerbot.py` holds the shared HTTP loop (standard library only, Python 3.8+).

```bash
POKER_TOKEN=pk_... POKER_URL=http://localhost:8000 python3 bots/tight.py
POKER_TOKEN=pk_... python3 bots/caller.py practice     # start a practice table first
```
