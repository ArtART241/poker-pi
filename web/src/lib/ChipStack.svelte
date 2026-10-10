<script>
  // A stack of casino chips showing an amount, split into denominations (largest first).
  let { amount = 0, scale = 1.6, maxColumns = 5 } = $props();

  // value, face, edge, stripe (classic casino colours)
  const DENOMS = [
    [25000, "#7dd3fc", "#0284c7", "#fff"],
    [5000, "#f97316", "#c2410c", "#fff"],
    [1000, "#facc15", "#ca8a04", "#422006"],
    [500, "#8b5cf6", "#6d28d9", "#fff"],
    [100, "#27272a", "#09090b", "#fff"],
    [25, "#16a34a", "#166534", "#fff"],
    [5, "#dc2626", "#991b1b", "#fff"],
    [1, "#f4f4f0", "#b8b8ae", "#2563eb"],
  ];
  const PER_COLUMN = 8;
  const LAYER = 4; // height of one chip edge in svg units
  const W = 24; // chip width in svg units (= 1em at scale 1)

  const columns = $derived.by(() => {
    let rest = Math.max(0, Math.floor(amount));
    const cols = [];
    for (const [value, face, edge, stripe] of DENOMS) {
      let n = Math.floor(rest / value);
      rest -= n * value;
      while (n > 0 && cols.length < maxColumns) {
        const take = Math.min(n, PER_COLUMN);
        cols.push({ n: take, face, edge, stripe });
        n -= take;
      }
    }
    return cols;
  });
  const height = $derived(Math.max(1, ...columns.map((c) => c.n)) * LAYER + 10);
  const width = $derived(Math.max(1, columns.length) * (W + 3));
</script>

{#if columns.length}
  <svg
    viewBox="0 0 {width} {height}"
    style="width:{(width / W) * scale}em;height:{(height / W) * scale}em"
    aria-hidden="true"
  >
    {#each columns as col, ci (ci)}
      {#each { length: col.n } as _, i (i)}
        {@const x = ci * (W + 3)}
        {@const y = height - 6 - i * LAYER}
        <g class="chip" style="animation-delay:{(ci * PER_COLUMN + i) * 12}ms">
          <rect {x} y={y - LAYER / 2} width={W} height={LAYER + 1} fill={col.edge} />
          {#each [3, 10.5, 18] as sx (sx)}
            <rect x={x + sx} y={y - LAYER / 2} width="3" height={LAYER + 1} fill={col.stripe} opacity="0.85" />
          {/each}
          <ellipse cx={x + W / 2} cy={y - LAYER / 2} rx={W / 2} ry="4.5" fill={col.face} stroke={col.edge} stroke-width="0.8" />
          <ellipse cx={x + W / 2} cy={y - LAYER / 2} rx={W / 2 - 3.5} ry="2.8" fill="none" stroke={col.stripe} stroke-width="0.9" stroke-dasharray="2.2 1.6" opacity="0.9" />
        </g>
      {/each}
    {/each}
  </svg>
{/if}

<style>
  svg {
    display: block;
    overflow: visible;
    filter: drop-shadow(0 1px 1.5px rgb(0 0 0 / 0.55));
  }
  .chip {
    animation: drop 0.25s ease-out backwards;
  }
  @keyframes drop {
    from { transform: translateY(-6px); opacity: 0; }
  }
</style>
