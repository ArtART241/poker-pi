#!/usr/bin/env python3
"""poker-pi starter bot (Python 3.8+, standard library only).

Run:
    export POKER_TOKEN="pk_..."                         # your bot token
    export POKER_URL="https://poker.example.com"    # optional, default http://localhost:8000
    python3 bot.py              # play tournaments you are registered for
    python3 bot.py practice     # start a practice table against house bots first

Only `decide()` needs to change to make the bot smarter. Everything else is plumbing.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE_URL = os.environ.get("POKER_URL", "http://localhost:8000").rstrip("/")
TOKEN = os.environ.get("POKER_TOKEN", "")

RANKS = "23456789TJQKA"


# --------------------------------------------------------------------------- your strategy

def decide(state):
    """Return the action for this turn as a dict, e.g. {"action": "call"}.

    state["hole_cards"]  your two cards, e.g. ["Ah", "Td"]
    state["board"]       community cards (0, 3, 4 or 5)
    state["legal"]       what you may do: {"fold": True, "check": bool,
                         "call": chips-to-add or None, "raise": {"min": x, "max": y} or None}
    state["to_call"], state["pot"], state["stack"], state["players"], ... see the docs.
    """
    legal = state["legal"]
    card1, card2 = state["hole_cards"]
    r1, r2 = RANKS.index(card1[0]), RANKS.index(card2[0])

    pair = r1 == r2
    high = max(r1, r2) >= RANKS.index("T") and min(r1, r2) >= RANKS.index("9")
    strong = pair or high or max(r1, r2) == RANKS.index("A")

    big_blind = state["blinds"]["big"]
    nobody_raised = state["current_bet"] <= big_blind
    if strong and legal["raise"] and nobody_raised:
        # raise TO 3 big blinds (amount = your total bet on this street), within the legal range
        amount = max(legal["raise"]["min"], 3 * big_blind)
        return {"action": "raise", "amount": min(amount, legal["raise"]["max"])}
    if legal["check"]:
        return {"action": "check"}
    if strong or state["to_call"] <= state["stack"] // 20:
        return {"action": "call"}
    return {"action": "fold"}


# --------------------------------------------------------------------------- HTTP plumbing

def api(method, path, body=None, timeout=40):
    """Send a request, return (status_code, parsed_json_or_None)."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(BASE_URL + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + TOKEN)
    req.add_header("User-Agent", "poker-pi-starter-bot/1.0 (python)")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:  # 4xx / 5xx still carry a JSON body with "detail"
        raw = e.read()
        try:
            return e.code, json.loads(raw) if raw else None
        except ValueError:
            return e.code, {"detail": raw.decode("utf-8", "replace")}


def register_for_open_tournaments():
    status, tournaments = api("GET", "/api/v1/bot/tournaments")
    if status != 200:
        print("could not list tournaments:", status, tournaments)
        return
    for t in tournaments:
        if t["status"] == "registering" and not t["registered"]:
            status, body = api("POST", f"/api/v1/bot/tournaments/{t['id']}/register")
            print(f"register for '{t['name']}' (starts {t['start_at']}):", status, body)


def main():
    sys.stdout.reconfigure(line_buffering=True)  # show output immediately, even when redirected
    if not TOKEN:
        sys.exit("Set the POKER_TOKEN environment variable to your bot token.")

    status, me = api("GET", "/api/v1/bot/me")
    if status != 200:
        sys.exit(f"Token check failed ({status}): {me}")
    print(f"Hello {me['name']}! Talking to {BASE_URL}")

    if len(sys.argv) > 1 and sys.argv[1] == "practice":
        status, table = api("POST", "/api/v1/bot/practice", {"opponents": ["random", "station", "tight"]})
        print("practice table:", status, table.get("watch_url") if table else table)

    register_for_open_tournaments()
    last_check = time.time()

    while True:
        if time.time() - last_check > 300:  # look for new tournaments every 5 minutes
            register_for_open_tournaments()
            last_check = time.time()
        try:
            status, state = api("GET", "/api/v1/bot/turn?wait=25")
        except OSError as e:  # network problem: wait a bit and try again
            print("network error:", e)
            time.sleep(2)
            continue

        if status == 204:  # not our turn yet, just ask again
            continue
        if status != 200:
            print("unexpected answer:", status, state)
            time.sleep(2)
            continue

        action = decide(state)
        status, result = api("POST", "/api/v1/bot/action", {"turn_id": state["turn_id"], **action})
        print(f"hand {state['hand_id']} {state['street']:<7} {' '.join(state['hole_cards'])} | "
              f"board {' '.join(state['board']) or '-':<14} -> {action} [{status}]")
        if status == 422:
            # our action was not legal: say why, then play it safe so we do not time out
            print("  rejected:", result["detail"])
            safe = "check" if state["legal"]["check"] else "fold"
            api("POST", "/api/v1/bot/action", {"turn_id": state["turn_id"], "action": safe})
        elif status != 200:
            print("  server said:", result)


if __name__ == "__main__":
    main()
