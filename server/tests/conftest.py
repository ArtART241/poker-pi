import pytest


@pytest.fixture(autouse=True)
def no_real_discord(monkeypatch):
    """Tests must never post to a real webhook, even if the variable is set in the shell."""
    monkeypatch.delenv("DISCORD_TOURNAMENT_WEBHOOK_URL", raising=False)
