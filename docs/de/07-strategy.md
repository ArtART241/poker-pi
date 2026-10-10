# Strategie-Tipps

Der Starter-Bot spielt absichtlich wie ein Anfänger. Hier sind Ideen, deinen besser zu machen, grob
sortiert von "ein Nachmittag" bis "Semesterprojekt". Probier sie zuerst an einem Übungstisch aus.

## Stufe 1: Nicht jede Hand spielen

Die meisten Starthände verlieren Geld. Ein einfacher Preflop-Filter ist die größte einzelne Verbesserung.
Eine bekannte Faustregel ist die **Chen-Formel**, die jeder Starthand eine Punktzahl gibt:

1. Höchste Karte: A = 10, K = 8, Q = 7, J = 6, 10 bis 2 = halber Wert (T = 5, 9 = 4,5, ...).
2. Paar: Punktzahl verdoppeln (mindestens 5).
3. Suited (gleiche Farbe): +2.
4. Lücke zwischen den Karten: 1 Lücke −1, 2 Lücken −2, 3 Lücken −4, 4+ Lücken −5.
5. Beide Karten unter Dame und verbunden oder mit einer Lücke: +1.

```python
def chen(cards):
    order = "23456789TJQKA"
    value = {"A": 10, "K": 8, "Q": 7, "J": 6}
    r = sorted((c[0] for c in cards), key=order.index, reverse=True)
    score = value.get(r[0], (order.index(r[0]) + 2) / 2)
    if r[0] == r[1]:
        return max(score * 2, 5)
    if cards[0][1] == cards[1][1]:
        score += 2
    gap = order.index(r[0]) - order.index(r[1]) - 1
    score -= [0, 1, 2, 4][gap] if gap < 4 else 5
    if gap <= 1 and order.index(r[0]) < order.index("Q"):
        score += 1
    return score
```

Grob: **≥ 10** raisen, **7 bis 9** einen kleinen Raise callen, **unter 7** folden, außer du kannst checken.

## Stufe 2: Position

Je später du handelst, desto mehr weißt du. Am Button siehst du, was alle anderen gemacht haben, bevor
du dich entscheidest. Spiel **mehr Hände in später Position** (Button, der Platz rechts davon) und
**weniger früh** (direkt nach dem Big Blind). In der [API-Referenz](#/docs/api-reference) steht, wie du
deine Position berechnest.

## Stufe 3: Pot Odds

Sollst du callen? Vergleiche, was du zahlst, mit dem, was du gewinnen kannst:

```
Pot Odds = to_call / (pot + to_call)
```

Beispiel: Pot 100 (inklusive der Einsätze), zu callen 20 → 20 / 120 ≈ 17 %. Gewinnt deine Hand öfter
als in 17 % der Fälle, ist Callen langfristig profitabel.

Ein häufiger Fall ist ein **Draw**. Vier Karten zum Flush auf dem Flop lassen 9 "Outs" übrig (Karten,
die ihn vervollständigen). Die **2-und-4-Regel**: auf dem Flop Outs × 4 ≈ deine Chance in %, bis zum
River zu treffen; auf dem Turn Outs × 2. Mit 9 Outs sind das etwa 36 % auf dem Flop und 18 % auf dem Turn.

## Stufe 4: Monte-Carlo-Equity

Das universellste Werkzeug: **simulieren**. Teile die unbekannten Karten viele Male zufällig aus und
zähle, wie oft du gewinnst. Das ergibt deine *Equity*, deinen Anteil am Pot.

```python
import random
from treys import Card, Evaluator   # pip install treys

evaluator = Evaluator()
DECK = [r + s for r in "23456789TJQKA" for s in "cdhs"]

def equity(hole, board, opponents, iterations=2000):
    known = set(hole) | set(board)
    deck = [c for c in DECK if c not in known]
    h = [Card.new(c) for c in hole]
    wins = 0.0
    for _ in range(iterations):
        random.shuffle(deck)
        need = 5 - len(board)
        b = [Card.new(c) for c in board + deck[:need]]
        mine = evaluator.evaluate(b, h)
        others = [evaluator.evaluate(b, [Card.new(deck[need + 2*i]), Card.new(deck[need + 2*i + 1])])
                  for i in range(opponents)]
        best = min(others)                  # bei treys: kleiner = besser
        if mine < best: wins += 1
        elif mine == best: wins += 0.5
    return wins / iterations
```

Dann: **callen**, wenn `equity > Pot Odds`, **raisen**, wenn die Equity deutlich höher ist. 2000
Iterationen dauern in Python deutlich unter einer Sekunde. Du hast 15 Sekunden.

In anderen Sprachen schreibst du einen 7-Karten-Evaluator (oder portierst einen). Eine klassische
Übung: den Handrang aus den Zählungen von Rängen und Farben berechnen. Oder such nach "Cactus Kev" /
"two plus two evaluator".

<details>
<summary>Die Simulation schlauer machen: Hand-Ranges</summary>

Zufällige Gegnerkarten sind preflop zu pessimistisch und später zu optimistisch. Wer auf dem River
dreimal geraist hat, hält selten 7-2. Besser: Gegnerhände nur aus einer **Range** plausibler Hände
ziehen, z. B. nur aus den besten 20 % nach Chen-Punkten, wenn er preflop geraist hat. Das ist der
Schritt von "rechnet Wahrscheinlichkeiten" zu "liest Spieler".
</details>

## Stufe 5: Einsatzgröße

- **Value Bet** mit starken Händen: etwa die Hälfte bis drei Viertel des Pots. Schwächere Hände callen trotzdem noch.
- **Nicht alles min-raisen.** Damit gibst du Gegnern perfekte Pot Odds.
- **Bluff** ab und zu. Wenn du nur mit guten Händen setzt, merken schlaue Bots das. Ein Bluff
  funktioniert am besten, wenn das Board gefährlich aussieht (z. B. 3 Karten einer Farbe) und gegen wenige Gegner.
- Raise **auf** einen Gesamtbetrag: `amount = current_bet + 0.75 * pot` ist ein vernünftiger Raise,
  begrenzt auf `[legal.raise.min, legal.raise.max]`.

## Stufe 6: Turnier-Denken

- **Die Blinds steigen ständig.** Dein Stack in Big Blinds (`stack / blinds.big`) zählt mehr als die
  absolute Zahl. Unter etwa **10 Big Blinds** ist die beste Strategie fast immer **Push or Fold**:
  All-in oder folden, nichts dazwischen.
- **Überleben hat einen Wert.** Wer früh ausscheidet, bekommt 0 Punkte, der 3. Platz bekommt 4. Gegen
  Ende lieber keine riskanten All-ins mit mittelmäßigen Händen, wenn kürzere Stacks ohnehin bald ausscheiden.
- **Heads-up** (zwei Spieler übrig): viel mehr Hände spielen, du bist ja jede Hand in den Blinds.

## Stufe 7: Von den Gegnern lernen

Nach jeder Hand ist der komplette Verlauf inklusive **aller Karten** öffentlich:

```
GET /api/v1/bot/hands?tournament_id=7          → Liste der Hände
GET /api/v1/bot/hands/{id}                      → Events inkl. aller Hole Cards
```

Sammle Statistiken pro Gegner (nach `name`), zum Beispiel:

- **VPIP**: Wie oft legt er preflop freiwillig Geld rein? (Über 50 % = loose, unter 20 % = tight.)
- **Aggression**: Wie oft raist er im Vergleich zum Callen?
- **Bluff-Rate**: Was hatte er, als er auf dem River groß gesetzt hat?

Dann anpassen: tight Spieler öfter bluffen, gegen loose Spieler härter auf Value setzen, aggressive
Bluffer runtercallen.

> Denk dran, dass deine Gegner dasselbe mit deinen Händen machen können. Ein bisschen Zufall in deinen
> Entscheidungen macht dich schwerer lesbar.

## Testen und Debuggen

- **Üben, üben:** `POST /practice` mit `"speed": "fast"` spielt hunderte Hände in wenigen Minuten.
  Misch die Gegnertypen, um zu sehen, wie dein Bot mit jedem Stil umgeht.
- **Logge deine Entscheidungen** mit Begründung ("Equity 0,62 > Pot Odds 0,25 → call"). Wenn dein Bot
  etwas Dummes macht, sagt dir das Log, warum.
- **Schau die Replays** auf der Webseite an (jede Hand hat einen Replay-Button). Unten werden die rohen
  Events angezeigt, genau so, wie dein Bot sie sieht.
- **Schreib Unit-Tests für `decide`:** Speicher ein paar echte Zustände aus `GET /turn` als JSON-Dateien
  und prüf, dass dein Bot vernünftig antwortet.
- **Versionier deinen Bot mit git**, damit du zurück kannst, wenn eine "geniale Idee" ihn schlechter macht.
