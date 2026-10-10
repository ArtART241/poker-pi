<script>
  import { get } from "../lib/api.js";
  let rows = $state(null);
  $effect(() => {
    get("/leaderboard").then((r) => (rows = r));
  });
</script>

<h1>Leaderboard</h1>
<p class="muted">Points per tournament: 1st 10 · 2nd 6 · 3rd 4 · 4th 3 · 5th 2 · 6th 1. Practice tables do not count.</p>
{#if rows}
  <div class="card-box table-scroll">
    <table class="data">
      <thead>
        <tr><th>#</th><th>Bot</th><th>Owner</th><th class="num">Points</th><th class="num">Wins</th><th class="num">Tournaments</th><th class="num">Avg. place</th><th class="num">Hands</th></tr>
      </thead>
      <tbody>
        {#each rows as r, i (r.name)}
          <tr>
            <td>{i + 1}</td>
            <td><a href="#/bot/{encodeURIComponent(r.name)}"><b>{r.name}</b></a></td>
            <td class="muted">{r.owner}</td>
            <td class="num"><b>{r.points}</b></td>
            <td class="num">{r.wins}</td>
            <td class="num">{r.tournaments}</td>
            <td class="num">{r.avg_place ?? "-"}</td>
            <td class="num">{r.hands}</td>
          </tr>
        {:else}
          <tr><td colspan="8" class="muted">No bots yet.</td></tr>
        {/each}
      </tbody>
    </table>
  </div>
{:else}
  <p class="muted">Loading…</p>
{/if}
