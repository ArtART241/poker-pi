<script>
  // A playing card drawn entirely in SVG: corner indices, real pip layouts for A-10,
  // and double-headed court cards (J, Q, K) in a simplified traditional style.
  import { SUIT_PATH, RED, BLACK, isRed, rankLabel } from "./suits.js";

  let { card } = $props();

  const rank = $derived(card[0]);
  const suit = $derived(card[1]);
  const color = $derived(isRed(suit) ? RED : BLACK);
  const label = $derived(rankLabel(rank));

  // pip centres in a 250 x 350 card
  const L = 82, M = 125, R = 168;
  const T = 80, B = 270, C = 175;
  const r4 = [80, 143, 207, 270];
  const LAYOUT = {
    "2": [[M, T], [M, B]],
    "3": [[M, T], [M, C], [M, B]],
    "4": [[L, T], [R, T], [L, B], [R, B]],
    "5": [[L, T], [R, T], [M, C], [L, B], [R, B]],
    "6": [[L, T], [R, T], [L, C], [R, C], [L, B], [R, B]],
    "7": [[L, T], [R, T], [M, 127], [L, C], [R, C], [L, B], [R, B]],
    "8": [[L, T], [R, T], [M, 127], [L, C], [R, C], [M, 223], [L, B], [R, B]],
    "9": [...r4.flatMap((y) => [[L, y], [R, y]]), [M, C]],
    T: [...r4.flatMap((y) => [[L, y], [R, y]]), [M, 111], [M, 239]],
  };
  const pips = $derived(LAYOUT[rank] ?? []);
  const court = $derived(rank === "J" || rank === "Q" || rank === "K");

  // court palette: robes alternate by suit so the twelve court cards don't all look the same
  const ROBES = {
    h: ["#1d3f8f", "#c4161c", "#e2a72e"],
    d: ["#c4161c", "#1d3f8f", "#e2a72e"],
    s: ["#1d3f8f", "#e2a72e", "#c4161c"],
    c: ["#c4161c", "#e2a72e", "#1d3f8f"],
  };
  const robe = $derived(ROBES[suit]);

  const pip = (x, y, size, flip = false) =>
    `translate(${x} ${y}) ${flip ? "rotate(180)" : ""} scale(${size / 100}) translate(-50 -50)`;
</script>

<svg viewBox="0 0 250 350" xmlns="http://www.w3.org/2000/svg" role="img" aria-label={card}>
  <rect x="2" y="2" width="246" height="346" rx="18" fill="#fffdf6" stroke="#cfc8b8" stroke-width="3" />

  <!-- corner indices -->
  {#each [false, true] as rotated (rotated)}
    <g fill={color} transform={rotated ? "rotate(180 125 175)" : ""}>
      <text
        x="32"
        y="64"
        text-anchor="middle"
        font-family="'Times New Roman', Times, 'Liberation Serif', serif"
        font-weight="700"
        font-size={label === "10" ? 48 : 58}
        letter-spacing={label === "10" ? -5 : 0}>{label}</text
      >
      <path d={SUIT_PATH[suit]} transform={pip(32, 92, 34)} />
    </g>
  {/each}

  {#if rank === "A"}
    {#if suit === "s"}
      <ellipse cx="125" cy="175" rx="74" ry="84" fill="none" stroke={BLACK} stroke-width="2" />
      <ellipse cx="125" cy="175" rx="66" ry="76" fill="none" stroke={BLACK} stroke-width="1" stroke-dasharray="4 5" />
      <path d={SUIT_PATH.s} transform={pip(125, 172, 112)} fill={BLACK} />
    {:else}
      <path d={SUIT_PATH[suit]} transform={pip(125, 175, 96)} fill={color} />
    {/if}
  {:else if court}
    <!-- frame -->
    <rect x="58" y="44" width="134" height="262" rx="6" fill="#fff6dc" stroke={color} stroke-width="3" />
    <clipPath id="frame-{card}"><rect x="59.5" y="45.5" width="131" height="259" rx="5" /></clipPath>
    <g clip-path="url(#frame-{card})">
      {#each [false, true] as rotated (rotated)}
        <g transform={rotated ? "rotate(180 125 175)" : ""}>
          <!-- attribute behind the figure -->
          {#if rank === "K"}
            <rect x="160" y="62" width="6" height="104" fill="#9aa3ad" stroke={BLACK} stroke-width="1.5" />
            <rect x="152" y="96" width="22" height="6" rx="2" fill={robe[2]} stroke={BLACK} stroke-width="1.5" />
          {:else if rank === "Q"}
            <line x1="163" y1="80" x2="163" y2="160" stroke="#2f7a3b" stroke-width="3" />
            <circle cx="163" cy="76" r="9" fill={robe[1]} stroke={BLACK} stroke-width="1.5" />
            <circle cx="163" cy="76" r="3.5" fill={robe[2]} />
          {:else}
            <line x1="164" y1="58" x2="150" y2="168" stroke="#7a5230" stroke-width="4" />
            <path d="M158 54 L174 62 L166 78 Z" fill="#9aa3ad" stroke={BLACK} stroke-width="1.5" />
          {/if}

          <!-- robe with trims -->
          <path d="M66 175 L72 138 Q90 124 125 122 Q160 124 178 138 L184 175 Z" fill={robe[0]} stroke={BLACK} stroke-width="2" />
          <path d="M110 123 L125 175 L140 123 Q125 121 110 123 Z" fill={robe[1]} stroke={BLACK} stroke-width="1.5" />
          <path d="M72 140 Q98 128 125 127 Q152 128 178 140" fill="none" stroke={robe[2]} stroke-width="5" />
          {#each [84, 100, 150, 166] as x (x)}
            <circle cx={x} cy={158} r="3" fill={robe[2]} stroke={BLACK} stroke-width="1" />
          {/each}

          <!-- hair (queen) behind the face -->
          {#if rank === "Q"}
            <path d="M101 98 Q100 132 108 126 L142 126 Q150 132 149 98 Q146 76 125 75 Q104 76 101 98 Z" fill="#6b3a1e" stroke={BLACK} stroke-width="1.5" />
          {/if}

          <!-- face -->
          <ellipse cx="125" cy="103" rx="17" ry="20" fill="#f6d7b0" stroke={BLACK} stroke-width="2" />
          <circle cx="119" cy="100" r="1.8" fill={BLACK} />
          <circle cx="131" cy="100" r="1.8" fill={BLACK} />
          <path d="M120 112 Q125 115 130 112" fill="none" stroke={BLACK} stroke-width="1.5" />
          {#if rank === "K"}
            <path d="M109 108 Q112 132 125 134 Q138 132 141 108 Q133 117 125 116 Q117 117 109 108 Z" fill="#8a8f96" stroke={BLACK} stroke-width="1.5" />
            <path d="M118 111 Q125 107 132 111" fill="none" stroke={BLACK} stroke-width="1.5" />
          {/if}

          <!-- headwear -->
          {#if rank === "K"}
            <path d="M104 88 L102 62 L113 74 L125 56 L137 74 L148 62 L146 88 Z" fill={robe[2]} stroke={BLACK} stroke-width="2" />
            <rect x="103" y="84" width="44" height="7" fill={robe[2]} stroke={BLACK} stroke-width="1.5" />
            <circle cx="125" cy="76" r="3.5" fill={RED} />
            <circle cx="112" cy="80" r="2.5" fill="#1d3f8f" />
            <circle cx="138" cy="80" r="2.5" fill="#1d3f8f" />
          {:else if rank === "Q"}
            <path d="M106 88 Q108 70 116 78 Q120 62 125 64 Q130 62 134 78 Q142 70 144 88 Z" fill={robe[2]} stroke={BLACK} stroke-width="2" />
            {#each [112, 125, 138] as x (x)}
              <circle cx={x} cy={x === 125 ? 67 : 76} r="2.6" fill="#fff" stroke={BLACK} stroke-width="1" />
            {/each}
          {:else}
            <path d="M100 90 Q104 70 125 70 Q146 70 150 90 Z" fill={robe[1]} stroke={BLACK} stroke-width="2" />
            <rect x="100" y="86" width="50" height="6" fill={robe[2]} stroke={BLACK} stroke-width="1.5" />
            <path d="M144 76 Q160 54 150 44 Q156 62 140 74 Z" fill={robe[0]} stroke={BLACK} stroke-width="1.5" />
          {/if}

          <!-- suit emblem -->
          <path d={SUIT_PATH[suit]} transform={pip(80, 66, 28)} fill={color} />
        </g>
      {/each}
      <line x1="58" y1="175" x2="192" y2="175" stroke={BLACK} stroke-width="2" />
    </g>
    <rect x="58" y="44" width="134" height="262" rx="6" fill="none" stroke={color} stroke-width="3" />
  {:else}
    {#each pips as [x, y], i (i)}
      <path d={SUIT_PATH[suit]} transform={pip(x, y, 40, y > C)} fill={color} />
    {/each}
  {/if}
</svg>

<style>
  svg {
    display: block;
    width: 100%;
    height: 100%;
  }
  text {
    user-select: none;
    font-variant-numeric: lining-nums;
  }
</style>
