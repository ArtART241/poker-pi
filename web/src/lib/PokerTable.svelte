<script>
  import { untrack } from "svelte";
  import Card from "./Card.svelte";
  import ChipStack from "./ChipStack.svelte";
  import { chips } from "./format.js";
  import { collected } from "./reducer.js";

  let { table, title = "", subtitle = "" } = $props();

  // seat k sits at angle 90° + k·40° (seat 0 at the bottom, clockwise)
  const at = (seat, rx, ry) => {
    const a = ((90 + seat * 40) * Math.PI) / 180;
    return { x: 50 + rx * Math.cos(a), y: 50 + ry * Math.sin(a) };
  };
  const css = ({ x, y }) => `left:${x}%;top:${y}%`;
  const SEAT = [45, 41];
  const BET = [29, 21];
  const POT = { x: 50, y: 62 };

  let now = $state(Date.now());
  $effect(() => {
    const t = setInterval(() => (now = Date.now()), 200);
    return () => clearInterval(t);
  });

  const seats = $derived(Object.values(table.seats).sort((a, b) => a.seat - b.seat));
  const middle = $derived(Math.max(0, collected(table)));
  const timer = $derived(
    table.toAct ? Math.max(0, Math.min(1, (table.toAct.until - now) / (table.toAct.total || 1))) : 0,
  );
  const initials = (name) =>
    name
      .split(/[\s_-]+/)
      .map((w) => w[0])
      .join("")
      .slice(0, 2)
      .toUpperCase();

  // ---- flying chips: bets slide into the pot, the pot slides to the winner
  let ghosts = $state([]);
  let ghostId = 0;
  let prev = { seq: 0, hand: null, bets: {}, win: null };

  function fly(from, to, amount) {
    const id = ++ghostId;
    untrack(() => ghosts.push({ id, from, to, amount }));
    setTimeout(() => (ghosts = ghosts.filter((g) => g.id !== id)), 700);
  }

  $effect(() => {
    const seq = table.seq;
    const forward = table.handId === prev.hand && seq > prev.seq;
    const bets = Object.fromEntries(Object.values(table.seats).map((s) => [s.seat, s.bet]));
    if (forward) {
      for (const [seat, bet] of Object.entries(prev.bets)) {
        if (bet > 0 && (bets[seat] ?? 0) === 0) fly(at(+seat, ...BET), POT, bet);
      }
      if (table.lastWin && table.lastWin !== prev.win) {
        for (const w of table.lastWin.winners) setTimeout(() => fly(POT, at(w.seat, ...SEAT), w.amount), 250);
      }
    }
    prev = { seq, hand: table.handId, bets, win: table.lastWin };
  });
</script>

<div class="wrap">
  <div class="felt">
    <div class="rail"></div>
    <div class="center">
      {#if title}<div class="title">{title}</div>{/if}
      <div class="board">
        {#each [0, 1, 2, 3, 4] as i (i)}
          {#if table.board[i]}
            {#key table.board[i]}<Card card={table.board[i]} size="lg" />{/key}
          {:else}
            <span class="slot"></span>
          {/if}
        {/each}
      </div>
      <div class="pot" class:empty={middle <= 0}>
        <ChipStack amount={middle} scale={2.2} maxColumns={6} />
        <span class="amount">Pot {chips(middle)}</span>
      </div>
      {#if subtitle}<div class="subtitle">{subtitle}</div>{/if}
    </div>

    {#each seats as s (s.seat)}
      {#if s.bet > 0}
        <div class="bet" style={css(at(s.seat, ...BET))}>
          <ChipStack amount={s.bet} scale={1.7} maxColumns={3} />
          <span class="amount">{chips(s.bet)}</span>
        </div>
      {/if}
      {#if table.button === s.seat}
        <div class="dealer" style={css(at(s.seat + 0.5, 33, 27))} title="Dealer button: {s.name} is the dealer this hand">D</div>
      {/if}
      <div
        class="seat"
        class:folded={s.status === "folded"}
        class:winner={s.winner}
        class:acting={table.toAct?.seat === s.seat}
        style={css(at(s.seat, ...SEAT))}
      >
        <div class="cards">
          {#if s.status !== "folded" || s.cards}
            <Card card={s.cards?.[0]} size="md" dim={s.status === "folded"} />
            <Card card={s.cards?.[1]} size="md" dim={s.status === "folded"} />
          {/if}
        </div>
        <div class="plate">
          <div class="avatar">{initials(s.name)}</div>
          <div class="info">
            <div class="name" title={s.name}>{s.name}</div>
            <div class="stack">{s.stack > 0 || s.status === "all_in" ? chips(s.stack) : "busted"}</div>
          </div>
          {#if table.toAct?.seat === s.seat}
            <div class="timer" style="transform:scaleX({timer})"></div>
          {/if}
        </div>
        {#if s.connection}
          <div class="badge status">{s.connection.replace("_", " ")}</div>
        {:else if s.action}
          {#key s.action.text}
            <div class="badge {s.action.kind}" title={s.action.text}>{s.action.text}</div>
          {/key}
        {/if}
      </div>
    {/each}

    {#if table.flash}
      {#key table.flash.seq}
        <div class="flash {table.flash.kind}" style={css(at(table.flash.seat, 45, 41))}>
          {table.flash.text}
        </div>
      {/key}
    {/if}

    {#each ghosts as g (g.id)}
      <div class="ghost" style="--x0:{g.from.x}%;--y0:{g.from.y}%;--x1:{g.to.x}%;--y1:{g.to.y}%">
        <ChipStack amount={g.amount} scale={1.7} maxColumns={3} />
      </div>
    {/each}
  </div>
</div>

<style>
  .wrap {
    container-type: inline-size;
    width: 100%;
    padding: 4cqw 7cqw 9cqw;
    box-sizing: border-box;
  }
  .felt {
    position: relative;
    aspect-ratio: 2 / 1.08;
    border-radius: 50% / 50%;
    background: radial-gradient(ellipse at 50% 40%, #1f8a55 0%, #13693f 55%, #0c4f2f 100%);
    box-shadow:
      inset 0 0 4cqw rgb(0 0 0 / 0.45),
      0 0 0 1.4cqw #5b3a1e,
      0 0 0 1.7cqw #3c2513,
      0 2cqw 5cqw rgb(0 0 0 / 0.5);
  }
  .rail {
    position: absolute;
    inset: 4%;
    border-radius: 50% / 50%;
    border: 1px solid rgb(255 255 255 / 0.12);
  }
  .center {
    position: absolute;
    left: 50%;
    top: 47%;
    transform: translate(-50%, -50%);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.8cqw;
    font-size: max(11px, 1.6cqw);
    color: #e8f5ec;
  }
  .title {
    font-size: max(11px, 1.5cqw);
    letter-spacing: 0.15em;
    text-transform: uppercase;
    opacity: 0.6;
  }
  .subtitle { opacity: 0.75; font-size: max(10px, 1.3cqw); }
  .board { display: flex; gap: 0.7cqw; }
  .board :global(.card.lg), .slot { width: 7.4cqw; }
  .slot {
    aspect-ratio: 5 / 7;
    border-radius: 7%/5%;
    border: 1px dashed rgb(255 255 255 / 0.18);
  }
  .pot, .bet {
    display: flex;
    align-items: flex-end;
    gap: 0.5em;
    font-weight: 800;
    color: #fff;
  }
  .pot { min-height: 3.2cqw; font-size: max(11px, 1.55cqw); }
  .pot.empty { visibility: hidden; }
  .amount {
    background: rgb(0 0 0 / 0.45);
    padding: 0.1em 0.6em;
    border-radius: 99px;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  .bet {
    position: absolute;
    transform: translate(-50%, -50%);
    font-size: max(10px, 1.4cqw);
  }
  .ghost {
    position: absolute;
    transform: translate(-50%, -50%);
    font-size: max(10px, 1.4cqw);
    pointer-events: none;
    animation: fly 0.55s cubic-bezier(0.5, 0, 0.3, 1) forwards;
  }
  @keyframes fly {
    from { left: var(--x0); top: var(--y0); }
    to { left: var(--x1); top: var(--y1); opacity: 0.15; }
  }
  .dealer {
    position: absolute;
    transform: translate(-50%, -50%);
    width: 3cqw;
    height: 3cqw;
    min-width: 18px;
    min-height: 18px;
    border-radius: 50%;
    background: radial-gradient(circle at 35% 30%, #fff, #e7e2d6);
    border: 2px solid #c9c2b0;
    box-shadow: 0 2px 4px rgb(0 0 0 / 0.55), inset 0 0 0 2px #fff;
    color: #1b1b1f;
    font-weight: 900;
    font-size: max(9px, 1.45cqw);
    display: grid;
    place-items: center;
    cursor: help;
    transition: left 0.6s, top 0.6s;
  }
  .seat {
    position: absolute;
    transform: translate(-50%, -50%);
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 17cqw;
    transition: opacity 0.3s;
  }
  .seat.folded { opacity: 0.6; }
  .cards {
    display: flex;
    gap: 0.4cqw;
    margin-bottom: -2cqw;
    z-index: 0;
    min-height: 2cqw;
  }
  .cards :global(.card.md) { width: 4.9cqw; }
  .plate {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    gap: 0.8cqw;
    width: 100%;
    box-sizing: border-box;
    padding: 0.6cqw 1cqw;
    background: #15181d;
    border: 2px solid #2b3139;
    border-radius: 1.4cqw;
    color: #f1f3f5;
    overflow: hidden;
    box-shadow: 0 0.6cqw 1.6cqw rgb(0 0 0 / 0.45);
    transition: border-color 0.3s, box-shadow 0.3s;
  }
  .acting .plate { border-color: #f2c14e; box-shadow: 0 0 2cqw rgb(242 193 78 / 0.55); }
  .winner .plate { border-color: #facc15; box-shadow: 0 0 2.6cqw rgb(250 204 21 / 0.7); }
  .avatar {
    flex: none;
    width: 3.4cqw;
    height: 3.4cqw;
    border-radius: 50%;
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    display: grid;
    place-items: center;
    font-weight: 800;
    font-size: max(8px, 1.3cqw);
  }
  .info { min-width: 0; line-height: 1.15; }
  .name {
    font-weight: 700;
    font-size: max(10px, 1.45cqw);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .stack { font-size: max(10px, 1.35cqw); color: #f2c14e; font-variant-numeric: tabular-nums; }
  .timer {
    position: absolute;
    left: 0;
    bottom: 0;
    height: 3px;
    width: 100%;
    background: #f2c14e;
    transform-origin: left;
    transition: transform 0.2s linear;
  }

  /* action badges: stay visible for the rest of the betting round */
  .badge {
    margin-top: 0.5cqw;
    font-size: max(10px, 1.3cqw);
    font-weight: 800;
    padding: 0.15em 0.75em;
    border-radius: 99px;
    color: #fff;
    background: #374151;
    white-space: nowrap;
    max-width: 24cqw;
    overflow: hidden;
    text-overflow: ellipsis;
    box-shadow: 0 2px 6px rgb(0 0 0 / 0.4);
    animation: pop 0.35s cubic-bezier(0.3, 1.6, 0.6, 1);
    z-index: 2;
  }
  .badge.fold { background: #4b5563; color: #d1d5db; }
  .badge.check { background: #2563eb; }
  .badge.call { background: #16a34a; }
  .badge.raise { background: #ea580c; }
  .badge.allin { background: #dc2626; animation: pop 0.35s cubic-bezier(0.3, 1.6, 0.6, 1), pulse 1.2s ease-in-out 0.4s infinite; }
  .badge.blind { background: #6d28d9; }
  .badge.win { background: linear-gradient(90deg, #facc15, #f59e0b); color: #1c1403; }
  .badge.status { background: #92400e; }
  @keyframes pop {
    from { transform: scale(0.4); opacity: 0; }
  }
  @keyframes pulse {
    50% { box-shadow: 0 0 0 0.5cqw rgb(220 38 38 / 0.35), 0 2px 6px rgb(0 0 0 / 0.4); }
  }

  /* big pop-up when an action happens, above the player's cards */
  .flash {
    position: absolute;
    transform: translate(-50%, -50%);
    z-index: 5;
    pointer-events: none;
    font-size: max(13px, 2.1cqw);
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    white-space: nowrap;
    color: #fff;
    padding: 0.25em 0.8em;
    border-radius: 0.5em;
    border: 2px solid rgb(255 255 255 / 0.85);
    box-shadow: 0 0.4em 1.2em rgb(0 0 0 / 0.5);
    text-shadow: 0 1px 2px rgb(0 0 0 / 0.4);
    animation: flash 1.4s ease-out forwards;
  }
  .flash.fold { background: #4b5563; }
  .flash.check { background: #2563eb; }
  .flash.call { background: #16a34a; }
  .flash.raise { background: #ea580c; }
  .flash.allin { background: #dc2626; font-size: max(15px, 2.8cqw); }
  @keyframes flash {
    0% { transform: translate(-50%, -150%) scale(0.4); opacity: 0; }
    12% { transform: translate(-50%, -260%) scale(1.2); opacity: 1; }
    24% { transform: translate(-50%, -250%) scale(1); }
    78% { transform: translate(-50%, -260%) scale(1); opacity: 1; }
    100% { transform: translate(-50%, -300%) scale(0.95); opacity: 0; }
  }

  @container (max-width: 460px) {
    .felt { aspect-ratio: 1 / 1.25; }
    .title, .subtitle { display: none; }
    .seat { width: 24cqw; }
    .avatar { display: none; }
    .cards :global(.card.md) { width: 7cqw; }
    .board :global(.card.lg), .slot { width: 11cqw; }
    .name, .stack, .badge, .bet, .ghost { font-size: 9px; }
    .flash { font-size: 13px; }
  }
</style>
