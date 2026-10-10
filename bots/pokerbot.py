"""Minimal poker-pi client used by the test bots in this folder (Python 3.8+, standard library only).

    POKER_TOKEN=pk_... POKER_URL=http://localhost:8000 python3 caller.py [practice]

A bot module only defines decide(state) -> {"action": ..., "amount": ...} and calls run(decide).
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE_URL = os.environ.get("POKER_URL", "http://localhost:8000").rstrip("/")
TOKEN = os.environ.get("POKER_TOKEN", "")


def api(method, path, body=None, timeout=40):
    """Send a request; return (status_code, parsed JSON or None)."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE_URL + path, data=data, method=method)
    req.add_header("Authorization", "Bearer " + TOKEN)
    req.add_header("User-Agent", "poker-pi-testbot/1.0")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw) if raw else None
        except ValueError:
            return e.code, {"detail": raw.decode(errors="replace")}


def register_for_open_tournaments():
    status, tournaments = api("GET", "/api/v1/bot/tournaments")
    if status != 200:
        return
    for t in tournaments:
        if t["status"] == "registering" and not t["registered"]:
            api("POST", f"/api/v1/bot/tournaments/{t['id']}/register")
            print(f"registered for {t['name']!r}")


def run(decide):
    sys.stdout.reconfigure(line_buffering=True)
    if not TOKEN:
        sys.exit("POKER_TOKEN is not set.")
    status, me = api("GET", "/api/v1/bot/me")
    if status != 200:
        sys.exit(f"token check failed ({status}): {me}")
    print(f"{me['name']} connected to {BASE_URL}")

    if "practice" in sys.argv[1:]:
        status, table = api("POST", "/api/v1/bot/practice", {})
        print("practice table:", table.get("watch_url") if table else status)

    register_for_open_tournaments()
    last_check = time.time()
    while True:
        if time.time() - last_check > 300:
            register_for_open_tournaments()
            last_check = time.time()
        try:
            status, state = api("GET", "/api/v1/bot/turn?wait=25")
        except OSError as e:
            print("network error:", e)
            time.sleep(2)
            continue
        if status == 204:
            continue
        if status != 200:
            print("unexpected answer:", status, state)
            time.sleep(2)
            continue

        action = decide(state)
        status, result = api("POST", "/api/v1/bot/action", {"turn_id": state["turn_id"], **action})
        print(f"hand {state['hand_id']} {state['street']:<7} {' '.join(state['hole_cards'])} -> {action} [{status}]")
        if status == 422:  # not legal: fall back to the safe move so the turn does not time out
            safe = "check" if state["legal"]["check"] else "fold"
            api("POST", "/api/v1/bot/action", {"turn_id": state["turn_id"], "action": safe})
