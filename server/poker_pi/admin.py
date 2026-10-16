"""Admin command line. Works directly on the database; the running server picks changes up.

    python -m poker_pi.admin create-bot "Bluff Master" --owner Alice
    python -m poker_pi.admin create-tournament --name "Friday Night" --start "2026-10-16 20:00"
    python -m poker_pi.admin register 1 "Bluff Master" "Other Bot"
    python -m poker_pi.admin start 1
    python -m poker_pi.admin discord-test
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timedelta, timezone

from .config import Settings
from .discord_commentator import post_webhook
from .store.db import Store, now_iso
from .tournament.blinds import full_config


def parse_start(value: str) -> str:
    value = value.strip().lower()
    now = datetime.now(timezone.utc)
    if value == "now":
        when = now
    elif m := re.fullmatch(r"\+(\d+)([smhd])", value):
        unit = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}[m.group(2)]
        when = now + timedelta(**{unit: int(m.group(1))})
    else:
        when = datetime.fromisoformat(value)
        if when.tzinfo is None:
            when = when.astimezone()  # interpret as local time
    return when.astimezone(timezone.utc).isoformat(timespec="seconds")


def _bot(store: Store, name: str) -> dict:
    bot = store.get_bot_by_name(name)
    if bot is None:
        sys.exit(f"no bot named {name!r}")
    return bot


def _tournament(store: Store, tid: int) -> dict:
    t = store.get_tournament(tid)
    if t is None:
        sys.exit(f"no tournament {tid}")
    return t


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="poker_pi.admin", description="poker-pi administration")
    ap.add_argument("--db", help="database path (default: $POKER_DB or ./data/poker.db)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("create-bot", help="create a bot and print its token (shown only once)")
    p.add_argument("name")
    p.add_argument("--owner", required=True, help="who owns the bot (your friend's name)")
    sub.add_parser("list-bots", help="list bots")
    p = sub.add_parser("rotate-token", help="issue a new token for a bot (old one stops working)")
    p.add_argument("name")
    p = sub.add_parser("revoke-bot", help="disable a bot")
    p.add_argument("name")
    p = sub.add_parser("restore-bot", help="re-enable a revoked bot")
    p.add_argument("name")

    p = sub.add_parser("create-tournament", help="schedule a tournament")
    p.add_argument("--name", required=True)
    p.add_argument("--start", required=True,
                   help='start time: "2026-10-16 20:00" (local time), "+15m", "+2h" or "now"')
    p.add_argument("--stack", type=int, default=1500, help="starting stack (default 1500)")
    p.add_argument("--hands-per-level", type=int, default=10, help="hands per blind level (default 10)")
    p.add_argument("--pace", type=float, default=2.0, help="min seconds between actions (default 2)")
    p.add_argument("--street-pause", type=float, default=1.5, help="pause before flop/turn/river (default 1.5)")
    p.add_argument("--hand-pause", type=float, default=4.0, help="pause between hands (default 4)")
    p.add_argument("--max-players", type=int, default=9, choices=range(2, 10), metavar="2-9")
    sub.add_parser("list-tournaments", help="list tournaments")
    p = sub.add_parser("show-tournament", help="details of a tournament")
    p.add_argument("id", type=int)
    p = sub.add_parser("register", help="register bots for a tournament")
    p.add_argument("id", type=int)
    p.add_argument("bots", nargs="+", help="bot names")
    p = sub.add_parser("unregister", help="remove bots from a tournament")
    p.add_argument("id", type=int)
    p.add_argument("bots", nargs="+")
    p = sub.add_parser("start", help="start a tournament now (instead of waiting for its start time)")
    p.add_argument("id", type=int)
    p = sub.add_parser("reschedule", help="change the start time")
    p.add_argument("id", type=int)
    p.add_argument("start")
    p = sub.add_parser("cancel", help="cancel a tournament (also stops a running one)")
    p.add_argument("id", type=int)
    p = sub.add_parser("discord-test", help="post a message to the Discord webhook to check the setup")
    p.add_argument("message", nargs="?", default="poker-pi: test message from the admin CLI")

    args = ap.parse_args(argv)
    if args.cmd == "discord-test":
        url = Settings().discord_webhook_url
        if not url.startswith("https://"):
            sys.exit("DISCORD_TOURNAMENT_WEBHOOK_URL is not set (or not an https:// URL)")
        try:
            post_webhook(url, args.message)
        except Exception as e:
            sys.exit(f"sending failed: {e}")
        print("Sent.")
        return
    store = Store(args.db or Settings().db_path)

    if args.cmd == "create-bot":
        if store.get_bot_by_name(args.name):
            sys.exit(f"a bot named {args.name!r} already exists")
        bot, token = store.create_bot(args.name, args.owner)
        print(f"Created bot {bot['name']!r} (owner {bot['owner']}, id {bot['id']})")
        print()
        print(f"  Token: {token}")
        print()
        print("Give this token to the owner. It is shown only once (use rotate-token if it gets lost).")
    elif args.cmd == "list-bots":
        for b in store.list_bots(include_revoked=True):
            flag = "  [revoked]" if b["revoked"] else ""
            print(f"{b['id']}  {b['name']:<24} owner={b['owner']:<16} created={b['created_at']}{flag}")
    elif args.cmd == "rotate-token":
        bot = _bot(store, args.name)
        print(f"New token for {bot['name']!r}: {store.rotate_token(bot['id'])}")
    elif args.cmd in ("revoke-bot", "restore-bot"):
        bot = _bot(store, args.name)
        store.set_revoked(bot["id"], args.cmd == "revoke-bot")
        print(f"{bot['name']!r} {'revoked' if args.cmd == 'revoke-bot' else 'restored'}")
    elif args.cmd == "create-tournament":
        config = full_config({
            "starting_stack": args.stack,
            "hands_per_level": args.hands_per_level,
            "max_players": args.max_players,
            "pacing": {"action": args.pace, "street": args.street_pause, "hand_end": args.hand_pause},
        })
        config["levels"] = [list(level) for level in config["levels"]]
        t = store.create_tournament(args.name, parse_start(args.start), config)
        print(f"Tournament {t['id']} {t['name']!r} starts {t['start_at']} (UTC). Registration is open.")
    elif args.cmd == "list-tournaments":
        for t in store.list_tournaments():
            n = len(store.registrations(t["id"]))
            print(f"{t['id']:>4}  {t['status']:<12} {t['start_at']}  {t['name']}  ({n} players)"
                  + (f"  - {t['note']}" if t["note"] else ""))
    elif args.cmd == "show-tournament":
        t = _tournament(store, args.id)
        print(f"{t['name']} [{t['status']}] start {t['start_at']}")
        print("players:", ", ".join(r["name"] for r in store.registrations(t["id"])) or "-")
        for r in store.results(t["id"]):
            print(f"  {r['place']:>2}. {r['name']} ({r['points']} pts)")
    elif args.cmd in ("register", "unregister"):
        t = _tournament(store, args.id)
        if t["status"] != "registering":
            sys.exit(f"tournament is {t['status']}, registration is closed")
        for name in args.bots:
            bot = _bot(store, name)
            (store.register if args.cmd == "register" else store.unregister)(t["id"], bot["id"])
            print(f"{args.cmd}ed {bot['name']}")
    elif args.cmd == "start":
        t = _tournament(store, args.id)
        if t["status"] != "registering":
            sys.exit(f"tournament is {t['status']}")
        store.update_tournament(t["id"], start_at=now_iso())
        print("Starting within a second or two (if the server is running).")
    elif args.cmd == "reschedule":
        t = _tournament(store, args.id)
        store.update_tournament(t["id"], start_at=parse_start(args.start))
        print("Rescheduled.")
    elif args.cmd == "cancel":
        t = _tournament(store, args.id)
        if t["status"] in ("finished", "cancelled"):
            sys.exit(f"tournament is already {t['status']}")
        store.update_tournament(t["id"], status="cancelled", note="cancelled by the admin", finished_at=now_iso())
        print("Cancelled.")


if __name__ == "__main__":
    main()
