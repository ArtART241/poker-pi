# Poker rules

The game is **No-Limit Texas Hold'em**, played as a tournament. This page covers the rules a bot
has to respect; how to play *well* is left to each participant.

## Course of a hand

Each player receives **two private cards** (*hole cards*). Up to five **community cards** (the
*board*) are dealt face up and shared by everyone. The best **five-card combination** out of a
player's two cards and the board wins the pot.

| Phase | What happens |
|---|---|
| **Preflop** | Blinds are posted, two cards are dealt to each player. First betting round. |
| **Flop** | Three community cards. Second betting round. |
| **Turn** | Fourth community card. Third betting round. |
| **River** | Fifth community card. Final betting round. |
| **Showdown** | The remaining players reveal their cards; the best hand wins. |

A hand ends early when all players but one have folded. The remaining player wins the pot without
showing cards.

## Button, blinds and order of play

- The **dealer button** (the **D** puck on the table) moves one seat clockwise every hand.
- The player left of the button posts the **small blind**, the next one the **big blind**: forced
  bets that create an initial pot.
- **Preflop**, the player left of the big blind acts first; the big blind acts last.
- **From the flop on**, the first active player left of the button acts first.
- **Heads-up** (two players): the button posts the small blind, acts first preflop and last on
  later streets.
- Later tournament levels add an **ante**: a small amount paid by every player before the hand.
  Antes go directly into the pot and do not count as a bet.

The server determines the order of play and the allowed actions, so a bot does not need to
compute any of this. Position still matters strategically: acting last provides more information.

## Actions

| Action | Allowed when | Effect |
|---|---|---|
| **fold** | always | The hand is given up; chips already in the pot are lost. |
| **check** | nobody has bet more than the player on this street | No chips are added. |
| **call** | another player has bet more | The highest bet is matched. |
| **raise** | `legal.raise` is not `null` | The bet is increased. |

### Raise *to*, not raise *by*

`amount` always denotes **the total bet on the current street after the raise**, not the
increase. Raising a big blind of 20 to 60 is sent as `{"action": "raise", "amount": 60}`,
regardless of how much the player had already put in on that street.

The allowed range is given by `legal.raise.min` and `legal.raise.max`; any whole number in
between is valid.

- **Minimum raise**: the current bet plus the size of the last full raise. After a raise from
  20 to 60 (an increase of 40), the next minimum is 100.
- **Maximum**: all remaining chips (all-in), hence "No-Limit".
- A player without enough chips for a minimum raise may still go all-in; then `min == max`.

`legal.raise` is `null` when raising is not possible, for example when every opponent is already
all-in, or when the betting has not been reopened (see below).

### All-in and side pots

A player can never lose more than their stack. Someone who cannot cover a bet calls **all-in**
with the remaining chips and can win at most that amount from each opponent. The excess forms a
**side pot** among the other players. The server computes all pots.

<details>
<summary>When a short all-in does not reopen the betting</summary>

If a player bets 100 and an opponent goes all-in for 130, the increase of 30 is smaller than a
full raise. When the action returns to the first player, they may call or fold but not raise
again. Several short all-ins that together amount to a full raise do reopen the betting. This is
the standard casino rule; a bot only needs to look at `legal.raise`.
</details>

## Hand rankings (best to worst)

| Hand | Example | Description |
|---|---|---|
| Straight flush | `9h 8h 7h 6h 5h` | Five consecutive cards of one suit (A-K-Q-J-T is a royal flush) |
| Four of a kind | `Qs Qh Qd Qc 4s` | Four cards of the same rank |
| Full house | `Ts Th Td 3c 3s` | Three of a kind plus a pair |
| Flush | `Ad Jd 8d 4d 2d` | Five cards of one suit |
| Straight | `8c 7d 6h 5s 4c` | Five consecutive cards (the ace counts high `A K Q J T` or low `5 4 3 2 A`) |
| Three of a kind | `7s 7h 7d Kc 2s` | Three cards of the same rank |
| Two pair | `Js Jd 5c 5h As` | Two different pairs |
| One pair | `Ah Ad 9c 6s 3h` | Two cards of the same rank |
| High card | `Ks Jd 8c 5h 2s` | None of the above |

Equal hands split the pot; an odd chip goes to the first winner left of the button.

## Card notation

Cards are two-character strings: **rank + suit**.

- Ranks: `2 3 4 5 6 7 8 9 T J Q K A` (`T` = ten)
- Suits: `c` clubs, `d` diamonds, `h` hearts, `s` spades

`"Ah"` is the ace of hearts, `"Td"` the ten of diamonds. The position of the rank character in the
string `"23456789TJQKA"` gives a numeric rank from 0 to 12.

## Tournament format

- **Freezeout**: every bot starts with the same stack (usually 1500 chips). A bot without chips is
  eliminated; there are no rebuys.
- **Blinds increase** every few hands (shown on the tournament page, typically every 10 hands), so
  every tournament ends eventually.
- One table with up to **9 bots**. Seats are assigned randomly.
- **Placement** follows the order of elimination. Bots eliminated in the same hand are ranked by
  their stack at the start of that hand.
- **Leaderboard points**: 1st 10, 2nd 6, 3rd 4, 4th 3, 5th 2, 6th 1.

## Hidden information

- A bot only sees its own hole cards. Opponents' cards are revealed at the showdown (`showdown`
  event) and never earlier.
- Spectators do not see hole cards while a hand is in progress either.
- **After a hand has finished**, its complete history, including all hole cards (also of folded
  hands), is available to every bot via `GET /api/v1/bot/hands/{id}`. All bots have the same
  access; the data can be used to study opponents.
- Cards are shuffled with a cryptographically secure random number generator.
