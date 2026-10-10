"""Calling station: checks when possible, otherwise calls. Never raises, never folds."""
from pokerbot import run


def decide(state):
    return {"action": "check"} if state["legal"]["check"] else {"action": "call"}


if __name__ == "__main__":
    run(decide)
