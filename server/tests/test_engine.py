import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from poker_pi.engine.cards import FULL_DECK
from poker_pi.engine.hand import Action, Hand, IllegalAction, SeatSpec

FOLD, CHECK, CALL = Action("fold"), Action("check"), Action("call")


def raise_to(x: int) -> Action:
    return Action("raise", x)


def make_hand(stacks, button=0, sb=10, bb=20, ante=0, holes=None, board=None):
    """stacks: list indexed by seat. holes: {seat: ["Ah", "Kd"]}, board: 5 cards."""
    seats = [s for s, stack in enumerate(stacks) if stack]
    deck = None
    if holes is not None:
        n = len(seats)
        b = seats.index(button)
        order = [seats[(b + 1 + k) % n] for k in range(n)]
        deck = [holes[s][0] for s in order] + [holes[s][1] for s in order] + list(board)
        deck += [c for c in FULL_DECK if c not in deck]
    specs = [SeatSpec(s, f"p{s}", f"bot{s}", stacks[s]) for s in seats]
    return Hand(1, specs, button, sb, bb, ante, deck=deck)


def stacks_of(h):
    return {p.seat: p.stack for p in h.players}


def test_three_handed_blinds_and_order():
    h = make_hand([1000, 1000, 1000], button=0)
    assert h.player_by_seat(1).bet == 10
    assert h.player_by_seat(2).bet == 20
    assert h.to_act.seat == 0
    legal = h.legal_actions()
    assert legal == {"fold": True, "check": False, "call": 20, "raise": {"min": 40, "max": 1000}}


def test_heads_up_button_is_small_blind_and_acts_first_preflop_only():
    h = make_hand([1000, 1000], button=0)
    assert h.player_by_seat(0).bet == 10  # button posts small blind
    assert h.to_act.seat == 0
    h.apply(CALL)
    assert h.to_act.seat == 1  # big blind option
    h.apply(CHECK)
    assert h.street == "flop"
    assert h.to_act.seat == 1  # big blind acts first after the flop


def test_fold_to_big_blind_returns_uncalled_and_awards_blinds():
    h = make_hand([1000, 1000, 1000], button=0)
    h.apply(FOLD)
    h.apply(FOLD)
    assert h.done
    assert stacks_of(h) == {0: 1000, 1: 990, 2: 1010}
    assert not any(e["type"] == "showdown" for e in h.events)


def test_big_blind_has_option_after_limps():
    h = make_hand([1000, 1000, 1000], button=0)
    h.apply(CALL)
    h.apply(CALL)
    assert h.to_act.seat == 2
    legal = h.legal_actions()
    assert legal["check"] and legal["raise"] == {"min": 40, "max": 1000}
    h.apply(raise_to(60))
    assert h.to_act.seat == 0


def test_min_raise_tracks_last_full_raise():
    h = make_hand([1000, 1000, 1000], button=0)
    h.apply(raise_to(60))  # raise of 40
    assert h.legal_actions()["raise"]["min"] == 100
    h.apply(raise_to(200))  # raise of 140
    assert h.legal_actions()["raise"]["min"] == 340


def test_short_all_in_does_not_reopen_betting():
    # seat 3 is short. 0 raises, 1 calls, 2 folds, 3 shoves for less than a full raise.
    h = make_hand([1000, 1000, 1000, 130], button=3)
    # button 3 -> sb 0, bb 1, first to act 2
    assert h.to_act.seat == 2
    h.apply(raise_to(100))  # seat 2: raise of 80
    h.apply(raise_to(130))  # seat 3: all-in, +30 is not a full raise
    assert h.player_by_seat(3).all_in
    h.apply(FOLD)  # seat 0
    h.apply(CALL)  # seat 1 calls 130 (has not acted yet, could also raise)
    assert h.to_act.seat == 2
    legal = h.legal_actions()
    assert legal["call"] == 30
    assert legal["raise"] is None  # betting not reopened for seat 2


def test_cumulative_short_all_ins_reopen():
    # sb 10 / bb 20. Seats: 0 btn A(1000), 1 sb B(1000), 2 bb C(1000), 3 D(150), 4 E(190)
    h = make_hand([1000, 1000, 1000, 150, 180], button=0)
    assert h.to_act.seat == 3
    h.apply(raise_to(100))  # D raises to 100 (+80, full) -> min raise 80
    h.apply(CALL)  # E calls 100
    h.apply(CALL)  # A calls 100
    h.apply(CALL)  # B calls 100
    h.apply(CALL)  # C calls 100 -> preflop over
    assert h.street == "flop"
    # flop: first to act is B (seat 1)
    h.apply(raise_to(40))  # B bets 40 -> min raise 40
    h.apply(CALL)  # C calls 40
    h.apply(raise_to(50))  # D all-in 50 (+10, short)
    h.apply(raise_to(80))  # E all-in 80 (+30, short)
    h.apply(CALL)  # A calls 80
    assert h.to_act.seat == 1
    # B faced 40, now 80: two short raises add up to +40 = a full raise -> reopened
    assert h.legal_actions()["raise"] == {"min": 120, "max": 900}


def test_side_pots_three_way_all_in():
    # seat 0 shortest with the best hand, seat 1 middle with second best, seat 2 biggest
    holes = {0: ["Ah", "As"], 1: ["Kh", "Ks"], 2: ["Qh", "Qs"]}
    board = ["2c", "7d", "9c", "3s", "4h"]
    h = make_hand([100, 300, 500], button=0, holes=holes, board=board)
    h.apply(raise_to(100))  # seat 0 all-in
    h.apply(raise_to(300))  # seat 1 all-in
    assert h.legal_actions()["raise"] is None  # everyone else is all-in
    h.apply(CALL)  # seat 2 calls 300
    assert h.done
    assert stacks_of(h) == {0: 300, 1: 400, 2: 200}
    wins = [e for e in h.events if e["type"] == "win"]
    assert [w["amount"] for w in wins] == [300, 400]
    assert h.board == board


def test_split_pot_odd_chip_goes_left_of_button():
    holes = {0: ["2h", "3d"], 1: ["Ah", "Kd"], 2: ["Ac", "Ks"]}
    board = ["Qs", "Jc", "Th", "7d", "7c"]  # broadway for both 1 and 2
    h = make_hand([1000, 1000, 1000], button=0, sb=5, bb=10, ante=1, holes=holes, board=board)
    h.apply(CALL)  # seat 0 limps 10
    h.apply(CALL)  # seat 1 completes
    h.apply(CHECK)  # seat 2
    for _ in range(3):  # flop, turn, river: everybody checks
        h.apply(CHECK); h.apply(CHECK); h.apply(CHECK)
    assert h.done
    # pot = 3 antes + 30 = 33 -> 16 / 17, seat 1 (first left of button) gets the odd chip
    assert stacks_of(h) == {0: 989, 1: 1006, 2: 1005}


def test_illegal_actions():
    h = make_hand([1000, 1000, 1000], button=0)
    with pytest.raises(IllegalAction):
        h.apply(CHECK)
    with pytest.raises(IllegalAction):
        h.apply(raise_to(30))  # below min raise 40
    with pytest.raises(IllegalAction):
        h.apply(raise_to(5000))
    with pytest.raises(IllegalAction):
        h.apply(Action("raise"))
    with pytest.raises(IllegalAction):
        h.apply(Action("dance"))
    h.apply(CALL)
    h.apply(CALL)
    with pytest.raises(IllegalAction):
        h.apply(CALL)  # big blind can check, nothing to call


def test_all_in_short_of_min_raise_is_allowed():
    h = make_hand([1000, 1000, 30], button=0)  # bb seat 2 has 30 -> posts 20, 10 behind
    h.apply(raise_to(100))
    h.apply(FOLD)
    legal = h.legal_actions()  # seat 2 can only call all-in (10 more)
    assert legal["call"] == 10
    assert legal["raise"] is None


def test_ante_can_put_a_player_all_in():
    h = make_hand([1000, 1000, 5], button=0, ante=5)
    assert h.player_by_seat(2).all_in  # posted 5 ante, cannot post the big blind
    assert h.to_act.seat == 0


def test_public_events_hide_hole_cards_until_showdown():
    h = make_hand([1000, 1000], button=0)
    assert not any("cards" in e and e["type"] != "street" for e in h.public_events())
    h.apply(FOLD)
    assert h.events[-1]["type"] == "hand_end"


@st.composite
def random_hands(draw):
    n = draw(st.integers(2, 9))
    stacks = [draw(st.integers(1, 3000)) for _ in range(n)]
    button = draw(st.integers(0, n - 1))
    ante = draw(st.sampled_from([0, 0, 5]))
    choices = draw(st.lists(st.integers(0, 10_000), min_size=200, max_size=200))
    return stacks, button, ante, choices


@settings(max_examples=400, deadline=None)
@given(random_hands())
def test_random_hands_conserve_chips_and_terminate(params):
    stacks, button, ante, choices = params
    h = make_hand(stacks, button=button, ante=ante)
    total = sum(stacks)
    steps = 0
    for c in choices:
        if h.done:
            break
        legal = h.legal_actions()
        options = [FOLD]
        if legal["check"]:
            options.append(CHECK)
        if legal["call"] is not None:
            options.append(CALL)
        if legal["raise"]:
            lo, hi = legal["raise"]["min"], legal["raise"]["max"]
            options.append(raise_to(lo))
            options.append(raise_to(hi))
            options.append(raise_to(lo + c % (hi - lo + 1)))
        h.apply(options[c % len(options)])
        assert sum(p.stack for p in h.players) + h.pot == total or h.done
        steps += 1
    # play out with check/call if the random choices ran out
    while not h.done:
        legal = h.legal_actions()
        h.apply(CHECK if legal["check"] else CALL)
        steps += 1
        assert steps < 1000
    assert sum(p.stack for p in h.players) == total
    assert all(p.stack >= 0 for p in h.players)
    end = h.events[-1]
    assert end["type"] == "hand_end"
    assert sum(r["net"] for r in end["results"]) == 0
    assert len(h.board) in (0, 3, 4, 5)
