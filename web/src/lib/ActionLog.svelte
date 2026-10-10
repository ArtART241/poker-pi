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
  .line.fold { color: var(--muted); }
  .line.check::before, .line.call::before, .line.raise::before, .line.allin::before {
    content: "";
    display: inline-block;
    width: 0.55em;
    height: 0.55em;
    border-radius: 50%;
    margin-right: 0.5em;
    vertical-align: 0.05em;
  }
  .line.check::before { background: #3b82f6; }
  .line.call::before { background: #16a34a; }
  .line.raise::before { background: #ea580c; }
  .line.raise { font-weight: 600; }
  .line.allin::before { background: #dc2626; }
  .line.allin { font-weight: 800; color: #ef4444; }
</style>
