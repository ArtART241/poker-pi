<script>
  import Card from "./Card.svelte";
  import { chips } from "./format.js";
  import { collected } from "./reducer.js";

  let { table, title = "", subtitle = "" } = $props();

  const pos = (seat, rx, ry) => {
    const a = ((90 + seat * 40) * Math.PI) / 180;
    return `left:${50 + rx * Math.cos(a)}%;top:${50 + ry * Math.sin(a)}%`;
  };

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
        <span class="chip"></span>Pot {chips(middle)}
      </div>
      {#if subtitle}<div class="subtitle">{subtitle}</div>{/if}
    </div>

    {#each seats as s (s.seat)}
      {#if s.bet > 0}
        <div class="bet" style={pos(s.seat, 29, 21)}><span class="chip"></span>{chips(s.bet)}</div>
      {/if}
      {#if table.button === s.seat}
        <div class="dealer" style={pos(s.seat + 0.5, 33, 27)} title="Dealer button">D</div>
      {/if}
      <div
        class="seat"
        class:folded={s.status === "folded"}
        class:winner={s.winner}
        class:acting={table.toAct?.seat === s.seat}
        style={pos(s.seat, 45, 41)}
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
        {#if s.status === "all_in"}
          <div class="tag allin">ALL-IN</div>
        {:else if s.connection}
          <div class="tag warn">{s.connection.replace("_", " ")}</div>
        {:else if s.label}
          <div class="tag" class:win={s.winner}>{s.label}</div>
        {/if}
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
    top: 48%;
    transform: translate(-50%, -50%);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1cqw;
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
  .board { display: flex; gap: 0.6cqw; font-size: max(8px, 1.5cqw); }
  .board :global(.card.lg) { width: 6.2cqw; height: 8.6cqw; font-size: 2.6cqw; }
  .slot {
    width: 6.2cqw;
    height: 8.6cqw;
    border-radius: 6px;
    border: 1px dashed rgb(255 255 255 / 0.18);
  }
  .pot {
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 0.5em;
    background: rgb(0 0 0 / 0.3);
    padding: 0.2em 0.9em;
    border-radius: 99px;
    min-height: 1.4em;
  }
  .pot.empty { visibility: hidden; }
  .chip {
    display: inline-block;
    width: 0.95em;
    height: 0.95em;
    border-radius: 50%;
    background: #f2c14e;
    border: 0.18em dashed #fff;
    box-sizing: border-box;
  }
  .bet {
    position: absolute;
    transform: translate(-50%, -50%);
    font-size: max(10px, 1.45cqw);
    font-weight: 700;
    color: #fff;
    display: flex;
    gap: 0.35em;
    align-items: center;
    background: rgb(0 0 0 / 0.35);
    padding: 0.15em 0.6em;
    border-radius: 99px;
    transition: all 0.3s;
  }
  .dealer {
    position: absolute;
    transform: translate(-50%, -50%);
    width: 2.6cqw;
    height: 2.6cqw;
    min-width: 16px;
    min-height: 16px;
    border-radius: 50%;
    background: #fff;
    color: #111;
    font-weight: 800;
    font-size: max(9px, 1.4cqw);
    display: grid;
    place-items: center;
    box-shadow: 0 1px 3px rgb(0 0 0 / 0.5);
    transition: all 0.5s;
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
  .seat.folded { opacity: 0.55; }
  .cards {
    display: flex;
    gap: 0.4cqw;
    height: 6.2cqw;
    margin-bottom: -1.6cqw;
    z-index: 0;
  }
  .cards :global(.card.md) { width: 4.4cqw; height: 6.1cqw; font-size: 1.9cqw; border-radius: 0.6cqw; }
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
  .winner .plate { border-color: #4ade80; box-shadow: 0 0 2.4cqw rgb(74 222 128 / 0.6); }
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
  .tag {
    margin-top: 0.4cqw;
    font-size: max(9px, 1.2cqw);
    padding: 0.1em 0.6em;
    border-radius: 99px;
    background: rgb(0 0 0 / 0.55);
    color: #e5e7eb;
    white-space: nowrap;
    max-width: 22cqw;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .tag.win { background: #15803d; color: #fff; font-weight: 700; }
  .tag.allin { background: #b91c1c; color: #fff; font-weight: 800; letter-spacing: 0.05em; }
  .tag.warn { background: #92400e; color: #fff; }
  @container (max-width: 560px) {
    .felt { aspect-ratio: 1 / 1.25; }
    .title, .subtitle { display: none; }
    .seat { width: 24cqw; }
    .avatar { display: none; }
    .cards { height: 9cqw; margin-bottom: -2cqw; }
    .cards :global(.card.md) { width: 6.4cqw; height: 8.8cqw; font-size: 2.8cqw; }
    .board :global(.card.lg), .slot { width: 10cqw; height: 13.8cqw; }
    .board :global(.card.lg) { font-size: 4cqw; }
    .name, .stack, .tag, .bet { font-size: 9px; }
  }
</style>
