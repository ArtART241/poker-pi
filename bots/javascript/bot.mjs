// poker-pi starter bot (Node.js 18+, no packages needed: uses the built-in fetch).
//
// Run:
//   export POKER_TOKEN="pk_..."                          # your bot token
//   export POKER_URL="https://poker.example.com"    # optional, default http://localhost:8000
//   node bot.mjs             # play tournaments
//   node bot.mjs practice    # start a practice table against house bots first
//
// Only decide() needs to change to make the bot smarter.

const BASE_URL = (process.env.POKER_URL ?? "http://localhost:8000").replace(/\/$/, "");
const TOKEN = process.env.POKER_TOKEN ?? "";
const RANKS = "23456789TJQKA";

// ---------------------------------------------------------------------------- your strategy

function decide(state) {
  const legal = state.legal;
  const [c1, c2] = state.hole_cards;
  const r1 = RANKS.indexOf(c1[0]);
  const r2 = RANKS.indexOf(c2[0]);

  const pair = r1 === r2;
  const high = Math.max(r1, r2) >= RANKS.indexOf("T") && Math.min(r1, r2) >= RANKS.indexOf("9");
  const strong = pair || high || Math.max(r1, r2) === RANKS.indexOf("A");

  const bigBlind = state.blinds.big;
  const nobodyRaised = state.current_bet <= bigBlind;
  if (strong && legal.raise && nobodyRaised) {
    // raise TO 3 big blinds (amount = your total bet on this street), within the legal range
    const amount = Math.max(legal.raise.min, 3 * bigBlind);
    return { action: "raise", amount: Math.min(amount, legal.raise.max) };
  }
  if (legal.check) return { action: "check" };
  if (strong || state.to_call <= Math.floor(state.stack / 20)) return { action: "call" };
  return { action: "fold" };
}

// ---------------------------------------------------------------------------- HTTP plumbing

async function api(method, path, body) {
  const res = await fetch(BASE_URL + path, {
    method,
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      "User-Agent": "poker-pi-starter-bot/1.0 (node)",
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(40_000),
  });
  const text = await res.text();
  return { status: res.status, data: text ? JSON.parse(text) : null };
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function registerForOpenTournaments() {
  const { status, data } = await api("GET", "/api/v1/bot/tournaments");
  if (status !== 200) return console.log("could not list tournaments:", status, data);
  for (const t of data) {
    if (t.status === "registering" && !t.registered) {
      const r = await api("POST", `/api/v1/bot/tournaments/${t.id}/register`);
      console.log(`register for '${t.name}' (starts ${t.start_at}):`, r.status, r.data);
    }
  }
}

async function main() {
  if (!TOKEN) {
    console.error("Set the POKER_TOKEN environment variable to your bot token.");
    process.exit(1);
  }
  const me = await api("GET", "/api/v1/bot/me");
  if (me.status !== 200) {
    console.error(`Token check failed (${me.status}):`, me.data);
    process.exit(1);
  }
  console.log(`Hello ${me.data.name}! Talking to ${BASE_URL}`);

  if (process.argv[2] === "practice") {
    const p = await api("POST", "/api/v1/bot/practice", { opponents: ["random", "station", "tight"] });
    console.log("practice table:", p.status, p.data?.watch_url ?? p.data);
  }

  await registerForOpenTournaments();
  let lastCheck = Date.now();

  while (true) {
    if (Date.now() - lastCheck > 300_000) {
      await registerForOpenTournaments();
      lastCheck = Date.now();
    }
    let turn;
    try {
      turn = await api("GET", "/api/v1/bot/turn?wait=25");
    } catch (err) {
      console.log("network error:", err.message);
      await sleep(2000);
      continue;
    }
    if (turn.status === 204) continue; // not our turn yet, ask again
    if (turn.status !== 200) {
      console.log("unexpected answer:", turn.status, turn.data);
      await sleep(2000);
      continue;
    }

    const state = turn.data;
    const action = decide(state);
    const res = await api("POST", "/api/v1/bot/action", { turn_id: state.turn_id, ...action });
    console.log(
      `hand ${state.hand_id} ${state.street.padEnd(7)} ${state.hole_cards.join(" ")} | ` +
        `board ${(state.board.join(" ") || "-").padEnd(14)} -> ${JSON.stringify(action)} [${res.status}]`,
    );
    if (res.status === 422) {
      // our action was not legal: say why, then play it safe so we do not time out
      console.log("  rejected:", res.data.detail);
      const safe = state.legal.check ? "check" : "fold";
      await api("POST", "/api/v1/bot/action", { turn_id: state.turn_id, action: safe });
    } else if (res.status !== 200) {
      console.log("  server said:", res.data);
    }
  }
}

main();
