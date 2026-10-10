<script>
  // One playing card. The face style comes from the viewer setting (Drawn / Artwork).
  // To remove a style: delete its component/files and its entry in settings.svelte.js DECKS.
  import DrawnCard from "./cards/DrawnCard.svelte";
  import { deck } from "./settings.svelte.js";
  import { rankLabel } from "./cards/suits.js";

  let { card = null, size = "md", dim = false } = $props();

  const artworkSrc = (c) => `/cards/artwork/${rankLabel(c[0])}${c[1].toUpperCase()}.svg`;
</script>

{#if card}
  <span class="card {size}" class:dim title={card}>
    {#if deck() === "artwork"}
      <img src={artworkSrc(card)} alt={card} draggable="false" />
    {:else}
      <DrawnCard {card} />
    {/if}
  </span>
{:else}
  <span class="card back {size}" aria-label="hidden card"></span>
{/if}

<style>
  .card {
    display: inline-block;
    position: relative;
    aspect-ratio: 5 / 7;
    border-radius: 7%/5%;
    background: #fffdf6;
    box-shadow: 0 1px 4px rgb(0 0 0 / 0.45);
    overflow: hidden;
    user-select: none;
    transform-origin: 50% 100%;
    animation: flip 0.35s ease-out;
    transition: opacity 0.3s, filter 0.3s;
    flex: none;
  }
  .md { width: 2.6rem; }
  .lg { width: 3.4rem; }
  .sm { width: 1.7rem; }
  img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: fill;
  }
  .dim { opacity: 0.55; filter: grayscale(0.6); }
  .back {
    background:
      radial-gradient(circle at 50% 50%, transparent 0 28%, rgb(255 255 255 / 0.18) 29% 31%, transparent 32%),
      repeating-linear-gradient(45deg, rgb(255 255 255 / 0.14) 0 2px, transparent 2px 9px),
      repeating-linear-gradient(-45deg, rgb(255 255 255 / 0.14) 0 2px, transparent 2px 9px),
      #9b1c2c;
    border: 3px solid #fffdf6;
    animation: deal 0.3s ease-out;
  }
  @keyframes flip {
    from { transform: perspective(400px) rotateY(85deg); filter: brightness(0.7); }
    to { transform: perspective(400px) rotateY(0deg); }
  }
  @keyframes deal {
    from { transform: translateY(-14px) scale(0.85); opacity: 0; }
  }
</style>
