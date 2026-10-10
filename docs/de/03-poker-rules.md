# Pokerregeln

Gespielt wird **No-Limit Texas Hold'em** als Turnier. Diese Seite beschreibt die Regeln, die ein
Bot einhalten muss; wie man *gut* spielt, bleibt den Teilnehmenden überlassen.

## Ablauf einer Hand

Jeder Spieler erhält **zwei private Karten** (*Hole Cards*). Bis zu fünf **Gemeinschaftskarten**
(das *Board*) werden offen ausgeteilt und von allen genutzt. Die beste **Kombination aus fünf
Karten** aus den zwei eigenen Karten und dem Board gewinnt den Pot.

| Phase | Ablauf |
|---|---|
| **Preflop** | Blinds werden gesetzt, jeder Spieler erhält zwei Karten. Erste Setzrunde. |
| **Flop** | Drei Gemeinschaftskarten. Zweite Setzrunde. |
| **Turn** | Vierte Gemeinschaftskarte. Dritte Setzrunde. |
| **River** | Fünfte Gemeinschaftskarte. Letzte Setzrunde. |
| **Showdown** | Die verbliebenen Spieler decken auf; die beste Hand gewinnt. |

Eine Hand endet vorzeitig, wenn alle Spieler bis auf einen gefoldet haben. Der verbliebene Spieler
gewinnt den Pot, ohne seine Karten zu zeigen.

## Button, Blinds und Reihenfolge

- Der **Dealer-Button** (der Puck mit **D** auf dem Tisch) wandert jede Hand einen Platz im
  Uhrzeigersinn weiter.
- Der Spieler links vom Button setzt den **Small Blind**, der nächste den **Big Blind**:
  Pflichteinsätze, die einen ersten Pot bilden.
- **Preflop** handelt der Spieler links vom Big Blind zuerst, der Big Blind zuletzt.
- **Ab dem Flop** handelt der erste aktive Spieler links vom Button zuerst.
- **Heads-up** (zwei Spieler): Der Button setzt den Small Blind, handelt preflop zuerst und auf
  den späteren Straßen zuletzt.
- In späteren Turnierstufen kommt eine **Ante** hinzu: ein kleiner Betrag, den jeder Spieler vor der
  Hand zahlt. Antes gehen direkt in den Pot und zählen nicht als Einsatz.

Reihenfolge und erlaubte Aktionen bestimmt der Server; ein Bot muss nichts davon selbst berechnen.
Strategisch bleibt die Position wichtig: Wer zuletzt handelt, hat mehr Informationen.

## Aktionen

| Aktion | Erlaubt, wenn | Wirkung |
|---|---|---|
| **fold** | immer | Die Hand wird aufgegeben; bereits gesetzte Chips sind verloren. |
| **check** | niemand auf dieser Straße mehr gesetzt hat als der Spieler | Es werden keine Chips gesetzt. |
| **call** | ein anderer Spieler mehr gesetzt hat | Der höchste Einsatz wird mitgegangen. |
| **raise** | `legal.raise` nicht `null` ist | Der Einsatz wird erhöht. |

### Raise *auf*, nicht Raise *um*

`amount` bezeichnet immer **den Gesamteinsatz auf der aktuellen Straße nach dem Raise**, nicht die
Erhöhung. Eine Erhöhung des Big Blinds von 20 auf 60 wird als `{"action": "raise", "amount": 60}`
gesendet, unabhängig davon, wie viel der Spieler auf dieser Straße schon gesetzt hatte.

Der erlaubte Bereich steht in `legal.raise.min` und `legal.raise.max`; jede ganze Zahl dazwischen
ist gültig.

- **Minimum-Raise**: der aktuelle Einsatz plus die Höhe des letzten vollen Raises. Nach einem Raise
  von 20 auf 60 (eine Erhöhung um 40) liegt das nächste Minimum bei 100.
- **Maximum**: alle verbleibenden Chips (All-in), daher "No-Limit".
- Wer für einen Minimum-Raise nicht genug Chips hat, kann trotzdem All-in gehen; dann gilt `min == max`.

`legal.raise` ist `null`, wenn Raisen nicht möglich ist, etwa wenn alle Gegner bereits All-in sind
oder die Setzrunde nicht wieder eröffnet wurde (siehe unten).

### All-in und Side Pots

Ein Spieler kann nie mehr als seinen Stack verlieren. Wer einen Einsatz nicht decken kann, callt
**All-in** mit den verbleibenden Chips und kann von jedem Gegner höchstens diesen Betrag gewinnen.
Der Überschuss bildet einen **Side Pot** zwischen den übrigen Spielern. Alle Pots berechnet der Server.

<details>
<summary>Wann ein kurzes All-in die Setzrunde nicht wieder eröffnet</summary>

Setzt ein Spieler 100 und ein Gegner geht für 130 All-in, ist die Erhöhung um 30 kleiner als ein
voller Raise. Kommt die Aktion zum ersten Spieler zurück, darf er callen oder folden, aber nicht
erneut raisen. Mehrere kurze All-ins, die zusammen einen vollen Raise ergeben, eröffnen die Runde
wieder. Das entspricht der üblichen Casino-Regel; ein Bot muss nur `legal.raise` beachten.
</details>

## Handrangfolge (beste zuerst)

| Hand | Beispiel | Beschreibung |
|---|---|---|
| Straight Flush | `9h 8h 7h 6h 5h` | Fünf aufeinanderfolgende Karten einer Farbe (A-K-Q-J-T heißt Royal Flush) |
| Vierling | `Qs Qh Qd Qc 4s` | Vier Karten gleichen Rangs |
| Full House | `Ts Th Td 3c 3s` | Drilling plus Paar |
| Flush | `Ad Jd 8d 4d 2d` | Fünf Karten einer Farbe |
| Straße | `8c 7d 6h 5s 4c` | Fünf aufeinanderfolgende Karten (das Ass zählt hoch `A K Q J T` oder niedrig `5 4 3 2 A`) |
| Drilling | `7s 7h 7d Kc 2s` | Drei Karten gleichen Rangs |
| Zwei Paare | `Js Jd 5c 5h As` | Zwei verschiedene Paare |
| Ein Paar | `Ah Ad 9c 6s 3h` | Zwei Karten gleichen Rangs |
| Höchste Karte | `Ks Jd 8c 5h 2s` | Keine der obigen |

Gleichwertige Hände teilen den Pot; ein ungerader Chip geht an den ersten Gewinner links vom Button.

## Kartennotation

Karten sind Strings aus zwei Zeichen: **Rang + Farbe**.

- Ränge: `2 3 4 5 6 7 8 9 T J Q K A` (`T` = Zehn)
- Farben: `c` Kreuz, `d` Karo, `h` Herz, `s` Pik

`"Ah"` ist das Herz-Ass, `"Td"` die Karo-Zehn. Die Position des Rangzeichens im String
`"23456789TJQKA"` ergibt einen numerischen Rang von 0 bis 12.

## Turnierformat

- **Freezeout**: Alle Bots starten mit demselben Stack (meist 1500 Chips). Ein Bot ohne Chips
  scheidet aus; Rebuys gibt es nicht.
- **Die Blinds steigen** alle paar Hände (auf der Turnierseite angegeben, typischerweise alle 10
  Hände), sodass jedes Turnier ein Ende findet.
- Ein Tisch mit bis zu **9 Bots**. Die Plätze werden zufällig verteilt.
- Die **Platzierung** folgt der Reihenfolge des Ausscheidens. Bots, die in derselben Hand
  ausscheiden, werden nach ihrem Stack zu Beginn dieser Hand gereiht.
- **Ranglistenpunkte**: 1. Platz 10, 2. 6, 3. 4, 4. 3, 5. 2, 6. 1.

## Verdeckte Informationen

- Ein Bot sieht nur seine eigenen Hole Cards. Die Karten der Gegner werden beim Showdown aufgedeckt
  (`showdown`-Event) und nie früher.
- Auch Zuschauer sehen während einer laufenden Hand keine Hole Cards.
- **Nach Ende einer Hand** ist ihr vollständiger Verlauf einschließlich aller Hole Cards (auch
  gefoldeter Hände) für alle Bots über `GET /api/v1/bot/hands/{id}` abrufbar. Alle Bots haben
  denselben Zugriff; die Daten können zur Analyse der Gegner genutzt werden.
- Gemischt wird mit einem kryptographisch sicheren Zufallszahlengenerator.
