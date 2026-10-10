// Plays recorded sounds for table events. Files live in web/public/sounds/ and are named after
// the sound, e.g. "raise.mp3" or "check.wav". Several takes ("chips_1.mp3", "chips_2.mp3") are
// picked at random. Missing files are simply skipped; see web/public/sounds/README.md for the list.
import { settings, server } from "./settings.svelte.js";

const base = (file) => file.replace(/\.[^.]+$/, "").replace(/_\d+$/, "");

function files(name) {
  return server.sounds.filter((f) => base(f) === name);
}

export function hasSound(name) {
  return files(name).length > 0;
}

// play the first of the given sounds that has a recording
export function play(...names) {
  if (!settings.sound) return;
  for (const name of names) {
    const options = files(name);
    if (!options.length) continue;
    const audio = new Audio(`/sounds/${options[Math.floor(Math.random() * options.length)]}`);
    audio.volume = settings.volume;
    audio.play().catch(() => {});
    return;
  }
}

export function soundForEvent(ev) {
  switch (ev.type) {
    case "hand_start":
      play("shuffle");
      setTimeout(() => play("deal"), 450);
      break;
    case "action":
      if (ev.action === "fold") play("fold");
      else if (ev.action === "check") play("check");
      else if (ev.all_in) play("allin", ev.action === "raise" ? "raise" : "call", "chips");
      else if (ev.action === "call") play("call", "chips");
      else play("raise", "chips");
      break;
    case "street":
      play(ev.street, "card");
      break;
    case "showdown":
      play("showdown");
      break;
    case "win":
      play("win", "chips");
      break;
    case "player_status":
      if (ev.status === "timeout") play("timeout");
      if (ev.status === "disconnected") play("disconnected");
      break;
    case "eliminated":
      play("eliminated");
      break;
    case "tournament_end":
      play("tournament_win");
      break;
    case "table_status":
      if (ev.status === "running") play("tournament_start");
      break;
  }
}
