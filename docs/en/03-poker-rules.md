# Poker rules

We play **No-Limit Texas Hold'em** tournaments. If you've never played, this page is enough to write
a bot that plays correctly. Playing *well* is the fun part, and that's up to you.

## A hand, step by step

Each player gets **2 private cards** (*hole cards*). Up to 5 **community cards** (the *board*) are
dealt face up in the middle and everyone can use them. The best **5-card combination** out of your
2 + the 5 shared cards wins the pot.

| Phase | What happens |
|---|---|
| **Preflop** | Blinds are posted, everyone gets 2 cards. First betting round. |
| **Flop** | 3 community cards. Second betting round. |
| **Turn** | 4th community card. Third betting round. |
| **River** | 5th community card. Last betting round. |
| **Showdown** | Players still in the hand show their cards and the best hand wins. |

A hand ends early when everyone except one player folds. That player wins the pot without showing
cards.

## Button, blinds and turn order

- The **button** (dealer, marked **D**) moves one seat clockwise every hand.
- The player left of the button posts the **small blind**, the next one the **big blind**. These are
  forced bets so there's something to play for.
- **Preflop**, the player left of the big blind acts first, and the big blind acts last.
- **On flop, turn and river**, the first active player left of the button acts first.
- **Heads-up** (only 2 players left): the button posts the small blind and acts *first* preflop but
  *last* after the flop.
- Later in tournaments there's also an **ante**: a small amount *everyone* pays before the hand.
  Antes go straight into the pot and don't count as a bet.

You don't have to compute any of this yourself. The server tells you whose turn it is and what you're
allowed to do. It's still useful for strategy: acting last (being "in position") is a big advantage.

## Your options

| Action | When | Effect |
|---|---|---|
| **fold** | always | Give up the hand. Your chips in the pot are lost. |
| **check** | if nobody has bet more than you on this street | Do nothing, pass the turn on. |
| **call** | if someone bet more than you | Match the highest bet. |
| **raise** | if allowed | Increase the bet. |

### "Raise TO", not "raise BY"

In poker-pi, `amount` is always **the total you want your bet on this street to be**, not the
increase. Example: the big blind is 20 and you want to make it 60. You send
`{"action": "raise", "amount": 60}`, even though you only add 60 minus whatever you already bet.

The server gives you the allowed range in `legal.raise.min` and `legal.raise.max`. Any whole
number in between is fine.

- **Minimum raise**: the current bet plus the size of the last raise. If someone raised from 20 to 60
  (a raise of 40), the next minimum is 100.
- **Maximum**: all your chips (*all-in*). That's the "No-Limit" part.
- If you don't have enough chips for a minimum raise, you can still go all-in: then `min == max`.

> If `legal.raise` is `null`, you can't raise right now. That happens when everyone else is all-in,
> or when the betting wasn't reopened (see below).

### All-in and side pots

You can never lose more than you have. If you can't afford a call, you call **all-in** with what's
left and can only win as much from each opponent as you put in yourself. The rest forms a **side
pot** between the other players. The server calculates all of this. Your bot only needs to know
that it can be all-in with chips still behind in other players' stacks.

<details>
<summary>Advanced: when a short all-in doesn't reopen the betting</summary>

Say you bet 100 and someone goes all-in for 130. That's a raise of only 30, smaller than a "full"
raise. When the action comes back to you, you may **call or fold, but not raise again**. Real
casinos use the same rule. Several short all-ins that add up to a full raise do reopen the betting.
You don't need to remember this: just check `legal.raise`.
</details>

## Hand rankings (best to worst)

| Hand | Example | Description |
|---|---|---|
| Straight flush | `9h 8h 7h 6h 5h` | Five in a row, same suit (the best one, A-K-Q-J-T, is a royal flush) |
| Four of a kind | `Qs Qh Qd Qc 4s` | Four cards of the same rank |
| Full house | `Ts Th Td 3c 3s` | Three of a kind + a pair |
| Flush | `Ad Jd 8d 4d 2d` | Five cards of the same suit |
| Straight | `8c 7d 6h 5s 4c` | Five in a row (A can be high `A K Q J T` or low `5 4 3 2 A`) |
| Three of a kind | `7s 7h 7d Kc 2s` | Three cards of the same rank |
| Two pair | `Js Jd 5c 5h As` | Two different pairs |
| One pair | `Ah Ad 9c 6s 3h` | Two cards of the same rank |
| High card | `Ks Jd 8c 5h 2s` | None of the above |

Equal hands split the pot. Leftover odd chips go to the first winner left of the button.

## Card notation

Cards are 2-character strings: **rank + suit**.

- Ranks: `2 3 4 5 6 7 8 9 T J Q K A` (`T` = ten)
- Suits: `c` clubs ♣, `d` diamonds ♦, `h` hearts ♥, `s` spades ♠

So `"Ah"` is the ace of hearts and `"Td"` is the ten of diamonds. A handy trick: `"23456789TJQKA".index(card[0])`
gives you the rank as a number from 0 to 12.

## Tournament format

- **Freezeout**: everyone starts with the same stack (usually 1500 chips). If you lose all your chips
  you're out, with no rebuys.
- **Blinds go up** every few hands (shown on the tournament page, usually every 10 hands), so the
  tournament always ends. Late in the tournament the blinds are big and you can't wait for perfect
  hands forever.
- One table with up to **9 bots**. Seats are drawn randomly.
- **Placement** is by bust-out order: the last one standing wins. If two bots bust in the same hand,
  the one that started the hand with more chips places higher.
- **Points** for the leaderboard: 1st 10 · 2nd 6 · 3rd 4 · 4th 3 · 5th 2 · 6th 1.

## Hidden information and fairness

- Your bot sees **its own** hole cards only. Opponents' cards are revealed at the showdown (in the
  `showdown` event) and never before.
- Spectators on the website also don't see hole cards while a hand is running.
- **After a hand is over**, its full history including everyone's cards (even of folded hands) is
  available to everyone via `GET /api/v1/bot/hands/{id}`. All bots have the same access, and you can
  use it to learn how your opponents play (see [Strategy tips](#/docs/strategy)).
- Cards are shuffled with a cryptographically secure random generator.
