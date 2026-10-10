"""SQLite persistence. Small, synchronous and fast enough for a handful of bots."""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA = """
CREATE TABLE IF NOT EXISTS bots (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE COLLATE NOCASE,
    owner       TEXT NOT NULL,
    token_hash  TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL,
    revoked     INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS tournaments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    status      TEXT NOT NULL,           -- registering | running | finished | cancelled
    start_at    TEXT NOT NULL,           -- ISO 8601, UTC
    config      TEXT NOT NULL,           -- JSON
    state       TEXT,                    -- JSON snapshot after every hand (for resuming)
    note        TEXT,
    created_at  TEXT NOT NULL,
    started_at  TEXT,
    finished_at TEXT
);
CREATE TABLE IF NOT EXISTS registrations (
    tournament_id INTEGER NOT NULL,
    bot_id        TEXT NOT NULL,
    registered_at TEXT NOT NULL,
    PRIMARY KEY (tournament_id, bot_id)
);
CREATE TABLE IF NOT EXISTS hands (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    table_id      TEXT NOT NULL,
    tournament_id INTEGER,
    practice      INTEGER NOT NULL DEFAULT 0,
    hand_no       INTEGER NOT NULL,
    started_at    TEXT NOT NULL,
    ended_at      TEXT,
    events        TEXT
);
CREATE INDEX IF NOT EXISTS hands_by_table ON hands (table_id, id);
CREATE INDEX IF NOT EXISTS hands_by_tournament ON hands (tournament_id, id);
CREATE TABLE IF NOT EXISTS hand_players (
    hand_id  INTEGER NOT NULL,
    bot_id   TEXT NOT NULL,
    seat     INTEGER NOT NULL,
    net      INTEGER NOT NULL,
    practice INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (hand_id, bot_id)
);
CREATE INDEX IF NOT EXISTS hand_players_by_bot ON hand_players (bot_id, hand_id);
CREATE TABLE IF NOT EXISTS results (
    tournament_id INTEGER NOT NULL,
    bot_id        TEXT NOT NULL,
    place         INTEGER NOT NULL,
    points        INTEGER NOT NULL,
    PRIMARY KEY (tournament_id, bot_id)
);
"""

POINTS = {1: 10, 2: 6, 3: 4, 4: 3, 5: 2, 6: 1}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_token() -> str:
    return "pk_" + secrets.token_urlsafe(32)


class Store:
    def __init__(self, path: str) -> None:
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=5000")
        self.db.executescript(SCHEMA)

    def close(self) -> None:
        self.db.close()

    def _all(self, sql: str, args: Iterable[Any] = ()) -> list[dict[str, Any]]:
        return [dict(r) for r in self.db.execute(sql, tuple(args)).fetchall()]

    def _one(self, sql: str, args: Iterable[Any] = ()) -> dict[str, Any] | None:
        row = self.db.execute(sql, tuple(args)).fetchone()
        return dict(row) if row else None

    # ------------------------------------------------------------------ bots

    def create_bot(self, name: str, owner: str) -> tuple[dict[str, Any], str]:
        token = new_token()
        bot_id = "b_" + secrets.token_hex(5)
        self.db.execute(
            "INSERT INTO bots (id, name, owner, token_hash, created_at) VALUES (?, ?, ?, ?, ?)",
            (bot_id, name, owner, hash_token(token), now_iso()),
        )
        return self.get_bot(bot_id), token  # type: ignore[return-value]

    def rotate_token(self, bot_id: str) -> str:
        token = new_token()
        self.db.execute("UPDATE bots SET token_hash = ? WHERE id = ?", (hash_token(token), bot_id))
        return token

    def get_bot(self, bot_id: str) -> dict[str, Any] | None:
        return self._one("SELECT id, name, owner, created_at, revoked FROM bots WHERE id = ?", (bot_id,))

    def get_bot_by_name(self, name: str) -> dict[str, Any] | None:
        return self._one("SELECT id, name, owner, created_at, revoked FROM bots WHERE name = ?", (name,))

    def bot_for_token(self, token: str) -> dict[str, Any] | None:
        return self._one(
            "SELECT id, name, owner, created_at, revoked FROM bots WHERE token_hash = ? AND revoked = 0",
            (hash_token(token),),
        )

    def list_bots(self, include_revoked: bool = False) -> list[dict[str, Any]]:
        sql = "SELECT id, name, owner, created_at, revoked FROM bots"
        if not include_revoked:
            sql += " WHERE revoked = 0"
        return self._all(sql + " ORDER BY name")

    def set_revoked(self, bot_id: str, revoked: bool) -> None:
        self.db.execute("UPDATE bots SET revoked = ? WHERE id = ?", (int(revoked), bot_id))

    # ------------------------------------------------------------------ tournaments

    def create_tournament(self, name: str, start_at: str, config: dict[str, Any]) -> dict[str, Any]:
        cur = self.db.execute(
            "INSERT INTO tournaments (name, status, start_at, config, created_at) VALUES (?, 'registering', ?, ?, ?)",
            (name, start_at, json.dumps(config), now_iso()),
        )
        return self.get_tournament(cur.lastrowid)  # type: ignore[arg-type,return-value]

    def _decode_tournament(self, row: dict[str, Any] | None) -> dict[str, Any] | None:
        if row is None:
            return None
        row["config"] = json.loads(row["config"])
        row["state"] = json.loads(row["state"]) if row["state"] else None
        return row

    def get_tournament(self, tid: int) -> dict[str, Any] | None:
        return self._decode_tournament(self._one("SELECT * FROM tournaments WHERE id = ?", (tid,)))

    def list_tournaments(self, statuses: Iterable[str] | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if statuses:
            statuses = list(statuses)
            marks = ",".join("?" * len(statuses))
            rows = self._all(
                f"SELECT * FROM tournaments WHERE status IN ({marks}) ORDER BY start_at DESC LIMIT ?",
                [*statuses, limit],
            )
        else:
            rows = self._all("SELECT * FROM tournaments ORDER BY start_at DESC LIMIT ?", (limit,))
        return [self._decode_tournament(r) for r in rows]  # type: ignore[misc]

    def update_tournament(self, tid: int, **fields: Any) -> None:
        if "state" in fields and fields["state"] is not None:
            fields["state"] = json.dumps(fields["state"])
        if "config" in fields:
            fields["config"] = json.dumps(fields["config"])
        cols = ", ".join(f"{k} = ?" for k in fields)
        self.db.execute(f"UPDATE tournaments SET {cols} WHERE id = ?", (*fields.values(), tid))

    def register(self, tid: int, bot_id: str) -> None:
        self.db.execute(
            "INSERT OR IGNORE INTO registrations (tournament_id, bot_id, registered_at) VALUES (?, ?, ?)",
            (tid, bot_id, now_iso()),
        )

    def unregister(self, tid: int, bot_id: str) -> None:
        self.db.execute("DELETE FROM registrations WHERE tournament_id = ? AND bot_id = ?", (tid, bot_id))

    def registrations(self, tid: int) -> list[dict[str, Any]]:
        return self._all(
            """SELECT b.id, b.name, b.owner, r.registered_at FROM registrations r
               JOIN bots b ON b.id = r.bot_id WHERE r.tournament_id = ? AND b.revoked = 0
               ORDER BY r.registered_at""",
            (tid,),
        )

    def registered_tournaments(self, bot_id: str) -> list[int]:
        rows = self._all(
            """SELECT t.id FROM registrations r JOIN tournaments t ON t.id = r.tournament_id
               WHERE r.bot_id = ? AND t.status IN ('registering', 'running')""",
            (bot_id,),
        )
        return [r["id"] for r in rows]

    def save_results(self, tid: int, places: dict[str, int]) -> None:
        for bot_id, place in places.items():
            self.db.execute(
                "INSERT OR REPLACE INTO results (tournament_id, bot_id, place, points) VALUES (?, ?, ?, ?)",
                (tid, bot_id, place, POINTS.get(place, 0)),
            )

    def results(self, tid: int) -> list[dict[str, Any]]:
        return self._all(
            """SELECT r.place, r.points, b.name, b.owner, b.id AS bot_id FROM results r
               JOIN bots b ON b.id = r.bot_id WHERE r.tournament_id = ? ORDER BY r.place""",
            (tid,),
        )

    # ------------------------------------------------------------------ hands

    def begin_hand(self, table_id: str, tournament_id: int | None, practice: bool, hand_no: int) -> int:
        cur = self.db.execute(
            "INSERT INTO hands (table_id, tournament_id, practice, hand_no, started_at) VALUES (?, ?, ?, ?, ?)",
            (table_id, tournament_id, int(practice), hand_no, now_iso()),
        )
        return int(cur.lastrowid)  # type: ignore[arg-type]

    def finish_hand(self, hand_id: int, events: list[dict[str, Any]], practice: bool,
                    bot_results: list[tuple[str, int, int]]) -> None:
        """bot_results: (bot_id, seat, net) for real bots only."""
        self.db.execute("BEGIN")
        try:
            self.db.execute(
                "UPDATE hands SET ended_at = ?, events = ? WHERE id = ?",
                (now_iso(), json.dumps(events, separators=(",", ":")), hand_id),
            )
            self.db.executemany(
                "INSERT OR REPLACE INTO hand_players (hand_id, bot_id, seat, net, practice) VALUES (?, ?, ?, ?, ?)",
                [(hand_id, b, s, n, int(practice)) for b, s, n in bot_results],
            )
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def delete_unfinished_hands(self) -> None:
        self.db.execute("DELETE FROM hands WHERE ended_at IS NULL")

    def get_hand(self, hand_id: int) -> dict[str, Any] | None:
        row = self._one("SELECT * FROM hands WHERE id = ? AND ended_at IS NOT NULL", (hand_id,))
        if row:
            row["events"] = json.loads(row["events"])
            row["practice"] = bool(row["practice"])
        return row

    def list_hands(self, *, table_id: str | None = None, tournament_id: int | None = None,
                   bot_id: str | None = None, before: int | None = None,
                   limit: int = 50) -> list[dict[str, Any]]:
        where = ["h.ended_at IS NOT NULL"]
        args: list[Any] = []
        join = ""
        if table_id is not None:
            where.append("h.table_id = ?")
            args.append(table_id)
        if tournament_id is not None:
            where.append("h.tournament_id = ?")
            args.append(tournament_id)
        if bot_id is not None:
            join = "JOIN hand_players hp ON hp.hand_id = h.id"
            where.append("hp.bot_id = ?")
            args.append(bot_id)
        if before is not None:
            where.append("h.id < ?")
            args.append(before)
        rows = self._all(
            f"""SELECT h.id, h.table_id, h.tournament_id, h.practice, h.hand_no, h.started_at, h.ended_at, h.events
                FROM hands h {join} WHERE {' AND '.join(where)} ORDER BY h.id DESC LIMIT ?""",
            [*args, limit],
        )
        return [_hand_summary(r) for r in rows]

    # ------------------------------------------------------------------ stats

    def leaderboard(self) -> list[dict[str, Any]]:
        return self._all(
            """
            SELECT b.name, b.owner,
                   COALESCE(SUM(r.points), 0)                     AS points,
                   COUNT(r.tournament_id)                         AS tournaments,
                   COALESCE(SUM(CASE WHEN r.place = 1 THEN 1 ELSE 0 END), 0) AS wins,
                   AVG(r.place)                                   AS avg_place,
                   MIN(r.place)                                   AS best_place,
                   (SELECT COUNT(*) FROM hand_players hp WHERE hp.bot_id = b.id AND hp.practice = 0) AS hands
            FROM bots b LEFT JOIN results r ON r.bot_id = b.id
            WHERE b.revoked = 0
            GROUP BY b.id
            ORDER BY points DESC, wins DESC, avg_place ASC, b.name
            """
        )

    def bot_stats(self, bot_id: str) -> dict[str, Any]:
        hands = self._one(
            """SELECT COUNT(*) AS hands, COALESCE(SUM(net), 0) AS net,
                      COALESCE(SUM(CASE WHEN net > 0 THEN 1 ELSE 0 END), 0) AS won
               FROM hand_players WHERE bot_id = ? AND practice = 0""",
            (bot_id,),
        ) or {}
        practice = self._one(
            "SELECT COUNT(*) AS hands FROM hand_players WHERE bot_id = ? AND practice = 1", (bot_id,)
        ) or {}
        results = self._all(
            """SELECT r.tournament_id, t.name AS tournament, t.finished_at, r.place, r.points,
                      (SELECT COUNT(*) FROM results r2 WHERE r2.tournament_id = r.tournament_id) AS players
               FROM results r JOIN tournaments t ON t.id = r.tournament_id
               WHERE r.bot_id = ? ORDER BY t.finished_at DESC""",
            (bot_id,),
        )
        return {
            "hands": hands.get("hands", 0),
            "hands_won": hands.get("won", 0),
            "net_chips": hands.get("net", 0),
            "practice_hands": practice.get("hands", 0),
            "tournaments": results,
            "points": sum(r["points"] for r in results),
            "wins": sum(1 for r in results if r["place"] == 1),
        }


def _hand_summary(row: dict[str, Any]) -> dict[str, Any]:
    events = json.loads(row.pop("events") or "[]")
    start = next((e for e in events if e["type"] == "hand_start"), None)
    end = next((e for e in events if e["type"] == "hand_end"), None)
    wins = [e for e in events if e["type"] == "win"]
    winners = sorted({w["name"] for e in wins for w in e["winners"]})
    row["practice"] = bool(row["practice"])
    row["blinds"] = [start["small_blind"], start["big_blind"]] if start else None
    row["players"] = [p["name"] for p in start["players"]] if start else []
    row["pot"] = sum(e["amount"] for e in wins)
    row["winners"] = winners
    row["winning_hand"] = next((e["hand"] for e in wins if e["hand"]), None)
    row["board"] = end["board"] if end else []
    row["showdown"] = any(e["type"] == "showdown" for e in events)
    return row
