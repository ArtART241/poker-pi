"""Picks a random legal action. Raises are kept small."""
import random

from pokerbot import run


def decide(state):
    legal = state["legal"]
    options = [{"action": "fold"}]
    if legal["check"]:
        options.append({"action": "check"})
    if legal["call"] is not None:
        options.append({"action": "call"})
    if legal["raise"]:
        options.append({"action": "raise", "amount": legal["raise"]["min"]})
    return random.choice(options)


if __name__ == "__main__":
    run(decide)
