<script>
  import Card from "./Card.svelte";
  import { chips, ago } from "./format.js";
  let { hands = [] } = $props();
</script>

<div class="table-scroll">
  <table class="data">
    <thead>
      <tr><th>Hand</th><th>Blinds</th><th>Board</th><th>Winner</th><th class="num">Pot</th><th></th></tr>
    </thead>
    <tbody>
      {#each hands as h (h.id)}
        <tr>
          <td><a href="#/hand/{h.id}">#{h.hand_no}</a> <span class="muted">{ago(h.ended_at)}</span></td>
          <td>{h.blinds ? `${h.blinds[0]}/${h.blinds[1]}` : ""}</td>
          <td class="board">{#each h.board as c (c)}<Card card={c} size="sm" />{/each}</td>
          <td>{h.winners.join(", ")} {#if h.winning_hand}<span class="muted">({h.winning_hand})</span>{/if}</td>
          <td class="num">{chips(h.pot)}</td>
          <td><a href="#/hand/{h.id}">Replay ▶</a></td>
        </tr>
      {:else}
        <tr><td colspan="6" class="muted">No finished hands yet.</td></tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .board { display: flex; gap: 2px; min-height: 2.4rem; align-items: center; }
</style>
