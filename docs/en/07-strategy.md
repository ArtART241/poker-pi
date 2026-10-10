# Strategy tips

The starter bot plays like a beginner on purpose. Here are ideas to make yours better, roughly ordered
from "an afternoon" to "a semester project". Try them at a practice table first.

## Level 1: Don't play every hand

Most two-card hands lose money. A simple preflop filter is the biggest single improvement.
A well-known rule of thumb is the **Chen formula**, which gives each starting hand a score:

1. Highest card: A = 10, K = 8, Q = 7, J = 6, 10 to 2 = half their value (T = 5, 9 = 4.5, ...).
2. Pair: double the score (minimum 5).
3. Suited (same suit): +2.
4. Gap between the cards: 1 gap −1, 2 gaps −2, 3 gaps −4, 4+ gaps −5.
5. Both cards below a queen and connected or with one gap: +1.

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

Roughly: **≥ 10** raise, **7 to 9** call a small raise, **below 7** fold unless you can check.

## Level 2: Position

The later you act, the more you know. On the button you see what everyone else did before you decide.
Play **more hands in late position** (button, the seat right of it) and **fewer early** (just after
the big blind). See the [API reference](#/docs/api-reference) for how to compute your position.

## Level 3: Pot odds

Should you call? Compare what you pay with what you can win:

```
pot odds = to_call / (pot + to_call)
```

Example: pot 100 (including the bets), to call 20 → 20 / 120 ≈ 17%. If your hand wins more than 17% of
the time, calling is profitable in the long run.

A common case is a **draw**. Four cards to a flush on the flop leave 9 "outs" (cards that complete
it). The **rule of 2 and 4**: on the flop, outs × 4 ≈ your chance in % to hit by the river; on the
turn, outs × 2. With 9 outs, that's about 36% on the flop and 18% on the turn.

## Level 4: Monte Carlo equity

The most universal tool: **simulate**. Deal the unknown cards randomly many times and count how often
you win. That gives you your *equity*, your share of the pot.

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
        best = min(others)                  # lower = better in treys
        if mine < best: wins += 1
        elif mine == best: wins += 0.5
    return wins / iterations
```

Then: **call** if `equity > pot odds`, **raise** if the equity is clearly higher. 2000 iterations take
well under a second in Python. You have 15 seconds.

In other languages, write a 7-card evaluator (or port one). A classic exercise: compute the hand
rank from rank and suit counts. Or look up "Cactus Kev" / "two plus two evaluator".

<details>
<summary>Making the simulation smarter: hand ranges</summary>

Random opponent cards are too pessimistic preflop and too optimistic later. Someone who raised
three times on the river rarely holds 7-2. Better: sample opponent hands only from a **range** of
plausible hands, e.g. only the top 20% by Chen score if they raised preflop. That's the step from
"computes odds" to "reads players".
</details>

## Level 5: Bet sizing

- **Value bet** with strong hands: about half to three quarters of the pot. Weaker hands will still call.
- **Don't min-raise everything.** It gives opponents perfect pot odds.
- **Bluff** sometimes. If you only bet with good hands, smart bots will notice. A bluff works best
  when the board looks scary (e.g. 3 cards of one suit) and against few opponents.
- Raise **to** a total: `amount = current_bet + 0.75 * pot` is a reasonable raise, clipped to
  `[legal.raise.min, legal.raise.max]`.

## Level 6: Tournament thinking

- **Blinds keep rising.** Your stack measured in big blinds (`stack / blinds.big`) matters more than
  the absolute number. Below about **10 big blinds**, the best strategy is almost always
  **push or fold**: go all-in or fold, nothing in between.
- **Survival has value.** Busting early earns 0 points, while 3rd place earns 4. Near the end, avoid
  risky all-ins with marginal hands when shorter stacks are about to bust anyway.
- **Heads-up** (two players left): play many more hands, since you're in the blinds every hand.

## Level 7: Learn from your opponents

After every hand, the full history including **everyone's cards** is public:

```
GET /api/v1/bot/hands?tournament_id=7          → list of hands
GET /api/v1/bot/hands/{id}                      → events incl. all hole cards
```

Collect statistics per opponent (keyed by `name`), for example:

- **VPIP**: how often do they put money in preflop voluntarily? (Over 50% = loose, under 20% = tight.)
- **Aggression**: how often do they raise compared to calling?
- **Bluff rate**: what did they hold when they bet big on the river?

Then adapt: bluff tight players more, value-bet loose ones harder, and call aggressive bluffers down.

> Remember that your opponents can do the same with your hands. A bit of randomness in your
> decisions makes you harder to read.

## Testing and debugging

- **Practice, practice:** `POST /practice` with `"speed": "fast"` plays hundreds of hands in minutes.
  Mix the opponent types to see how your bot handles each style.
- **Log your decisions** with the reason ("equity 0.62 > pot odds 0.25 → call"). When your bot does
  something stupid, the log tells you why.
- **Watch the replays** on the website (each hand has a replay button). The raw events are shown at
  the bottom, exactly as your bot sees them.
- **Write unit tests for `decide`:** save a few real states from `GET /turn` as JSON files and check
  that your bot answers sensibly.
- **Version your bot with git** so you can go back when a "great idea" makes it worse.
