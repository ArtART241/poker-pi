<script>
  import { SUIT, RANK } from "./format.js";
  let { card = null, size = "md", dim = false } = $props();
</script>

{#if card}
  <span class="card {size} suit-{card[1]}" class:dim title={card}>
    <span class="rank">{RANK[card[0]] ?? card[0]}</span><span class="suit">{SUIT[card[1]]}</span>
  </span>
{:else}
  <span class="card back {size}" aria-label="hidden card"></span>
{/if}

<style>
  .card {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: #fdfdf8;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgb(0 0 0 / 0.45);
    font-weight: 700;
    line-height: 1;
    user-select: none;
    transition: transform 0.25s, opacity 0.25s;
    animation: deal 0.25s ease-out;
  }
  .md { width: 2.4rem; height: 3.3rem; font-size: 1.05rem; }
  .lg { width: 3.1rem; height: 4.3rem; font-size: 1.35rem; }
  .sm { width: 1.6rem; height: 2.2rem; font-size: 0.75rem; border-radius: 4px; }
  .suit { font-size: 1.1em; margin-top: 0.1em; }
  .suit-s { color: #1b1b1f; }
  .suit-h { color: #d22b2b; }
  .suit-d { color: #1f5fd1; }
  .suit-c { color: #13824b; }
  .dim { opacity: 0.45; }
  .back {
    background:
      repeating-linear-gradient(45deg, #8c1c2b 0 4px, #a8283a 4px 8px);
    border: 2px solid #fdfdf8;
  }
  @keyframes deal {
    from { transform: translateY(-6px) scale(0.9); opacity: 0; }
  }
</style>
