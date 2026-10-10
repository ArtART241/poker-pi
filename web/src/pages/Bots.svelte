<script>
  import { get } from "../lib/api.js";
  let bots = $state(null);
  $effect(() => {
    const load = () => get("/bots").then((b) => (bots = b));
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  });
</script>

<h1>Bots</h1>
<p class="muted">A green dot means the bot asked the server for a turn within the last minute.</p>
{#if bots}
  <div class="grid">
    {#each bots as b (b.name)}
      <a class="card-box bot" href="#/bot/{encodeURIComponent(b.name)}">
        <span class="dot" class:on={b.connected}></span>
        <div><div class="name">{b.name}</div><div class="muted small">by {b.owner}</div></div>
      </a>
    {:else}
      <p class="muted">No bots registered yet.</p>
    {/each}
  </div>
{/if}

<style>
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 0.7rem; }
  .bot { display: flex; gap: 0.8rem; align-items: center; color: var(--text); }
  .bot:hover { border-color: var(--accent); text-decoration: none; }
  .name { font-weight: 700; }
  .small { font-size: 0.85rem; }
  .dot { width: 0.7rem; height: 0.7rem; border-radius: 50%; background: var(--border); flex: none; }
  .dot.on { background: var(--good); }
</style>
