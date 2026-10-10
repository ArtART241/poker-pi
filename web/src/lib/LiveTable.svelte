<script>
  import PokerTable from "./PokerTable.svelte";
  import ActionLog from "./ActionLog.svelte";
  import { streamTable } from "./api.js";
  import { apply, emptyTable, fromSnapshot } from "./reducer.js";
  import { soundForEvent } from "./sound.js";

  let { tableId, onHandEnd = () => {}, onFinished = () => {} } = $props();

  let table = $state(emptyTable());
  let meta = $state(null);
  let connection = $state("connecting");

  $effect(() => {
    const id = tableId;
    table = emptyTable();
    const close = streamTable(
      id,
      (ev) => {
        if (ev.type === "snapshot") {
          meta = ev.table;
          table = fromSnapshot(ev.table);
          return;
        }
        table = apply(table, ev);
        soundForEvent(ev);
        if (ev.type === "hand_end") onHandEnd(ev);
        if (ev.type === "table_status" && meta) meta = { ...meta, status: ev.status, finish_reason: ev.reason };
        if (ev.type === "table_status" && ev.status === "finished") onFinished();
      },
      (s) => (connection = s),
    );
    return close;
  });

  const subtitle = $derived(
    table.blinds
      ? `Level ${table.level ?? "?"} · Blinds ${table.blinds.small}/${table.blinds.big}${table.blinds.ante ? ` · Ante ${table.blinds.ante}` : ""}`
      : "",
  );
</script>

<div class="live">
  <div>
    <div class="bar">
      <span class="dot {connection}"></span>
      {#if meta?.status === "finished"}
        <span>Finished{meta.finish_reason ? ` - ${meta.finish_reason}` : ""}</span>
      {:else if connection === "live"}
        <span>Live</span>
      {:else}
        <span>{connection}…</span>
      {/if}
      {#if table.handNo}<span class="muted">· Hand #{table.handNo}</span>{/if}
      {#if table.blinds}<span class="muted">· {table.blinds.small}/{table.blinds.big}</span>{/if}
      {#if meta?.spectators !== undefined}<span class="muted">· {meta.kind}</span>{/if}
    </div>
    <PokerTable {table} title={meta?.title ?? ""} {subtitle} />
  </div>
  <div>
    <h2 class="side">Action</h2>
    <ActionLog log={table.log} height="30rem" />
  </div>
</div>

<style>
  .live { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr); gap: 1rem; }
  @media (max-width: 1100px) { .live { grid-template-columns: minmax(0, 1fr); } }
  .bar { display: flex; gap: 0.5rem; align-items: center; font-size: 0.9rem; font-weight: 600; }
  .dot { width: 0.6rem; height: 0.6rem; border-radius: 50%; background: var(--muted); }
  .dot.live { background: #ef4444; box-shadow: 0 0 0 0 rgb(239 68 68 / 0.7); animation: pulse 1.6s infinite; }
  .dot.reconnecting { background: var(--accent); }
  .side { margin-top: 0; }
  @keyframes pulse { 70% { box-shadow: 0 0 0 0.5rem rgb(239 68 68 / 0); } 100% { box-shadow: 0 0 0 0 rgb(239 68 68 / 0); } }
</style>
