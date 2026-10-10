"""Plays only pairs and two high cards; raises those once, folds everything else to a bet."""
from pokerbot import run

RANKS = "23456789TJQKA"


def decide(state):
    legal = state["legal"]
    r1, r2 = (RANKS.index(c[0]) for c in state["hole_cards"])
    good = r1 == r2 or min(r1, r2) >= RANKS.index("T")
    nobody_raised = state["current_bet"] <= state["blinds"]["big"]
    if good and legal["raise"] and nobody_raised:
        amount = max(legal["raise"]["min"], 3 * state["blinds"]["big"])
        return {"action": "raise", "amount": min(amount, legal["raise"]["max"])}
    if legal["check"]:
        return {"action": "check"}
    return {"action": "call"} if good else {"action": "fold"}


if __name__ == "__main__":
    run(decide)
