<script>
  import { get } from "../lib/api.js";
  import { when } from "../lib/format.js";
  import { replay } from "../lib/reducer.js";
  import PokerTable from "../lib/PokerTable.svelte";
  import ActionLog from "../lib/ActionLog.svelte";

  let { id } = $props();
  let hand = $state(null);
  let error = $state("");
  let step = $state(0);
  let playing = $state(false);
  let speed = $state(1);

  // the steps worth pausing on (skip bookkeeping events)
  const visible = (e) => !["deal_hole", "post"].includes(e.type);
  const stops = $derived(hand ? [0, ...hand.events.map((e, i) => (visible(e) ? i + 1 : null)).filter((x) => x !== null)] : [0]);
  const firstStop = $derived(hand ? hand.events.findIndex((e) => e.type === "action") : 0);
  const table = $derived(hand ? replay(hand.events, stops[step] || firstStop) : null);

  $effect(() => {
    id;
    hand = null;
    get(`/hands/${id}`).then(
      (h) => {
        hand = h;
        step = 0;
        playing = true;
      },
      (e) => (error = e.message),
    );
  });

  $effect(() => {
    // read everything synchronously so the effect re-runs after each step
    const current = step;
    const last = stops.length - 1;
    const delay = 1100 / speed;
    if (!playing || !hand) return;
    const t = setTimeout(() => {
      if (current < last) step = current + 1;
      else playing = false;
    }, delay);
    return () => clearTimeout(t);
  });
</script>

{#if error}
  <p class="error">{error}</p>
{:else if hand && table}
  <div class="head">
    <div>
      <h1>Hand #{hand.hand_no} <span class="muted">replay</span></h1>
      <div class="muted">
        {when(hand.started_at)} ·
        {#if hand.tournament_id}<a href="#/tournament/{hand.tournament_id}">tournament</a>{:else if hand.practice}practice table{/if}
        · <a href="#/table/{hand.table_id}">table {hand.table_id}</a>
      </div>
    </div>
    <div class="nav">
      <a class="btn" href="#/hand/{hand.id - 1}">← Previous</a>
      <a class="btn" href="#/hand/{hand.id + 1}">Next →</a>
    </div>
  </div>
  <div class="grid-2">
    <div>
      <PokerTable {table} subtitle={table.blinds ? `Blinds ${table.blinds.small}/${table.blinds.big}` : ""} />
      <div class="controls card-box">
        <button onclick={() => ((playing = false), (step = 0))} title="Start">⏮</button>
        <button onclick={() => ((playing = false), (step = Math.max(0, step - 1)))} title="Back">◀</button>
        <button class="primary" onclick={() => { if (step >= stops.length - 1) step = 0; playing = !playing; }}>
          {playing ? "Pause" : "Play"}
        </button>
        <button onclick={() => ((playing = false), (step = Math.min(stops.length - 1, step + 1)))} title="Forward">▶</button>
        <button onclick={() => ((playing = false), (step = stops.length - 1))} title="End">⏭</button>
        <input type="range" min="0" max={stops.length - 1} bind:value={step} oninput={() => (playing = false)} />
        <select bind:value={speed}>
          <option value={0.5}>0.5×</option><option value={1}>1×</option><option value={2}>2×</option><option value={4}>4×</option>
        </select>
      </div>
    </div>
    <div>
      <h2 class="side">Action</h2>
      <ActionLog log={table.log} height="30rem" />
      <details class="raw">
        <summary>Raw events (what your bot sees in <code>action_log</code>)</summary>
        <pre>{JSON.stringify(hand.events, null, 1)}</pre>
      </details>
    </div>
  </div>
{:else}
  <p class="muted">Loading…</p>
{/if}

<style>
  .head { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 1rem; }
  .nav { display: flex; gap: 0.5rem; }
  .controls { display: flex; gap: 0.4rem; align-items: center; flex-wrap: wrap; margin-top: 0.5rem; padding: 0.6rem; }
  .controls input[type="range"] { flex: 1; min-width: 120px; }
  .side { margin-top: 0; }
  .raw { margin-top: 1rem; font-size: 0.85rem; }
  .raw pre { max-height: 20rem; overflow: auto; background: var(--code-bg); padding: 0.6rem; border-radius: 8px; }
</style>
