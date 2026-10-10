# Pokerregeln

Wir spielen **No-Limit Texas Hold'em** als Turnier. Wenn du noch nie gespielt hast, reicht diese Seite,
um einen Bot zu schreiben, der korrekt spielt. *Gut* spielen ist der spaßige Teil, und der liegt bei dir.

## Eine Hand, Schritt für Schritt

Jeder Spieler bekommt **2 private Karten** (*Hole Cards*). In der Mitte werden bis zu 5
**Gemeinschaftskarten** (das *Board*) offen ausgeteilt, die alle benutzen dürfen. Die beste
**Kombination aus 5 Karten** aus deinen 2 + den 5 gemeinsamen gewinnt den Pot.

| Phase | Was passiert |
|---|---|
| **Preflop** | Blinds werden gesetzt, alle bekommen 2 Karten. Erste Setzrunde. |
| **Flop** | 3 Gemeinschaftskarten. Zweite Setzrunde. |
| **Turn** | 4. Gemeinschaftskarte. Dritte Setzrunde. |
| **River** | 5. Gemeinschaftskarte. Letzte Setzrunde. |
| **Showdown** | Die noch beteiligten Spieler zeigen ihre Karten, die beste Hand gewinnt. |

Eine Hand endet früher, wenn alle außer einem Spieler folden. Der gewinnt den Pot, ohne seine Karten
zu zeigen.

## Button, Blinds und Reihenfolge

- Der **Button** (Dealer, markiert mit **D**) wandert jede Hand einen Platz im Uhrzeigersinn weiter.
- Der Spieler links vom Button setzt den **Small Blind**, der nächste den **Big Blind**. Das sind
  Pflichteinsätze, damit es überhaupt um etwas geht.
- **Preflop** handelt der Spieler links vom Big Blind zuerst, der Big Blind als Letzter.
- **Auf Flop, Turn und River** handelt der erste aktive Spieler links vom Button zuerst.
- **Heads-up** (nur noch 2 Spieler): Der Button setzt den Small Blind und handelt preflop *zuerst*,
  nach dem Flop aber *zuletzt*.
- Später im Turnier gibt es zusätzlich eine **Ante**: einen kleinen Betrag, den *alle* vor der Hand
  zahlen. Antes gehen direkt in den Pot und zählen nicht als Einsatz.

Nichts davon musst du selbst berechnen. Der Server sagt dir, wer dran ist und was du darfst. Für die
Strategie ist es trotzdem nützlich: Als Letzter zu handeln ("in Position") ist ein großer Vorteil.

## Deine Möglichkeiten

| Aktion | Wann | Wirkung |
|---|---|---|
| **fold** | immer | Hand aufgeben. Deine Chips im Pot sind weg. |
| **check** | wenn niemand auf dieser Straße mehr gesetzt hat als du | Nichts tun, weitergeben. |
| **call** | wenn jemand mehr gesetzt hat als du | Den höchsten Einsatz mitgehen. |
| **raise** | wenn erlaubt | Den Einsatz erhöhen. |

### "Raise AUF", nicht "Raise UM"

Bei poker-pi ist `amount` immer **der Gesamtbetrag, den dein Einsatz auf dieser Straße haben soll**,
nicht die Erhöhung. Beispiel: Der Big Blind ist 20 und du willst auf 60 erhöhen. Du schickst
`{"action": "raise", "amount": 60}`, obwohl du nur 60 minus deinen bisherigen Einsatz dazulegst.

Der Server nennt dir den erlaubten Bereich in `legal.raise.min` und `legal.raise.max`. Jede ganze Zahl
dazwischen ist okay.

- **Minimum-Raise**: aktueller Einsatz plus die Höhe des letzten Raises. Hat jemand von 20 auf 60
  erhöht (ein Raise um 40), ist das nächste Minimum 100.
- **Maximum**: alle deine Chips (*All-in*). Das ist der "No-Limit"-Teil.
- Reichen deine Chips nicht für einen Minimum-Raise, darfst du trotzdem All-in gehen: dann ist `min == max`.

> Wenn `legal.raise` `null` ist, darfst du gerade nicht raisen. Das passiert, wenn alle anderen All-in
> sind oder wenn die Setzrunde nicht wieder eröffnet wurde (siehe unten).

### All-in und Side Pots

Du kannst nie mehr verlieren, als du hast. Kannst du einen Call nicht bezahlen, callst du **All-in**
mit dem, was übrig ist, und kannst von jedem Gegner nur so viel gewinnen, wie du selbst eingesetzt
hast. Der Rest bildet einen **Side Pot** zwischen den anderen Spielern. Das alles rechnet der Server.
Dein Bot muss nur wissen, dass er All-in sein kann, während andere noch Chips vor sich haben.

<details>
<summary>Für Fortgeschrittene: wann ein kurzes All-in die Setzrunde nicht wieder eröffnet</summary>

Angenommen, du setzt 100 und jemand geht für 130 All-in. Das ist ein Raise um nur 30, weniger als ein
"voller" Raise. Wenn du wieder dran bist, darfst du **callen oder folden, aber nicht erneut raisen**.
In echten Casinos gilt dieselbe Regel. Mehrere kurze All-ins, die zusammen einen vollen Raise ergeben,
eröffnen die Runde aber wieder. Merken musst du dir das nicht: Schau einfach auf `legal.raise`.
</details>

## Handrangfolge (beste zuerst)

| Hand | Beispiel | Beschreibung |
|---|---|---|
| Straight Flush | `9h 8h 7h 6h 5h` | Fünf in Folge, gleiche Farbe (der beste, A-K-Q-J-T, heißt Royal Flush) |
| Vierling (Four of a Kind) | `Qs Qh Qd Qc 4s` | Vier Karten gleichen Rangs |
| Full House | `Ts Th Td 3c 3s` | Drilling + Paar |
| Flush | `Ad Jd 8d 4d 2d` | Fünf Karten gleicher Farbe |
| Straße (Straight) | `8c 7d 6h 5s 4c` | Fünf in Folge (das Ass kann hoch `A K Q J T` oder niedrig `5 4 3 2 A` sein) |
| Drilling (Three of a Kind) | `7s 7h 7d Kc 2s` | Drei Karten gleichen Rangs |
| Zwei Paare (Two Pair) | `Js Jd 5c 5h As` | Zwei verschiedene Paare |
| Ein Paar (One Pair) | `Ah Ad 9c 6s 3h` | Zwei Karten gleichen Rangs |
| Höchste Karte (High Card) | `Ks Jd 8c 5h 2s` | Nichts von alledem |

Gleich gute Hände teilen den Pot. Übrige ungerade Chips bekommt der erste Gewinner links vom Button.

## Kartennotation

Karten sind Strings aus 2 Zeichen: **Rang + Farbe**.

- Ränge: `2 3 4 5 6 7 8 9 T J Q K A` (`T` = Zehn)
- Farben: `c` Kreuz ♣ (clubs), `d` Karo ♦ (diamonds), `h` Herz ♥ (hearts), `s` Pik ♠ (spades)

`"Ah"` ist also das Herz-Ass und `"Td"` die Karo-Zehn. Praktischer Trick: `"23456789TJQKA".index(card[0])`
liefert den Rang als Zahl von 0 bis 12.

## Turnierformat

- **Freezeout**: Alle starten mit demselben Stack (meist 1500 Chips). Wer alle Chips verliert, ist
  raus, ohne Rebuys.
- **Die Blinds steigen** alle paar Hände (steht auf der Turnierseite, meist alle 10 Hände), damit das
  Turnier sicher endet. Spät im Turnier sind die Blinds groß, und du kannst nicht ewig auf perfekte
  Hände warten.
- Ein Tisch mit bis zu **9 Bots**. Die Plätze werden ausgelost.
- **Platzierung** nach Ausscheide-Reihenfolge: Wer als Letzter übrig ist, gewinnt. Scheiden zwei Bots
  in derselben Hand aus, landet der vorne, der die Hand mit mehr Chips begonnen hat.
- **Punkte** für die Rangliste: 1. Platz 10 · 2. 6 · 3. 4 · 4. 3 · 5. 2 · 6. 1.

## Verdeckte Informationen und Fairness

- Dein Bot sieht nur **seine eigenen** Hole Cards. Die Karten der Gegner werden beim Showdown
  aufgedeckt (im `showdown`-Event) und nie vorher.
- Auch Zuschauer auf der Webseite sehen keine Hole Cards, solange eine Hand läuft.
- **Nach Ende einer Hand** ist ihr kompletter Verlauf inklusive aller Karten (auch die gefoldeter
  Hände) für alle über `GET /api/v1/bot/hands/{id}` abrufbar. Alle Bots haben denselben Zugriff, und
  du kannst damit lernen, wie deine Gegner spielen (siehe [Strategie-Tipps](#/docs/strategy)).
- Gemischt wird mit einem kryptographisch sicheren Zufallsgenerator.
