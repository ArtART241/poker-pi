import asyncio
import json
import socket
from typing import Any

import httpx
import pytest
import uvicorn

from poker_pi.config import Settings
from poker_pi.main import create_app
from poker_pi.store.db import now_iso

pytestmark = pytest.mark.anyio

FAST = {"pacing": {"action": 0, "street": 0, "hand_end": 0}}


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def env(tmp_path):
    settings = Settings(db_path=str(tmp_path / "test.db"), static_dir=str(tmp_path / "none"),
                        decision_timeout=0.5, sitout_grace=0.2, max_timeouts=3, disconnect_after=60,
                        rate_limit=1000)
    app = create_app(settings)
    hub = app.state.hub
    await hub.start()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield app, hub, client
    await hub.stop()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def make_bots(hub, *names):
    return {n: hub.store.create_bot(n, "tester")[1] for n in names}


def make_tournament(hub, names, **cfg):
    t = hub.store.create_tournament("Test Cup", "2000-01-01T00:00:00+00:00", {**FAST, **cfg})
    for n in names:
        hub.store.register(t["id"], hub.store.get_bot_by_name(n)["id"])
    return t["id"]


async def play(client, token, strategy, stop: asyncio.Event, log: list | None = None):
    """A tiny bot: long-poll for turns and answer them with strategy(state)."""
    while not stop.is_set():
        r = await client.get("/api/v1/bot/turn", params={"wait": 0.2}, headers=auth(token))
        if r.status_code == 204:
            continue
        assert r.status_code == 200, r.text
        state = r.json()
        body = {"turn_id": state["turn_id"], **strategy(state)}
        r = await client.post("/api/v1/bot/action", json=body, headers=auth(token))
        if log is not None:
            log.append((state, r.status_code, r.json()))
        assert r.status_code in (200, 409), r.text


def shove(state):
    if state["legal"]["raise"]:
        return {"action": "raise", "amount": state["legal"]["raise"]["max"]}
    return {"action": "call"}


def caller(state):
    return {"action": "call"}  # "call" with nothing to call counts as check


async def wait_until(pred, timeout=10.0):
    end = asyncio.get_running_loop().time() + timeout
    while not pred():
        assert asyncio.get_running_loop().time() < end, "timed out"
        await asyncio.sleep(0.02)


async def test_auth_errors(env):
    _, hub, client = env
    r = await client.get("/api/v1/bot/me")
    assert r.status_code == 401 and "Bearer" in r.json()["detail"]
    r = await client.get("/api/v1/bot/me", headers=auth("nope"))
    assert r.status_code == 401
    tokens = make_bots(hub, "alice")
    r = await client.get("/api/v1/bot/me", headers=auth(tokens["alice"]))
    assert r.status_code == 200 and r.json()["name"] == "alice"


async def test_turn_long_poll_returns_204_when_idle(env):
    _, hub, client = env
    tokens = make_bots(hub, "alice")
    r = await client.get("/api/v1/bot/turn", params={"wait": 0.1}, headers=auth(tokens["alice"]))
    assert r.status_code == 204


async def test_full_tournament_over_http(env):
    _, hub, client = env
    tokens = make_bots(hub, "shover", "caller", "folder")
    tid = make_tournament(hub, ["shover", "caller", "folder"], starting_stack=500)
    hub.tournaments.tick()
    table = hub.tables[f"t{tid}"]
    stop = asyncio.Event()
    bots = [
        asyncio.create_task(play(client, tokens["shover"], shove, stop)),
        asyncio.create_task(play(client, tokens["caller"], caller, stop)),
        asyncio.create_task(play(client, tokens["folder"], lambda s: {"action": "fold"}, stop)),
    ]
    await wait_until(lambda: table.status == "finished", timeout=30)
    stop.set()
    await asyncio.gather(*bots)

    t = (await client.get(f"/api/v1/public/tournaments/{tid}")).json()
    assert t["status"] == "finished"
    assert [r["place"] for r in t["results"]] == [1, 2, 3]
    assert t["winner"] == t["results"][0]["name"]
    total = sum(s["stack"] for s in t["standings"])
    assert total == 1500  # all chips end with the winner

    board = (await client.get("/api/v1/public/leaderboard")).json()
    assert board[0]["points"] == 10 and board[0]["wins"] == 1

    hands = (await client.get("/api/v1/public/hands", params={"tournament_id": tid})).json()
    assert hands and hands[0]["tournament_id"] == tid
    detail = (await client.get(f"/api/v1/public/hands/{hands[0]['id']}")).json()
    assert detail["events"][0]["type"] == "hand_start"
    assert detail["events"][-1]["type"] == "hand_end"

    profile = (await client.get(f"/api/v1/public/bots/{t['winner']}")).json()
    assert profile["stats"]["wins"] == 1


async def test_illegal_stale_and_duplicate_actions(env):
    _, hub, client = env
    tokens = make_bots(hub, "a", "b")
    tid = make_tournament(hub, ["a", "b"])
    hub.tournaments.tick()

    # whoever is first to act (heads-up: the button) gets a turn
    states = {}
    for name in ("a", "b"):
        r = await client.get("/api/v1/bot/turn", params={"wait": 0.3}, headers=auth(tokens[name]))
        if r.status_code == 200:
            states[name] = r.json()
    assert len(states) == 1
    name, state = next(iter(states.items()))
    h = auth(tokens[name])
    other = auth(tokens["b" if name == "a" else "a"])

    assert state["legal"]["call"] == 10 and state["legal"]["raise"]["min"] == 40
    assert len(state["hole_cards"]) == 2
    assert not any("cards" in e for e in state["action_log"])

    r = await client.post("/api/v1/bot/action", json={"turn_id": state["turn_id"], "action": "check"}, headers=h)
    assert r.status_code == 422 and "cannot check" in r.json()["detail"]
    r = await client.post("/api/v1/bot/action",
                          json={"turn_id": state["turn_id"], "action": "raise", "amount": 25}, headers=h)
    assert r.status_code == 422 and "between 40" in r.json()["detail"]
    r = await client.post("/api/v1/bot/action",
                          json={"turn_id": state["turn_id"], "action": "raise"}, headers=h)
    assert r.status_code == 422
    r = await client.post("/api/v1/bot/action", json={"turn_id": state["turn_id"], "action": "call"}, headers=other)
    assert r.status_code == 403

    body = {"turn_id": state["turn_id"], "action": "raise", "amount": 60}
    r = await client.post("/api/v1/bot/action", json=body, headers=h)
    assert r.status_code == 200 and r.json() == {"accepted": True, "action": "raise", "amount": 60}
    r = await client.post("/api/v1/bot/action", json=body, headers=h)  # retry is fine
    assert r.status_code == 200
    r = await client.post("/api/v1/bot/action", json={**body, "action": "fold"}, headers=h)
    assert r.status_code == 409
    r = await client.post("/api/v1/bot/action", json={"turn_id": "t_bogus", "action": "fold"}, headers=h)
    assert r.status_code == 409
    hub.tables[f"t{tid}"].stop("test over")


async def test_timeouts_auto_fold_and_sit_out(env):
    _, hub, client = env
    tokens = make_bots(hub, "sleepy", "awake")
    tid = make_tournament(hub, ["sleepy", "awake"])
    # sleepy polls once so it counts as connected, then never answers
    await client.get("/api/v1/bot/turn", params={"wait": 0}, headers=auth(tokens["sleepy"]))
    hub.tournaments.tick()
    table = hub.tables[f"t{tid}"]
    stop = asyncio.Event()
    awake = asyncio.create_task(play(client, tokens["awake"], caller, stop))
    sleepy_seat = next(s for s in table.seats.values() if s.name == "sleepy")
    await wait_until(lambda: sleepy_seat.sitting_out, timeout=15)
    stop.set()
    await awake
    hands = hub.store.list_hands(table_id=table.id, limit=50)
    all_events = [e for h in hands for e in hub.store.get_hand(h["id"])["events"]] + table.hand.events
    statuses = [e["status"] for e in all_events if e["type"] == "player_status"]
    assert statuses.count("timeout") >= 3 and "sitting_out" in statuses
    table.stop("test over")


async def test_live_stream_never_leaks_hole_cards(env):
    _, hub, client = env
    tokens = make_bots(hub, "x", "y", "z")
    tid = make_tournament(hub, ["x", "y", "z"], starting_stack=400)
    hub.tournaments.tick()
    table = hub.tables[f"t{tid}"]
    queue = table.bus.subscribe()
    stop = asyncio.Event()
    bots = [asyncio.create_task(play(client, tokens[n], s, stop))
            for n, s in (("x", shove), ("y", caller), ("z", caller))]
    await wait_until(lambda: table.status == "finished", timeout=30)
    stop.set()
    await asyncio.gather(*bots)

    revealed = False
    seen_types = set()
    while not queue.empty():
        ev = queue.get_nowait()
        seen_types.add(ev["type"])
        if ev["type"] == "hand_start":
            revealed = False
        if ev["type"] == "showdown":
            revealed = True
        if ev["type"] in ("showdown", "hand_end", "street"):
            continue
        text = json.dumps(ev)
        assert '"cards"' not in text and "hole" not in text, ev
        if ev["type"] == "win" and ev["hand"]:
            assert revealed  # a named winning hand only after cards were shown
    assert {"hand_start", "action", "win", "hand_end"} <= seen_types
    assert "deal_hole" not in seen_types


async def test_sse_stream_starts_with_snapshot(env):
    app, hub, _ = env
    make_bots(hub, "p", "q")
    tid = make_tournament(hub, ["p", "q"])
    hub.tournaments.tick()
    # the in-process test transport buffers whole responses, so use a real server here
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, lifespan="off", log_level="warning"))
    serving = asyncio.create_task(server.serve(sockets=[sock]))
    await wait_until(lambda: server.started)
    try:
        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}") as client:
            async with client.stream("GET", f"/api/v1/public/tables/t{tid}/stream") as r:
                assert r.headers["content-type"].startswith("text/event-stream")
                messages = []
                async for line in r.aiter_lines():
                    if line.startswith("data: "):
                        messages.append(json.loads(line[6:]))
                    if len(messages) == 3:
                        break
        assert messages[0]["type"] == "snapshot"
        snap = messages[0]["table"]
        assert snap["id"] == f"t{tid}"
        assert "deal_hole" not in {e["type"] for e in snap["events"]}
    finally:
        server.should_exit = True
        await serving
        hub.tables[f"t{tid}"].stop("test over")


async def test_registration_rules(env):
    _, hub, client = env
    tokens = make_bots(hub, "a")
    t = hub.store.create_tournament("Later", "2999-01-01T00:00:00+00:00", {})
    h = auth(tokens["a"])
    r = await client.post(f"/api/v1/bot/tournaments/{t['id']}/register", headers=h)
    assert r.status_code == 200
    lst = (await client.get("/api/v1/bot/tournaments", headers=h)).json()
    assert lst[0]["registered"] is True
    r = await client.delete(f"/api/v1/bot/tournaments/{t['id']}/register", headers=h)
    assert r.json()["registered"] is False
    r = await client.post("/api/v1/bot/tournaments/999/register", headers=h)
    assert r.status_code == 404
    hub.store.update_tournament(t["id"], status="finished")
    r = await client.post(f"/api/v1/bot/tournaments/{t['id']}/register", headers=h)
    assert r.status_code == 409


async def test_not_enough_players_cancels(env):
    _, hub, client = env
    make_bots(hub, "lonely")
    tid = make_tournament(hub, ["lonely"])
    hub.tournaments.tick()
    t = hub.store.get_tournament(tid)
    assert t["status"] == "cancelled" and "not enough" in t["note"]


async def test_practice_table(env):
    _, hub, client = env
    tokens = make_bots(hub, "learner")
    h = auth(tokens["learner"])
    r = await client.post("/api/v1/bot/practice", json={"opponents": ["random", "station", "tight"]}, headers=h)
    assert r.status_code == 200, r.text
    info = r.json()
    assert len(info["players"]) == 4 and info["watch_url"].endswith(info["table_id"])
    table = hub.tables[info["table_id"]]
    stop = asyncio.Event()
    task = asyncio.create_task(play(client, tokens["learner"], caller, stop))
    await wait_until(lambda: table.hand_no >= 5 or table.status == "finished", timeout=20)
    r = await client.delete("/api/v1/bot/practice", headers=h)
    assert r.status_code == 200
    stop.set()
    await task
    await wait_until(lambda: table.status == "finished")
    hands = (await client.get("/api/v1/bot/hands", headers=h)).json()
    assert hands and all(x["practice"] for x in hands)
    board = (await client.get("/api/v1/public/leaderboard")).json()
    assert board[0]["hands"] == 0  # practice does not count


async def test_resume_after_restart(tmp_path):
    settings = Settings(db_path=str(tmp_path / "r.db"), static_dir=str(tmp_path / "none"),
                        decision_timeout=0.2, rate_limit=1000)
    app = create_app(settings)
    hub = app.state.hub
    await hub.start()
    make_bots(hub, "a", "b")
    tid = make_tournament(hub, ["a", "b"])
    hub.tournaments.tick()
    table = hub.tables[f"t{tid}"]
    await wait_until(lambda: table.hand_no >= 3, timeout=20)  # nobody plays: auto actions
    await hub.stop()

    app2 = create_app(settings)
    hub2 = app2.state.hub
    await hub2.start()
    t = hub2.store.get_tournament(tid)
    assert t["status"] == "running"
    hub2.tournaments.tick()
    table2 = hub2.tables[f"t{tid}"]
    assert table2.hand_no == t["state"]["hand_no"] >= 2
    assert sum(s.stack for s in table2.seats.values()) == 3000
    await hub2.stop()


async def test_openapi_yaml_and_docs(env):
    _, _, client = env
    r = await client.get("/openapi.yaml")
    assert r.status_code == 200 and "/api/v1/bot/turn" in r.text
    r = await client.get("/docs")
    assert r.status_code == 200


async def test_web_config_lists_sounds(tmp_path):
    static = tmp_path / "web"
    (static / "sounds").mkdir(parents=True)
    (static / "index.html").write_text("<html></html>")
    for name in ("raise.mp3", "chips_1.wav", "README.md"):
        (static / "sounds" / name).write_text("x")
    app = create_app(Settings(db_path=str(tmp_path / "c.db"), static_dir=str(static), card_deck="artwork"))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        cfg = (await client.get("/api/v1/public/config")).json()
    assert cfg == {"card_deck": "artwork", "sounds": ["chips_1.wav", "raise.mp3"]}
