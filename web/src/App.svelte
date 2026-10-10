<script>
  import { route } from "./lib/router.svelte.js";
  import Lobby from "./pages/Lobby.svelte";
  import Tournament from "./pages/Tournament.svelte";
  import TablePage from "./pages/TablePage.svelte";
  import HandReplay from "./pages/HandReplay.svelte";
  import Leaderboard from "./pages/Leaderboard.svelte";
  import Bots from "./pages/Bots.svelte";
  import BotProfile from "./pages/BotProfile.svelte";
  import Docs from "./pages/Docs.svelte";
  import CardGallery from "./pages/CardGallery.svelte";
  import Settings from "./lib/Settings.svelte";

  const page = $derived(route.parts[0] ?? "");
  const arg = $derived(route.parts.slice(1).map(decodeURIComponent).join("/"));
  const nav = [
    ["", "Lobby"],
    ["leaderboard", "Leaderboard"],
    ["bots", "Bots"],
    ["docs", "Docs"],
  ];
  let menuOpen = $state(false);
</script>

<header>
  <div class="inner">
    <a class="logo" href="#/"><span class="suit">♠</span> poker-pi</a>
    <button class="burger" onclick={() => (menuOpen = !menuOpen)} aria-label="Menu">☰</button>
    <nav class:open={menuOpen}>
      {#each nav as [path, label] (path)}
        <a href="#/{path}" class:active={page === path || (path === "bots" && page === "bot")} onclick={() => (menuOpen = false)}>{label}</a>
      {/each}
      <a href="/docs" target="_blank" rel="noopener">API ↗</a>
    </nav>
    <Settings />
  </div>
</header>

<main>
  {#if page === ""}
    <Lobby />
  {:else if page === "tournament"}
    <Tournament id={arg} />
  {:else if page === "table"}
    <TablePage id={arg} />
  {:else if page === "hand"}
    <HandReplay id={arg} />
  {:else if page === "leaderboard"}
    <Leaderboard />
  {:else if page === "bots"}
    <Bots />
  {:else if page === "bot"}
    <BotProfile name={arg} />
  {:else if page === "cards"}
    <CardGallery />
  {:else if page === "docs"}
    <Docs slug={arg} />
  {:else}
    <h1>Not found</h1>
    <p><a href="#/">Back to the lobby</a></p>
  {/if}
</main>

<footer>
  <span>poker-pi · a bot poker league</span>
  <span><a href="#/docs">Write your own bot</a> · <a href="/openapi.yaml">openapi.yaml</a></span>
</footer>

<style>
  header {
    position: sticky;
    top: 0;
    z-index: 10;
    background: color-mix(in srgb, var(--bg) 85%, transparent);
    backdrop-filter: blur(8px);
    border-bottom: 1px solid var(--border);
  }
  .inner, main, footer { max-width: 1240px; margin: 0 auto; padding-inline: 16px; }
  .inner { display: flex; align-items: center; gap: 1rem; height: 3.4rem; }
  .logo { font-weight: 800; font-size: 1.15rem; color: var(--text); letter-spacing: -0.01em; }
  .logo .suit { color: var(--accent); }
  nav { display: flex; gap: 0.25rem; margin-left: auto; }
  nav a { color: var(--muted); padding: 0.35rem 0.7rem; border-radius: 8px; font-weight: 600; font-size: 0.93rem; }
  nav a:hover { color: var(--text); text-decoration: none; background: var(--surface-2); }
  nav a.active { color: var(--text); background: var(--surface-2); }
  .burger { display: none; margin-left: auto; }
  @media (max-width: 640px) { .inner :global(.settings) { margin-left: 0.5rem; } }
  main { padding-block: 1.5rem 3rem; min-height: 70vh; }
  footer { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; padding-block: 1.5rem; color: var(--muted); font-size: 0.85rem; border-top: 1px solid var(--border); }
  @media (max-width: 640px) {
    .burger { display: block; }
    nav { display: none; position: absolute; top: 3.4rem; left: 0; right: 0; flex-direction: column; background: var(--surface); border-bottom: 1px solid var(--border); padding: 0.5rem 16px; }
    nav.open { display: flex; }
  }
</style>
