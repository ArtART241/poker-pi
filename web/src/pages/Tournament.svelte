<script>
  import { get } from "../lib/api.js";
  import { countdown, when, chips } from "../lib/format.js";
  import LiveTable from "../lib/LiveTable.svelte";
  import HandList from "../lib/HandList.svelte";

  let { id } = $props();
  let t = $state(null);
  let hands = $state([]);
  let error = $state("");
  let now = $state(Date.now());

  async function load() {
    try {
      [t, hands] = await Promise.all([get(`/tournaments/${id}`), get(`/hands?tournament_id=${id}&limit=25`)]);
      error = "";
    } catch (e) {
      error = e.message;
    }
  }

  $effect(() => {
    id;
    load();
    const a = setInterval(() => t?.status === "registering" && load(), 5000);
    const b = setInterval(() => (now = Date.now()), 1000);
    return () => (clearInterval(a), clearInterval(b));
  });

  const medal = (p) => ({ 1: "🥇", 2: "🥈", 3: "🥉" })[p] ?? p;
</script>

{#if error}
  <p class="error">{error}</p>
{:else if t}
  <div class="head">
    <div>
      <h1>{t.name}</h1>
      <div class="muted">
        {#if t.status === "registering"}
          Starts {when(t.start_at)} · in <b>{countdown(t.start_at, now)}</b>
        {:else if t.status === "running"}
          Started {when(t.started_at)}
        {:else}
          {when(t.started_at)} - {when(t.finished_at)}
        {/if}
        · Starting stack {chips(t.starting_stack)} · Blinds up every {t.hands_per_level} hands
      </div>
    </div>
    <span class="pill {t.status === 'running' ? 'live' : t.status}">{t.status === "running" ? "live" : t.status}</span>
  </div>
  {#if t.note}<p class="muted">{t.note}</p>{/if}

  {#if t.status === "running"}
    <LiveTable tableId={t.table_id} onHandEnd={load} onFinished={load} />
  {/if}

  <div class="grid-2">
    <div>
      {#if t.status === "registering"}
        <h2>Registered bots ({t.players.length}/{t.max_players})</h2>
        <div class="card-box">
          {#if t.players.length}
            <ul class="players">{#each t.players as p (p)}<li><a href="#/bot/{encodeURIComponent(p)}">{p}</a></li>{/each}</ul>
          {:else}
            <p class="muted">No bots yet. Bots register through the API: <code>POST /api/v1/bot/tournaments/{t.id}/register</code></p>
          {/if}
        </div>
      {:else}
        <h2>{t.status === "finished" ? "Final standings" : "Standings"}</h2>
        <div class="card-box table-scroll">
          <table class="data">
            <thead><tr><th>Place</th><th>Bot</th><th class="num">Chips</th><th class="num">Points</th></tr></thead>
            <tbody>
              {#each t.standings as s (s.name)}
                <tr>
                  <td>{s.place ? medal(s.place) : "in play"}</td>
                  <td><a href="#/bot/{encodeURIComponent(s.name)}">{s.name}</a></td>
                  <td class="num">{s.stack ? chips(s.stack) : "-"}</td>
                  <td class="num">{t.results.find((r) => r.name === s.name)?.points ?? ""}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}

      <h2>Hands</h2>
      <div class="card-box"><HandList {hands} /></div>
    </div>
    <div>
      <h2>Blind schedule</h2>
      <div class="card-box table-scroll">
        <table class="data">
          <thead><tr><th>Level</th><th class="num">Small</th><th class="num">Big</th><th class="num">Ante</th></tr></thead>
          <tbody>
            {#each t.config.levels as [sb, bb, ante], i (i)}
              <tr><td>{i + 1}</td><td class="num">{sb}</td><td class="num">{bb}</td><td class="num">{ante || "-"}</td></tr>
            {/each}
          </tbody>
        </table>
        <p class="muted small">Each level lasts {t.hands_per_level} hands. Points: 1st 10, 2nd 6, 3rd 4, 4th 3, 5th 2, 6th 1.</p>
      </div>
    </div>
  </div>
{:else}
  <p class="muted">Loading…</p>
{/if}

<style>
  .head { display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem; margin-bottom: 1rem; }
  .players { columns: 2; margin: 0; padding-left: 1.2rem; }
  .small { font-size: 0.85rem; }
</style>
