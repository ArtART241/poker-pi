"""Wires the pieces together. One Hub per running server."""

from __future__ import annotations

import asyncio
import contextlib

from .config import Settings
from .store.db import Store
from .tables.table import Table
from .tables.turns import TurnRegistry
from .tournament.manager import PracticeManager, TournamentManager


class Hub:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = Store(settings.db_path)
        self.registry = TurnRegistry(settings.disconnect_after)
        self.tables: dict[str, Table] = {}
        self.tournaments = TournamentManager(self)
        self.practice = PracticeManager(self)
        self._scheduler: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self.store.delete_unfinished_hands()
        self._scheduler = asyncio.create_task(self.tournaments.scheduler_loop(), name="scheduler")

    async def stop(self) -> None:
        tasks = [t.task for t in self.tables.values() if t.task and not t.task.done()]
        if self._scheduler:
            tasks.append(self._scheduler)
        for task in tasks:
            task.cancel()
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
        self.store.close()
