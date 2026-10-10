# Strategie-Hinweise

Eine Sammlung bekannter Ansätze, um einen Bot zu verbessern, grob nach Aufwand sortiert. Alle lassen
sich zunächst an Übungstischen erproben.

## Auswahl der Starthände

Die meisten Starthände verlieren auf Dauer Chips; ein Preflop-Filter ist daher meist die größte
einzelne Verbesserung. Eine verbreitete Faustregel ist die **Chen-Formel**, die eine Starthand bewertet:

1. Höchste Karte: A = 10, K = 8, Q = 7, J = 6, 10 bis 2 = halber Nennwert (T = 5, 9 = 4,5, ...).
2. Paar: Wert verdoppeln, mindestens 5.
3. Suited (gleiche Farbe): +2.
4. Lücke zwischen den Rängen: 1 Lücke −1, 2 Lücken −2, 3 Lücken −4, 4 oder mehr −5.
5. Keine oder eine Lücke und beide Karten unter Dame: +1.

```
funktion chen(karte1, karte2):
    hoch, niedrig = Ränge absteigend sortiert
    wert = wert_von(hoch)                      A=10, K=8, Q=7, J=6, sonst Nennwert / 2
    falls hoch == niedrig: return max(2 * wert, 5)
    falls gleiche Farbe: wert += 2
    luecke = index(hoch) - index(niedrig) - 1
    wert -= [0, 1, 2, 4][luecke] falls luecke < 4, sonst 5
    falls luecke <= 1 und hoch < Q: wert += 1
    return wert
```

Als grobe Orientierung: **ab 10** raisen, **7 bis 9** einen kleinen Raise callen, **unter 7**
folden, sofern Checken nichts kostet.

## Position

Wer später handelt, verfügt über mehr Informationen. Am Button sind die Entscheidungen aller anderen
Spieler bereits bekannt. Mehr Hände in später Position (Button und der Platz rechts davon) und
weniger in früher Position (direkt nach dem Big Blind) zu spielen, ist eine übliche Anpassung. Die
[API-Referenz](#/docs/api-reference) zeigt, wie sich die Position berechnen lässt.

## Pot Odds

Ob ein Call profitabel ist, lässt sich durch den Vergleich seines Preises mit dem Pot abschätzen:

```
Pot Odds = to_call / (pot + to_call)
```

Bei einem Pot von 100 (inklusive aktueller Einsätze) und 20 zu callen ergeben sich 20 / 120 ≈ 17 %.
Eine Hand, die häufiger gewinnt, macht den Call auf Dauer profitabel.

Bei **Draws** heißen die Karten, die die Hand vervollständigen, *Outs*. Vier Karten zum Flush auf dem
Flop lassen 9 Outs. Die **2-und-4-Regel** schätzt die Trefferwahrscheinlichkeit: Outs × 4 auf dem
Flop (zwei Karten folgen), Outs × 2 auf dem Turn. Neun Outs ergeben etwa 36 % auf dem Flop und
18 % auf dem Turn.

## Monte-Carlo-Equity

Das allgemeinste Werkzeug ist die Simulation: Die unbekannten Karten werden viele Male zufällig
verteilt, und es wird gezählt, wie oft die eigene Hand gewinnt. Das Ergebnis ist die *Equity*, der
erwartete Anteil am Pot.

```
funktion equity(hole, board, gegner, durchlaeufe):
    deck = alle 52 Karten ohne hole und board
    siege = 0
    wiederhole durchlaeufe mal:
        deck mischen
        volles_board = board + erste (5 - len(board)) Karten des Decks
        gegnerhaende = nächste 2 * gegner Karten, je zwei pro Gegner
        eigene = rang(hole + volles_board)
        beste_andere = bester Rang aller Gegnerhände + volles_board
        falls eigene schlägt beste_andere: siege += 1
        falls eigene gleich beste_andere:  siege += 0.5
    return siege / durchlaeufe
```

Eine übliche Regel: **callen**, wenn die Equity die Pot Odds übersteigt, **raisen**, wenn sie
deutlich höher liegt. Einige tausend Durchläufe passen in den meisten Sprachen bequem in das Limit
von 15 Sekunden.

Der nötige Baustein ist ein **Hand-Evaluator**: eine Funktion, die die beste Fünf-Karten-Hand aus
sieben Karten bewertet. Einen solchen zu schreiben ist eine gute Übung (das Zählen von Rängen und
Farben deckt die meisten Handtypen ab); fertige Evaluatoren gibt es für die meisten Sprachen, oft
nach dem "Cactus Kev"- oder "two plus two"-Verfahren.

<details>
<summary>Verfeinerung: Hand-Ranges</summary>

Gleichverteilte Gegnerhände sind preflop zu pessimistisch und später zu optimistisch. Wer bis zum
River dreimal geraist hat, hält selten 7-2. Gegnerhände aus einer **Range** plausibler Hände zu
ziehen (etwa den besten 20 % nach Chen-Wert nach einem Preflop-Raise), liefert deutlich bessere
Schätzungen.
</details>

## Einsatzhöhe

- **Value Bets** mit starken Händen in Höhe von etwa der Hälfte bis drei Vierteln des Pots werden von
  schwächeren Händen weiterhin gecallt.
- **Minimum-Raises** geben Gegnern sehr günstige Pot Odds und schützen wenig.
- **Bluffs** verhindern, dass ein Bot berechenbar wird. Sie wirken am besten auf bedrohlichen Boards
  (z. B. drei Karten einer Farbe) und gegen wenige Gegner.
- Da `amount` der Gesamteinsatz ist, entspricht ein Raise um drei Viertel des Pots
  `current_bet + 0,75 × pot`, begrenzt auf `[legal.raise.min, legal.raise.max]`.

## Turnierüberlegungen

- **Steigende Blinds** machen die Stackgröße in Big Blinds (`stack / blinds.big`) wichtiger als die
  absolute Zahl. Unterhalb von etwa **10 Big Blinds** ist eine Push-or-Fold-Strategie (All-in oder
  Fold) nahezu optimal.
- **Überleben hat einen Wert.** Frühes Ausscheiden bringt keine Punkte, der dritte Platz vier. Gegen
  Ende lassen sich knappe All-ins vermeiden, solange kürzere Stacks voraussichtlich zuerst ausscheiden.
- **Heads-up** erfordert eine deutlich breitere Handauswahl, da jeder Spieler in jeder Hand in den
  Blinds sitzt.

## Gegner-Modellierung

Der vollständige Verlauf jeder beendeten Hand, einschließlich aller Hole Cards, ist öffentlich:

```
GET /api/v1/bot/hands?tournament_id=7          → Liste der Hände
GET /api/v1/bot/hands/{id}                      → Events einschließlich aller Hole Cards
```

Nützliche Statistiken pro Gegner (nach `name`):

- **VPIP**: wie oft ein Spieler preflop freiwillig Chips investiert (über 50 % loose, unter 20 % tight).
- **Aggression**: Verhältnis von Raises zu Calls.
- **Showdown-Hände**: welche Hände nach großen Einsätzen gezeigt wurden.

Übliche Anpassungen sind häufigere Bluffs gegen tighte Spieler, größere Value Bets gegen loose
Spieler und weitere Calls gegen aggressive Spieler. Dieselben Daten stehen allen anderen Bots zur
Verfügung; etwas Zufall in den eigenen Entscheidungen erschwert die Modellierung.

## Testen

- Übungstische mit `"speed": "fast"` spielen hunderte Hände in wenigen Minuten. Gemischte Gegnertypen
  (`random`, `station`, `tight`) zeigen, wie eine Strategie mit verschiedenen Spielstilen umgeht.
- Jede Entscheidung mit ihrem Grund zu protokollieren (z. B. "Equity 0,62 > Pot Odds 0,25 → call")
  macht unerwartetes Verhalten leicht nachvollziehbar.
- Jede Hand auf der Webseite hat ein Replay; die darunter angezeigten Roh-Events entsprechen genau
  dem, was der Bot erhält.
- Echte Spielzustände aus `GET /turn` eignen sich gut als Testdaten für Unit-Tests von `decide`.
