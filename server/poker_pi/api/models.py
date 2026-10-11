"""Request/response models. They exist mostly to produce a precise OpenAPI spec that code
generators (Dart, Java, Go, TypeScript, ...) can turn into working clients: every response is a
named object, nothing is typed as "any object", and nullable fields are explicit."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Error(BaseModel):
    detail: str = Field(description="Human readable explanation of what went wrong.")


class RaiseRange(BaseModel):
    min: int = Field(description="Smallest total bet to raise TO.")
    max: int = Field(description="Largest total bet to raise TO (= all-in).")


class Legal(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    fold: bool = Field(description="Folding is always allowed.")
    check: bool = Field(description="True if nothing is owed, so checking is allowed.")
    call: int | None = Field(description="Chips a call would add, or null if there is nothing to call.")
    raise_: RaiseRange | None = Field(
        alias="raise", description="Allowed range for a raise (raise TO), or null if raising is not allowed."
    )


class PlayerView(BaseModel):
    seat: int
    name: str
    stack: int = Field(description="Chips behind (not counting chips already bet).")
    bet: int = Field(description="Chips this player has bet on the current street.")
    committed: int = Field(description="Chips this player has put into the pot during the whole hand.")
    status: Literal["active", "folded", "all_in"]
    is_you: bool


class BlindsInfo(BaseModel):
    small: int
    big: int
    ante: int
    level: int
    hands_until_next_level: int


# ---------------------------------------------------------------------------------------- events
# Every event has a "type"; the other fields depend on the type (see the docs). Fields that a type
# does not use are left out of the JSON, which is why all of them are optional here.


class EventPlayer(BaseModel):
    seat: int
    name: str
    player_id: str
    stack: int


class ShownHand(BaseModel):
    seat: int
    name: str
    cards: list[str]


class PotWinner(BaseModel):
    seat: int
    name: str
    amount: int


class HandResult(BaseModel):
    seat: int
    name: str
    player_id: str
    start_stack: int
    stack: int
    net: int
    cards: list[str]


class Event(BaseModel):
    """One thing that happened in a hand. `type` says which of the optional fields are present."""

    model_config = ConfigDict(extra="allow")

    type: str = Field(description="hand_start, post, deal_hole, action, street, uncalled, showdown, win, "
                                  "hand_end or player_status.")
    seat: int | None = None
    name: str | None = None
    # hand_start
    hand_id: int | None = None
    hand_no: int | None = None
    level: int | None = None
    button: int | None = None
    small_blind: int | None = None
    big_blind: int | None = None
    ante: int | None = None
    players: list[EventPlayer] | None = None
    # post
    blind: str | None = Field(default=None, description="post: small, big or ante.")
    # action
    street: str | None = None
    action: str | None = Field(default=None, description="action: fold, check, call or raise.")
    amount: int | None = Field(default=None, description="action: chips added (call) or new total bet (raise); "
                                                         "post/uncalled/win: chips.")
    bet: int | None = None
    stack: int | None = None
    all_in: bool | None = None
    pot: int | None = Field(default=None, description="action/street: chips in the middle; win: pot index "
                                                      "(0 = main pot).")
    # street, deal_hole
    cards: list[str] | None = None
    board: list[str] | None = None
    # showdown
    hands: list[ShownHand] | None = None
    # win
    winners: list[PotWinner] | None = None
    hand: str | None = Field(default=None, description="win: name of the winning hand, null without showdown.")
    # hand_end
    results: list[HandResult] | None = None
    # player_status
    status: str | None = Field(default=None, description="player_status: timeout, sitting_out, disconnected, "
                                                         "connected or back.")


# ---------------------------------------------------------------------------------------- bot API


class TurnState(BaseModel):
    turn_id: str = Field(description="Identifies this decision; send it back with the action.")
    deadline_ms: int = Field(description="Milliseconds left before the server checks/folds automatically.")
    table_id: str
    tournament_id: int | None = Field(description="null at practice tables.")
    practice: bool
    hand_id: int
    hand_no: int = Field(description="Number of the hand at this table (1, 2, 3, ...).")
    seat: int = Field(description="The bot's seat (0-8).")
    name: str
    hole_cards: list[str] = Field(description='The two private cards, e.g. ["Ah", "Td"].')
    stack: int = Field(description="Chips behind.")
    bet: int = Field(description="Chips already bet on this street.")
    street: Literal["preflop", "flop", "turn", "river"]
    board: list[str] = Field(description="Community cards (0, 3, 4 or 5).")
    pot: int = Field(description="All chips in the middle, including the bets of this street.")
    current_bet: int = Field(description="Highest bet on this street.")
    to_call: int = Field(description="Chips needed to call (0 if checking is possible).")
    legal: Legal
    blinds: BlindsInfo
    button: int = Field(description="Seat of the dealer button.")
    players: list[PlayerView]
    action_log: list[Event] = Field(description="Everything public that happened in this hand so far.")


class ActionRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [
        {"turn_id": "t_3f9a0c1b2d4e5f60", "action": "call"},
        {"turn_id": "t_3f9a0c1b2d4e5f60", "action": "raise", "amount": 120},
    ]})

    turn_id: str = Field(description="The turn_id from GET /turn.")
    action: str = Field(description="fold | check | call | raise (also accepted: bet = raise, allin).")
    amount: int | None = Field(default=None, description="Only for raise: the total bet to raise TO.")


class ActionResponse(BaseModel):
    accepted: bool
    action: str
    amount: int | None = None


class TableRef(BaseModel):
    table_id: str
    kind: Literal["tournament", "practice"]
    seat: int
    stack: int
    status: str


class BotTournamentResult(BaseModel):
    tournament_id: int
    tournament: str = Field(description="Tournament name.")
    finished_at: str | None
    place: int
    points: int
    players: int


class BotStats(BaseModel):
    hands: int = Field(description="Tournament hands played.")
    hands_won: int
    net_chips: int
    practice_hands: int
    tournaments: list[BotTournamentResult]
    points: int
    wins: int


class MeResponse(BaseModel):
    id: str
    name: str
    owner: str
    tables: list[TableRef] = Field(description="Tables the bot is currently seated at.")
    open_turns: int = Field(description="Turns waiting for an answer right now.")
    registered_tournaments: list[int]
    stats: BotStats


class TournamentInfo(BaseModel):
    id: int
    name: str
    status: Literal["registering", "running", "finished", "cancelled"]
    start_at: str
    started_at: str | None
    finished_at: str | None
    note: str | None
    table_id: str
    players: list[str] = Field(description="Registered bots (or the field, once started).")
    max_players: int
    starting_stack: int
    hands_per_level: int
    registered: bool | None = Field(default=None, description="Whether the requesting bot is registered "
                                                              "(bot API only).")
    winner: str | None = None


class RegistrationResponse(BaseModel):
    tournament_id: int
    registered: bool


class Opponent(str, Enum):
    random = "random"
    station = "station"
    tight = "tight"


class PracticeSpeed(str, Enum):
    fast = "fast"
    live = "live"


class PracticeRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [
        {"opponents": ["random", "station", "tight"], "speed": "fast"},
    ]})

    opponents: list[Opponent] | None = Field(
        default=None, min_length=1, max_length=8,
        description="House bots to play against: random, station (calls everything), tight (only plays good "
                    "hands). Default: one of each.",
    )
    speed: PracticeSpeed | None = Field(
        default=None, description="fast (default): no pauses. live: same pace as tournaments.")
    starting_stack: int | None = Field(default=None, ge=100, le=100_000, description="Default 1500.")


class SeatInfo(BaseModel):
    seat: int
    name: str
    stack: int
    status: str = Field(description="active, sitting_out, disconnected or busted.")
    house: bool = Field(description="True for built-in practice opponents.")


class PracticeResponse(BaseModel):
    table_id: str
    status: str
    finish_reason: str | None
    hand_no: int
    players: list[SeatInfo]
    watch_url: str


class HandSummary(BaseModel):
    id: int
    table_id: str
    tournament_id: int | None
    practice: bool
    hand_no: int
    started_at: str
    ended_at: str | None
    blinds: list[int] | None
    players: list[str]
    pot: int
    winners: list[str]
    winning_hand: str | None
    board: list[str]
    showdown: bool


class HandDetail(BaseModel):
    id: int
    table_id: str
    tournament_id: int | None
    practice: bool
    hand_no: int
    started_at: str
    ended_at: str | None
    events: list[Event] = Field(description="Complete history including everybody's hole cards.")


# ---------------------------------------------------------------------------------------- public API


class TableSummary(BaseModel):
    id: str
    kind: Literal["tournament", "practice"]
    title: str
    tournament_id: int | None
    status: str = Field(description="waiting, running or finished.")
    hand_no: int
    players: list[str]
    blinds: BlindsInfo | None


class WaitingOn(BaseModel):
    seat: int
    remaining_ms: int


class PacingInfo(BaseModel):
    action: float
    street: float
    hand_end: float


class TableSnapshot(BaseModel):
    id: str
    kind: Literal["tournament", "practice"]
    title: str
    tournament_id: int | None
    status: str = Field(description="waiting, running or finished.")
    finish_reason: str | None
    hand_no: int
    hand_id: int | None
    blinds: BlindsInfo | None
    button: int | None
    seats: list[SeatInfo]
    events: list[Event] = Field(description="Public events of the current (or last) hand; no hidden cards.")
    waiting_on: WaitingOn | None
    pacing: PacingInfo
    spectators: int


class TournamentConfig(BaseModel):
    starting_stack: int
    hands_per_level: int
    levels: list[list[int]] = Field(description="Blind levels as [small, big, ante].")
    pacing: PacingInfo
    max_players: int


class ResultRow(BaseModel):
    place: int
    points: int
    name: str
    owner: str
    bot_id: str


class Standing(BaseModel):
    name: str
    stack: int
    place: int | None = Field(description="null while the bot is still in play.")


class TournamentDetail(TournamentInfo):
    config: TournamentConfig
    results: list[ResultRow]
    standings: list[Standing]
    live: bool


class LeaderboardRow(BaseModel):
    name: str
    owner: str
    points: int
    tournaments: int
    wins: int
    avg_place: float | None
    best_place: int | None
    hands: int


class BotInfo(BaseModel):
    name: str
    owner: str
    created_at: str
    connected: bool


class BotTable(BaseModel):
    table_id: str
    kind: Literal["tournament", "practice"]
    title: str


class BotProfile(BotInfo):
    tables: list[BotTable]
    stats: BotStats
