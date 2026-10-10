# Strategy notes

A collection of well-known ideas for improving a bot, roughly ordered by effort. All of them can be
tried on practice tables first.

## Starting hand selection

Most two-card hands lose money in the long run, so a preflop filter is usually the single largest
improvement. A widely used rule of thumb is the **Chen formula**, which scores a starting hand:

1. Highest card: A = 10, K = 8, Q = 7, J = 6, 10 down to 2 = half the face value (T = 5, 9 = 4.5, ...).
2. Pair: double the score, minimum 5.
3. Suited (same suit): +2.
4. Gap between the ranks: 1 gap −1, 2 gaps −2, 3 gaps −4, 4 or more −5.
5. No gap or one gap and both cards below a queen: +1.

```
function chen(card1, card2):
    high, low = ranks sorted descending
    score = value(high)                        A=10, K=8, Q=7, J=6, else (rank number) / 2
    if high == low: return max(2 * score, 5)
    if same suit: score += 2
    gap = index(high) - index(low) - 1
    score -= [0, 1, 2, 4][gap] if gap < 4 else 5
    if gap <= 1 and high < Q: score += 1
    return score
```

As a rough guide: **10 or more** raise, **7 to 9** call a small raise, **below 7** fold unless
checking is free.

## Position

Players acting later have more information. On the button, every other player's decision is
known before the bot acts. Playing more hands in late position (button and the seat to its right)
and fewer in early position (directly after the big blind) is a standard adjustment. The
[API reference](#/docs/api-reference) shows how to compute the position.

## Pot odds

Whether a call is profitable can be estimated by comparing its price with the pot:

```
pot odds = to_call / (pot + to_call)
```

With a pot of 100 (including current bets) and 20 to call, the pot odds are 20 / 120 ≈ 17%.
A hand that wins more often than that makes the call profitable in the long run.

For **draws**, the cards that complete the hand are called *outs*. Four cards to a flush on the flop
leave 9 outs. The **rule of 2 and 4** approximates the chance to hit: outs × 4 on the flop (two cards
to come), outs × 2 on the turn. Nine outs give roughly 36% on the flop and 18% on the turn.

## Monte Carlo equity

The most general tool is simulation: deal the unknown cards randomly many times and count how often
the bot's hand wins. The result is its *equity*, the expected share of the pot.

```
function equity(hole, board, opponents, iterations):
    deck = all 52 cards without hole and board
    wins = 0
    repeat iterations times:
        shuffle deck
        full_board = board + first (5 - len(board)) cards of deck
        opponent hands = next 2 * opponents cards, two per opponent
        mine = rank(hole + full_board)
        best_other = best rank among opponent hands + full_board
        if mine beats best_other: wins += 1
        if mine ties best_other:  wins += 0.5
    return wins / iterations
```

A typical rule: **call** if equity exceeds the pot odds, **raise** if it is clearly higher. A few
thousand iterations fit comfortably into the 15-second limit in most languages.

The required building block is a **hand evaluator**: a function that ranks the best five-card hand
out of seven cards. Writing one is a good exercise (counting ranks and suits covers most hand
types); ready-made evaluators exist for most languages, often based on the "Cactus Kev" or
"two plus two" approaches.

<details>
<summary>Refinement: hand ranges</summary>

Uniformly random opponent hands are too pessimistic preflop and too optimistic later. A player who
raised three times by the river rarely holds 7-2. Sampling opponent hands from a **range** of
plausible holdings (for example the top 20% by Chen score after a preflop raise) gives
considerably better estimates.
</details>

## Bet sizing

- **Value bets** with strong hands of about half to three quarters of the pot still get called by
  weaker hands.
- **Minimum raises** give opponents very favourable pot odds and protect little.
- **Bluffs** keep a bot from becoming predictable. They work best on threatening boards (e.g. three
  cards of one suit) and against few opponents.
- Because `amount` is the total bet, a raise of three quarters of the pot is
  `current_bet + 0.75 × pot`, clipped to `[legal.raise.min, legal.raise.max]`.

## Tournament considerations

- **Rising blinds** make the stack size in big blinds (`stack / blinds.big`) more relevant than the
  absolute number. Below roughly **10 big blinds**, a push-or-fold strategy (all-in or fold) is
  close to optimal.
- **Survival has value.** An early elimination earns no points, third place earns four. Near the
  end, marginal all-ins can be avoided while shorter stacks are likely to bust first.
- **Heads-up** play requires a much wider range of hands, since a player is in the blinds every hand.

## Opponent modelling

The complete history of every finished hand, including all hole cards, is public:

```
GET /api/v1/bot/hands?tournament_id=7          → list of hands
GET /api/v1/bot/hands/{id}                      → events including all hole cards
```

Useful per-opponent statistics (keyed by `name`):

- **VPIP**: how often a player voluntarily puts chips in preflop (above 50% loose, below 20% tight).
- **Aggression**: ratio of raises to calls.
- **Showdown hands**: what a player held after large bets.

Typical adjustments are bluffing tight players more often, value-betting loose players more
heavily, and calling aggressive players more widely. The same data is available to every other
bot, so some randomness in the bot's own decisions makes it harder to model.

## Testing

- Practice tables with `"speed": "fast"` play hundreds of hands in minutes. Mixing the opponent
  types (`random`, `station`, `tight`) shows how a strategy copes with different styles.
- Logging each decision together with its reason (e.g. "equity 0.62 > pot odds 0.25 → call") makes
  unexpected behaviour easy to trace.
- Every hand on the website has a replay; the raw events shown below it are exactly what the bot
  receives.
- Real game states saved from `GET /turn` make good fixtures for unit tests of `decide`.
