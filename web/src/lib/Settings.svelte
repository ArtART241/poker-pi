<script>
  import { settings, server, deck, DECKS } from "./settings.svelte.js";
  import { play } from "./sound.js";
  import Card from "./Card.svelte";

  let open = $state(false);
  let box = $state();

  $effect(() => {
    if (!open) return;
    const close = (e) => box && !box.contains(e.target) && (open = false);
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  });

  const recorded = $derived(new Set(server.sounds.map((f) => f.replace(/\.[^.]+$/, "").replace(/_\d+$/, ""))));
</script>

<div class="settings" bind:this={box}>
  <button class="gear" onclick={() => (open = !open)} aria-label="Settings" aria-expanded={open} title="Settings">
    {settings.sound ? "🔊" : "🔇"} ⚙
  </button>
  {#if open}
    <div class="panel card-box">
      <div class="label">Card style</div>
      <div class="decks">
        {#each DECKS as d (d.id)}
          <button class="deck" class:on={deck() === d.id} onclick={() => (settings.deck = d.id)}>
            <span class="preview">
              {#key deck()}
                {#if deck() === d.id}
                  <Card card="Kh" size="sm" /><Card card="7s" size="sm" />
                {:else}
                  <span class="muted">{d.label}</span>
                {/if}
              {/key}
            </span>
            {d.label}{server.deck === d.id ? " (default)" : ""}
          </button>
        {/each}
      </div>

      <a class="small" href="#/cards" onclick={() => (open = false)}>See all 52 cards →</a>

      <div class="label sound">Sound</div>
      <label class="row">
        <input type="checkbox" bind:checked={settings.sound} onchange={() => settings.sound && play("chips", "check")} />
        Play sounds
      </label>
      <label class="row">
        Volume
        <input type="range" min="0" max="1" step="0.05" bind:value={settings.volume} disabled={!settings.sound} />
      </label>
      <p class="muted small">
        {#if recorded.size}
          {recorded.size} sound{recorded.size === 1 ? "" : "s"} recorded.
        {:else}
          No sounds recorded yet.
        {/if}
      </p>
    </div>
  {/if}
</div>

<style>
  .settings { position: relative; }
  .gear { font-size: 0.95rem; padding: 0.3rem 0.6rem; }
  .panel {
    position: absolute;
    right: 0;
    top: calc(100% + 0.5rem);
    width: 260px;
    z-index: 30;
    box-shadow: 0 10px 30px rgb(0 0 0 / 0.4);
  }
  .label { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); margin: 0.2rem 0 0.4rem; }
  .decks { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin-bottom: 0.5rem; }
  .deck { display: flex; flex-direction: column; align-items: center; gap: 0.3rem; font-size: 0.8rem; padding: 0.5rem; }
  .deck.on { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
  .preview { display: flex; gap: 3px; height: 2.5rem; align-items: center; }
  .label.sound { margin-top: 0.9rem; }
  .row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.9rem; margin: 0.3rem 0; }
  .row input[type="range"] { flex: 1; }
  .small { font-size: 0.8rem; margin: 0.4rem 0 0; }
</style>
