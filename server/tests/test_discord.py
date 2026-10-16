import asyncio
import random
import threading
import time
from types import SimpleNamespace

import httpx
import pytest

from poker_pi import discord_commentator as dc
from poker_pi.config import Settings
from poker_pi.discord_commentator import DiscordCommentator, _format_event
from poker_pi.main import create_app

from test_api import auth, caller, make_bots, make_tournament, play, shove, wait_until

pytestmark = pytest.mark.anyio

URL = "https://discord.invalid/api/webhooks/1/x"


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def first_phrasing(monkeypatch):
    """Always pick the first of the alternative phrasings, so tests can match exact texts."""
    monkeypatch.setattr(dc, "random", SimpleNamespace(choice=lambda options: options[0]))


def fmt(event, big_blind=20, title="Friday Cup"):
    return _format_event(event, table_title=title, big_blind=big_blind)


def action(**kw):
    return {"type": "action", "seat": 1, "name": "Ace", "street": "preflop", "action": "call",
            "amount": None, "bet": 0, "stack": 100, "all_in": False, "pot": 0, **kw}


class Recorder:
    """Stands in for post_webhook: records messages, with random delays like a real network."""

    def __init__(self, delay: float = 0.0, fail: set[int] = frozenset()):
        self.messages: list[str] = []
        self.delay = delay
        self.fail = fail
        self.calls = 0
        self.lock = threading.Lock()

    def __call__(self, url: str, message: str) -> None:
        assert url == URL
        with self.lock:
            self.calls += 1
            n = self.calls
        time.sleep(random.uniform(0, self.delay))
        if n in self.fail:
            raise RuntimeError("Discord answered HTTP 500")
        self.messages.append(message)


# ---------------------------------------------------------------------- formatting


def test_all_in_is_announced():
    msg = fmt(action(action="raise", amount=1500, bet=1500, all_in=True, pot=2250))
    assert "**Ace**" in msg and "1.500" in msg and "2.250" in msg


def test_big_raise_threshold():
    assert fmt(action(action="raise", amount=199, bet=199)) is None
    msg = fmt(action(action="raise", amount=750, bet=750))
    assert "750 Chips" in msg and "37,5x" in msg
    assert "10x" in fmt(action(action="raise", amount=200, bet=200))
    assert fmt(action(action="raise", amount=200, bet=200), big_blind=0) is None
    assert fmt(action(action="call", amount=None, bet=400)) is None


def test_eliminations_and_winner():
    assert "Platz 2" in fmt({"type": "eliminated", "seat": 2, "name": "Ace", "place": 2})
    assert "Platz **5**" in fmt({"type": "eliminated", "seat": 2, "name": "Ace", "place": 5})
    assert "**Ace**" in fmt({"type": "eliminated", "seat": 2, "name": "Ace", "place": None})
    assert "Ace" in fmt({"type": "tournament_end", "winner": "Ace", "results": []})
    assert fmt({"type": "tournament_end", "winner": None, "results": []}) is None


def test_other_events_are_quiet():
    for ev in ({"type": "hand_start"}, {"type": "street", "street": "flop"}, {"type": "turn"},
               {"type": "table_status", "status": "running"}, {"type": "win"}):
        assert fmt(ev) is None


def test_names_are_markdown_escaped():
    msg = fmt({"type": "eliminated", "seat": 1, "name": "**big_bot**", "place": 3})
    assert r"\*\*big\_bot\*\*" in msg


# ---------------------------------------------------------------------- delivery


def table(title="Cup", big=20):
    return SimpleNamespace(title=title, blinds=SimpleNamespace(big=big))


def eliminated(place):
    return {"type": "eliminated", "seat": place, "name": f"P{place}", "place": place}


async def test_messages_arrive_in_event_order():
    rec = Recorder(delay=0.02)
    c = DiscordCommentator(URL, post=rec)
    c.start()
    for place in range(9, 1, -1):
        c.on_event(table(), eliminated(place))
    c.on_event(table(), {"type": "tournament_end", "winner": "P1", "results": []})
    await c.stop()
    assert len(rec.messages) == 9
    for place, msg in zip(range(9, 1, -1), rec.messages):
        assert f"P{place}" in msg
    assert "P1" in rec.messages[-1]


async def test_a_failed_send_does_not_stop_the_rest(caplog):
    rec = Recorder(fail={1})
    c = DiscordCommentator(URL, post=rec)
    c.start()
    for place in (4, 3, 2):
        c.on_event(table(), eliminated(place))
    await c.stop()
    assert [m.count("P3") + m.count("P2") for m in rec.messages] == [1, 1]
    assert "HTTP 500" in caplog.text


async def test_disabled_without_valid_url(caplog):
    for url in ("", "  ", "discord.com/api/webhooks/1/x", "http://discord.com/api/webhooks/1/x"):
        rec = Recorder()
        c = DiscordCommentator(url, post=rec)
        c.start()
        c.on_event(table(), eliminated(2))
        await c.stop()
        assert not c.enabled and rec.calls == 0
    assert "not an https:// URL" in caplog.text
    assert "discord.com" not in caplog.text  # the URL is a secret and never logged


async def test_full_queue_drops_instead_of_growing(monkeypatch):
    monkeypatch.setattr(dc, "QUEUE_SIZE", 3)
    gate = threading.Event()
    rec = Recorder()

    def slow(url, message):
        gate.wait(5)
        rec(url, message)

    c = DiscordCommentator(URL, post=slow)
    c.start()
    for place in range(10, 1, -1):
        c.on_event(table(), eliminated(place))
    gate.set()
    await c.stop()
    assert 3 <= len(rec.messages) <= 4  # one in flight + a full queue


async def test_formatting_errors_are_contained():
    rec = Recorder()
    c = DiscordCommentator(URL, post=rec)
    c.start()
    c.on_event(table(), action(action="raise", amount=500, all_in=True, bet=object(), pot=0))
    c.on_event(table(), eliminated(2))
    await c.stop()
    assert len(rec.messages) == 2  # an odd value is printed as is; nothing raises


# ---------------------------------------------------------------------- end to end


async def test_tournament_commentary_end_to_end(tmp_path):
    settings = Settings(db_path=str(tmp_path / "d.db"), static_dir=str(tmp_path / "none"),
                        decision_timeout=0.5, rate_limit=1000)
    app = create_app(settings)
    hub = app.state.hub
    rec = Recorder(delay=0.01)
    hub.commentator = DiscordCommentator(URL, post=rec)
    await hub.start()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            tokens = make_bots(hub, "shover", "caller", "folder")
            tid = make_tournament(hub, ["shover", "caller", "folder"], starting_stack=500)
            hub.tournaments.tick()
            t = hub.tables[f"t{tid}"]
            stop = asyncio.Event()
            bots = [asyncio.create_task(play(client, tokens["shover"], shove, stop)),
                    asyncio.create_task(play(client, tokens["caller"], caller, stop)),
                    asyncio.create_task(play(client, tokens["folder"], lambda s: {"action": "fold"}, stop))]
            await wait_until(lambda: t.status == "finished", timeout=30)
            await asyncio.wait_for(hub.commentator._queue.join(), 5)
            sent = list(rec.messages)

            # practice tables are not commented on
            r = await client.post("/api/v1/bot/practice", json={"opponents": ["random"], "speed": "fast"},
                                  headers=auth(tokens["shover"]))
            assert r.status_code == 200, r.text
            practice = hub.practice.for_bot(hub.store.get_bot_by_name("shover")["id"])
            await wait_until(lambda: practice.status == "finished", timeout=30)
            stop.set()
            await asyncio.gather(*bots)
            places = {r["place"]: r["name"] for r in hub.store.results(tid)}
    finally:
        await hub.stop()

    assert any(m.startswith("🔥 **ALL-IN!**") and "**shover**" in m for m in sent)
    assert sent[-1].startswith("🏆 **TURNIERSIEG!**") and f"**{places[1]}**" in sent[-1]
    out = [m for m in sent if m.startswith(("💥 **TURNIER AUS!**", "💥 **PLAYER OUT!**"))]
    assert sorted(out) == sorted([
        f"💥 **TURNIER AUS!**\n**{places[2]}** scheidet auf Platz 2 aus. Knapp am ganz großen Triumph vorbei! 🥈",
        f"💥 **PLAYER OUT!**\nFür **{places[3]}** ist Schluss — Platz **3**. Der Traum vom Titel ist geplatzt! 🃏",
    ])
    assert sent.index(out[-1]) < len(sent) - 1  # eliminations before the winner
    assert rec.messages == sent  # nothing from the practice table
