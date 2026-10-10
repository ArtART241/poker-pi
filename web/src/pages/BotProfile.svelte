<script>
  import { get } from "../lib/api.js";
  import { chips, when } from "../lib/format.js";
  import HandList from "../lib/HandList.svelte";

  let { name } = $props();
  let bot = $state(null);
  let hands = $state([]);
  let error = $state("");

  $effect(() => {
    name;
    bot = null;
    Promise.all([get(`/bots/${encodeURIComponent(name)}`), get(`/hands?bot=${encodeURIComponent(name)}&limit=20`)]).then(
      ([b, h]) => ((bot = b), (hands = h)),
      (e) => (error = e.message),
    );
  });
</script>

{#if error}
  <p class="error">{error}</p>
{:else if bot}
  <h1><span class="dot" class:on={bot.connected}></span> {bot.name}</h1>
  <p class="muted">Built by {bot.owner} · registered {when(bot.created_at)}</p>
  {#if bot.tables.length}
    <p>Playing now: {#each bot.tables as t, i (t.table_id)}{i ? ", " : ""}<a href={t.kind === "practice" ? `#/table/${t.table_id}` : `#/table/${t.table_id}`}>{t.title}</a>{/each}</p>
  {/if}
  <div class="stats">
    <div class="card-box"><div class="v">{bot.stats.points}</div><div class="muted">points</div></div>
    <div class="card-box"><div class="v">{bot.stats.wins}</div><div class="muted">tournament wins</div></div>
    <div class="card-box"><div class="v">{bot.stats.hands}</div><div class="muted">tournament hands</div></div>
    <div class="card-box"><div class="v">{bot.stats.hands ? Math.round((100 * bot.stats.hands_won) / bot.stats.hands) : 0}%</div><div class="muted">hands won</div></div>
    <div class="card-box"><div class="v">{bot.stats.practice_hands}</div><div class="muted">practice hands</div></div>
  </div>

  <h2>Tournaments</h2>
  <div class="card-box table-scroll">
    <table class="data">
      <thead><tr><th>Tournament</th><th>Place</th><th class="num">Points</th></tr></thead>
      <tbody>
        {#each bot.stats.tournaments as t (t.tournament_id)}
          <tr><td><a href="#/tournament/{t.tournament_id}">{t.tournament}</a></td><td>{t.place} / {t.players}</td><td class="num">{t.points}</td></tr>
        {:else}
          <tr><td colspan="3" class="muted">No tournaments finished yet.</td></tr>
        {/each}
      </tbody>
    </table>
  </div>

  <h2>Recent hands</h2>
  <div class="card-box"><HandList {hands} /></div>
{:else}
  <p class="muted">Loading…</p>
{/if}

<style>
  .stats { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 0.7rem; }
  .v { font-size: 1.6rem; font-weight: 800; }
  .dot { display: inline-block; width: 0.8rem; height: 0.8rem; border-radius: 50%; background: var(--border); vertical-align: middle; }
  .dot.on { background: var(--good); }
</style>
