<script>
  import { get } from "../lib/api.js";
  import { countdown, when, ago } from "../lib/format.js";

  let tables = $state([]);
  let tournaments = $state([]);
  let error = $state("");
  let now = $state(Date.now());

  async function load() {
    try {
      [tables, tournaments] = await Promise.all([get("/tables"), get("/tournaments")]);
      error = "";
    } catch (e) {
      error = e.message;
    }
  }

  $effect(() => {
    load();
    const a = setInterval(load, 8000);
    const b = setInterval(() => (now = Date.now()), 1000);
    return () => (clearInterval(a), clearInterval(b));
  });

  const live = $derived(tables.filter((t) => t.status === "running"));
  const upcoming = $derived(tournaments.filter((t) => t.status === "registering").reverse());
  const past = $derived(tournaments.filter((t) => t.status === "finished" || t.status === "cancelled").slice(0, 12));
</script>

<section class="hero card-box">
  <div>
    <h1>Bots play poker. You watch.</h1>
    <p class="muted">
      Every player at these tables is a program written by one of us, in whatever language they like.
      The bots talk to this server over plain HTTP and play No-Limit Texas Hold'em tournaments.
    </p>
  </div>
  <div class="cta">
    <a class="btn primary" href="#/docs">Build a bot →</a>
    <a class="btn" href="#/leaderboard">Leaderboard</a>
  </div>
</section>

{#if error}<p class="error">Could not reach the server: {error}</p>{/if}

<h2>Live now</h2>
{#if live.length}
  <div class="cards">
    {#each live as t (t.id)}
      <a class="card-box tile" href={t.kind === "tournament" ? `#/tournament/${t.tournament_id}` : `#/table/${t.id}`}>
        <div class="row"><span class="pill live">{t.kind === "practice" ? "practice" : "live"}</span><span class="muted">Hand #{t.hand_no}</span></div>
        <div class="name">{t.title}</div>
        <div class="muted small">{t.players.join(" · ")}</div>
        {#if t.blinds}<div class="small">Level {t.blinds.level} · {t.blinds.small}/{t.blinds.big}</div>{/if}
      </a>
    {/each}
  </div>
{:else}
  <p class="muted">No table is running right now.</p>
{/if}

<h2>Upcoming tournaments</h2>
{#if upcoming.length}
  <div class="cards">
    {#each upcoming as t (t.id)}
      <a class="card-box tile" href="#/tournament/{t.id}">
        <div class="row"><span class="pill registering">registration open</span></div>
        <div class="name">{t.name}</div>
        <div class="small">{when(t.start_at)} · starts in <b>{countdown(t.start_at, now)}</b></div>
        <div class="muted small">{t.players.length}/{t.max_players} bots: {t.players.join(", ") || "nobody yet"}</div>
      </a>
    {/each}
  </div>
{:else}
  <p class="muted">Nothing scheduled yet.</p>
{/if}

<h2>Past tournaments</h2>
{#if past.length}
  <div class="card-box table-scroll">
    <table class="data">
      <thead><tr><th>Tournament</th><th>Finished</th><th>Players</th><th>Winner</th></tr></thead>
      <tbody>
        {#each past as t (t.id)}
          <tr>
            <td><a href="#/tournament/{t.id}">{t.name}</a> {#if t.status === "cancelled"}<span class="pill cancelled">cancelled</span>{/if}</td>
            <td class="muted">{ago(t.finished_at)}</td>
            <td>{t.players.length}</td>
            <td>{#if t.winner}🏆 <a href="#/bot/{encodeURIComponent(t.winner)}">{t.winner}</a>{:else}<span class="muted">{t.note ?? "-"}</span>{/if}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
{:else}
  <p class="muted">No tournaments played yet.</p>
{/if}

<style>
  .hero { display: flex; gap: 1.5rem; align-items: center; justify-content: space-between; flex-wrap: wrap; padding: 1.6rem;
    background: radial-gradient(ellipse at 0% 0%, color-mix(in srgb, #13693f 35%, var(--surface)), var(--surface)); }
  .hero p { max-width: 46rem; margin: 0; }
  .cta { display: flex; gap: 0.6rem; }
  .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 0.8rem; }
  .tile { color: var(--text); display: flex; flex-direction: column; gap: 0.3rem; transition: border-color 0.2s; }
  .tile:hover { border-color: var(--accent); text-decoration: none; }
  .row { display: flex; justify-content: space-between; align-items: center; }
  .name { font-weight: 800; font-size: 1.1rem; }
  .small { font-size: 0.87rem; }
</style>
