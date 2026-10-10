<script>
  let { log = [], height = "22rem" } = $props();
  let box = $state();
  $effect(() => {
    log.length;
    if (box) box.scrollTop = box.scrollHeight;
  });
</script>

<div class="log card-box" bind:this={box} style="max-height:{height}">
  {#each log as line, i (i)}
    <div class="line {line.kind}">{line.text}</div>
  {:else}
    <div class="muted">Nothing happened yet.</div>
  {/each}
</div>

<style>
  .log { overflow-y: auto; font-size: 0.87rem; padding: 0.6rem 0.8rem; }
  .line { padding: 0.12rem 0; border-bottom: 1px dashed transparent; }
  .hand { margin-top: 0.6rem; font-weight: 700; color: var(--accent); }
  .street { color: var(--link); font-weight: 600; }
  .win { color: var(--good); font-weight: 700; }
  .showdown { font-style: italic; }
  .status, .out { color: var(--bad); }
  .fold { color: var(--muted); }
</style>
