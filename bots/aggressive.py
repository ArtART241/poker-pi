"""Raises the pot whenever nobody has raised yet, otherwise calls. Goes all-in when short."""
from pokerbot import run


def decide(state):
    legal = state["legal"]
    short = state["stack"] <= 10 * state["blinds"]["big"]
    if legal["raise"] and short:
        return {"action": "allin"}
    if legal["raise"] and state["current_bet"] <= state["blinds"]["big"]:
        target = state["current_bet"] + state["pot"]
        return {"action": "raise", "amount": max(legal["raise"]["min"], min(target, legal["raise"]["max"]))}
    return {"action": "check"} if legal["check"] else {"action": "call"}


if __name__ == "__main__":
    run(decide)
