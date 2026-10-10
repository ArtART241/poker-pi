// Viewer settings (stored in this browser) + defaults from the server (/api/v1/public/config).

export const DECKS = [
  { id: "drawn", label: "Drawn" },
  { id: "artwork", label: "Artwork" },
];

function load() {
  try {
    return JSON.parse(localStorage.getItem("poker-settings") || "{}");
  } catch {
    return {};
  }
}

const saved = load();

export const settings = $state({
  deck: saved.deck ?? null, // null = use the server default
  sound: saved.sound ?? false, // browsers only allow sound after a click, so it starts off
  volume: saved.volume ?? 0.7,
});

export const server = $state({ deck: "drawn", sounds: [] });

export function deck() {
  const id = settings.deck ?? server.deck;
  return DECKS.some((d) => d.id === id) ? id : "drawn";
}

$effect.root(() => {
  $effect(() => {
    const data = { deck: settings.deck, sound: settings.sound, volume: settings.volume };
    try {
      localStorage.setItem("poker-settings", JSON.stringify(data));
    } catch {}
  });
});

fetch("/api/v1/public/config")
  .then((r) => (r.ok ? r.json() : null))
  .then((cfg) => {
    if (!cfg) return;
    server.deck = cfg.card_deck;
    server.sounds = cfg.sounds ?? [];
  })
  .catch(() => {});
