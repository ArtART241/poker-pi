// Turns the server's event stream into something a table view can draw.
// Used by both the live view (events arrive over SSE) and the replay viewer (events from a stored hand).

export function emptyTable() {
  return {
    handId: null,
    handNo: null,
    level: null,
    button: null,
    blinds: null,
    street: null,
    board: [],
    pot: 0, // everything in the middle, including current bets
    seats: {}, // seat -> { seat, name, stack, bet, status, cards, label, winner, connection }
    toAct: null, // { seat, until } (live only)
    log: [], // [{ text, kind }]
    winners: [],
    finished: false,
  };
}

const clone = (s) => ({
  ...s,
  seats: Object.fromEntries(Object.entries(s.seats).map(([k, v]) => [k, { ...v }])),
  board: [...s.board],
  log: [...s.log],
  winners: [...s.winners],
});

export function collected(state) {
  // chips already in the pot (not counting the bets in front of the players)
  return state.pot - Object.values(state.seats).reduce((sum, s) => sum + (s.bet || 0), 0);
}

const STREET_NAME = { flop: "Flop", turn: "Turn", river: "River" };

function say(state, text, kind = "info") {
  state.log.push({ text, kind });
  if (state.log.length > 400) state.log.shift();
}

export function apply(prev, ev, { now = Date.now() } = {}) {
  const s = clone(prev);
  const seat = ev.seat !== undefined ? s.seats[ev.seat] : undefined;

  switch (ev.type) {
    case "hand_start": {
      const old = s.seats;
      s.seats = {};
      for (const p of ev.players) {
        s.seats[p.seat] = {
          seat: p.seat,
          name: p.name,
          stack: p.stack,
          bet: 0,
          status: "active",
          cards: null,
          label: "",
          winner: false,
          connection: old[p.seat]?.connection ?? null,
        };
      }
      Object.assign(s, {
        handId: ev.hand_id,
        handNo: ev.hand_no ?? s.handNo,
        level: ev.level ?? s.level,
        button: ev.button,
        blinds: { small: ev.small_blind, big: ev.big_blind, ante: ev.ante },
        street: "preflop",
        board: [],
        pot: 0,
        toAct: null,
        winners: [],
        finished: false,
      });
      say(s, `Hand #${ev.hand_no ?? ev.hand_id} - blinds ${ev.small_blind}/${ev.big_blind}${ev.ante ? ` ante ${ev.ante}` : ""}`, "hand");
      break;
    }
    case "post":
      if (!seat) break;
      seat.stack -= ev.amount;
      if (ev.blind !== "ante") seat.bet += ev.amount;
      if (ev.all_in) seat.status = "all_in";
      s.pot += ev.amount;
      seat.label = ev.blind === "ante" ? "Ante" : ev.blind === "small" ? "Small blind" : "Big blind";
      break;
    case "deal_hole": // only present in replays
      if (seat) seat.cards = ev.cards;
      break;
    case "action": {
      if (!seat) break;
      seat.stack = ev.stack;
      seat.bet = ev.bet;
      s.pot = ev.pot;
      if (ev.action === "fold") seat.status = "folded";
      else if (ev.all_in) seat.status = "all_in";
      const label = actionLabel(ev);
      seat.label = label;
      s.toAct = null;
      say(s, `${ev.name} ${label.toLowerCase()}`, ev.action);
      break;
    }
    case "street":
      for (const p of Object.values(s.seats)) {
        p.bet = 0;
        if (p.status !== "folded") p.label = "";
      }
      s.board = ev.board;
      s.street = ev.street;
      s.pot = ev.pot;
      say(s, `${STREET_NAME[ev.street]}: ${ev.cards.join(" ")}`, "street");
      break;
    case "uncalled":
      if (!seat) break;
      seat.stack += ev.amount;
      seat.bet -= ev.amount;
      s.pot -= ev.amount;
      say(s, `${ev.amount} returned to ${ev.name} (uncalled)`);
      break;
    case "showdown":
      for (const h of ev.hands) if (s.seats[h.seat]) s.seats[h.seat].cards = h.cards;
      say(s, `Showdown: ${ev.hands.map((h) => `${h.name} ${h.cards.join(" ")}`).join(", ")}`, "showdown");
      break;
    case "win":
      for (const p of Object.values(s.seats)) p.bet = 0;
      for (const w of ev.winners) {
        const p = s.seats[w.seat];
        if (!p) continue;
        p.stack += w.amount;
        p.winner = true;
        p.label = ev.hand ? `Wins ${w.amount} - ${ev.hand}` : `Wins ${w.amount}`;
        s.winners.push(w.seat);
      }
      s.pot -= ev.amount;
      say(
        s,
        `${ev.winners.map((w) => `${w.name} wins ${w.amount}`).join(", ")}${ev.hand ? ` with ${ev.hand}` : ""}${ev.pot > 0 ? ` (side pot ${ev.pot})` : ""}`,
        "win",
      );
      break;
    case "hand_end":
      for (const r of ev.results) {
        const p = s.seats[r.seat];
        if (!p) continue;
        p.stack = r.stack;
        if (!p.cards) p.cards = r.cards;
      }
      s.pot = 0;
      s.toAct = null;
      s.finished = true;
      break;
    case "player_status":
      if (!seat) break;
      seat.connection = ev.status === "back" || ev.status === "connected" ? null : ev.status;
      say(s, `${ev.name}: ${statusText(ev.status)}`, "status");
      break;
    case "turn":
      s.toAct = { seat: ev.seat, until: now + ev.timeout_ms, total: ev.timeout_ms };
      break;
    case "eliminated":
      say(s, `${ev.name} is out${ev.place ? ` - finishes #${ev.place}` : ""}`, "out");
      break;
    case "tournament_end":
      say(s, ev.winner ? `${ev.winner} wins the tournament!` : "Tournament over", "win");
      break;
    case "table_status":
      if (ev.status === "finished") say(s, `Table closed${ev.reason ? `: ${ev.reason}` : ""}`, "hand");
      break;
  }
  return s;
}

export function actionLabel(ev) {
  switch (ev.action) {
    case "fold":
      return "Folds";
    case "check":
      return "Checks";
    case "call":
      return ev.all_in ? `Calls ${ev.amount} (all-in)` : `Calls ${ev.amount}`;
    case "raise":
      return ev.all_in ? `All-in ${ev.amount}` : `Raises to ${ev.amount}`;
    default:
      return ev.action;
  }
}

function statusText(status) {
  return (
    {
      timeout: "timed out (auto check/fold)",
      sitting_out: "sitting out after repeated timeouts",
      disconnected: "disconnected",
      connected: "connected again",
      back: "back in the game",
    }[status] ?? status
  );
}

// Build a table state from a full list of events (replays, snapshots).
export function replay(events, upTo = events.length) {
  let s = emptyTable();
  for (let i = 0; i < upTo; i++) s = apply(s, events[i]);
  return s;
}

// Initial live state from a /public/tables/{id} snapshot.
export function fromSnapshot(snap) {
  let s = emptyTable();
  if (snap.events?.length) {
    s = replay(snap.events);
  } else {
    for (const p of snap.seats) {
      s.seats[p.seat] = { seat: p.seat, name: p.name, stack: p.stack, bet: 0, status: "active", cards: null, label: "", winner: false, connection: null };
    }
    s.button = snap.button;
  }
  for (const p of snap.seats) {
    if (s.seats[p.seat] && (p.status === "disconnected" || p.status === "sitting_out")) s.seats[p.seat].connection = p.status;
  }
  // players eliminated after the current hand started are no longer listed in snap.seats
  if (snap.waiting_on) {
    s.toAct = { seat: snap.waiting_on.seat, until: Date.now() + snap.waiting_on.remaining_ms, total: snap.waiting_on.remaining_ms };
  }
  s.level = snap.blinds?.level ?? s.level;
  return s;
}
