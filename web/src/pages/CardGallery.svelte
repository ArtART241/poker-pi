<script>
  // All 52 cards in the selected style, for comparing the decks.
  import Card from "../lib/Card.svelte";
  import { settings, deck, DECKS } from "../lib/settings.svelte.js";

  const ranks = "AKQJT98765432".split("");
  const suits = ["s", "h", "d", "c"];
  let size = $state(110);
</script>

<h1>Card gallery</h1>
<div class="controls">
  {#each DECKS as d (d.id)}
    <button class:primary={deck() === d.id} onclick={() => (settings.deck = d.id)}>{d.label}</button>
  {/each}
  <label>Size <input type="range" min="40" max="220" bind:value={size} /></label>
</div>

{#each suits as s (s)}
  <div class="row" style="--w:{size}px">
    {#each ranks as r (r)}
      <Card card={r + s} size="gallery" />
    {/each}
    <Card card={null} size="gallery" />
  </div>
{/each}

<style>
  .controls { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; margin-bottom: 1rem; }
  .controls label { display: flex; gap: 0.5rem; align-items: center; margin-left: 1rem; }
  .row { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 16px; padding: 16px; border-radius: 12px; background: #13693f; }
  .row :global(.card.gallery) { width: var(--w); }
</style>
