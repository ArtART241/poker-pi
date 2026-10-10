# Sounds

Drop recorded files into this folder, named after the sound: `raise.mp3`, `check.wav`, ...
Any of `.mp3 .ogg .wav .m4a .webm .aac .flac` works. For variety, record several takes and
number them: `chips_1.mp3`, `chips_2.mp3`, `chips_3.mp3`. One is picked at random each time.

Missing sounds are skipped silently, so record as many or as few as you like. After adding files,
rebuild the website (`cd web && npm run build`) or restart `scripts/demo.sh`.

Viewers switch sound on in the ⚙ menu (it starts muted, because browsers only allow audio after a click).

| File name | Plays when | Idea | Fallback if missing |
|---|---|---|---|
| `shuffle` | a new hand starts | riffle shuffle of a real deck | none |
| `deal` | right after the shuffle | 1-2 cards sliding over felt | none |
| `check` | a bot checks | two knuckle knocks on a table | none |
| `fold` | a bot folds | cards tossed/slid away, or a sigh "fold" | none |
| `call` | a bot calls | a few chips set down, or a voice "call" | `chips` |
| `raise` | a bot raises | a bigger pile of chips, or a voice "raise!" | `chips` |
| `allin` | a bot goes all-in | chips shoved + voice "ALL IN!" | `raise` / `call`, then `chips` |
| `chips` | generic chip sound | chips clicking (record 3+ takes) | none |
| `flop` | flop is dealt | card flip(s), or a voice "flop" | `card` |
| `turn` | turn is dealt | card flip, or a voice "turn" | `card` |
| `river` | river is dealt | card flip, or a voice "river" | `card` |
| `card` | any community card | a single card flip | none |
| `showdown` | cards are revealed | dramatic "showdown!" or a drum hit | none |
| `win` | a pot is pushed to the winner | chips raked + a short cheer | `chips` |
| `timeout` | a bot is too slow | a clock tick or a buzzer | none |
| `disconnected` | a bot loses its connection | a short "uh-oh" | none |
| `eliminated` | a bot is knocked out | a sad trombone or a door slam | none |
| `tournament_start` | a tournament begins | "Shuffle up and deal!" | none |
| `tournament_win` | a tournament is won | applause / fanfare / "Winner winner, chicken dinner" | none |

Tips: keep each sound short (0.3 to 1.5 s, the fanfare can be longer), cut the silence at the
start, and normalize the volume so a quiet knock and a loud shove feel balanced. Bots act every
~2 seconds, so long sounds will overlap.
