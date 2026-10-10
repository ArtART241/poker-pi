<script>
  import { get } from "../lib/api.js";
  import LiveTable from "../lib/LiveTable.svelte";
  import HandList from "../lib/HandList.svelte";

  let { id } = $props();
  let hands = $state([]);
  let exists = $state(true);

  async function load() {
    hands = await get(`/hands?table_id=${encodeURIComponent(id)}&limit=25`);
  }
  $effect(() => {
    id;
    get(`/tables/${encodeURIComponent(id)}`).then(() => (exists = true), () => (exists = false));
    load();
  });
</script>

{#if exists}
  <LiveTable tableId={id} onHandEnd={load} />
{:else}
  <p class="muted">This table is not running any more. Its hands are still listed below.</p>
{/if}
<h2>Hands at this table</h2>
<div class="card-box"><HandList {hands} /></div>
