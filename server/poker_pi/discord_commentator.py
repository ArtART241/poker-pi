"""Live commentary for tournaments in a Discord channel, sent through a webhook.

Set DISCORD_TOURNAMENT_WEBHOOK_URL to turn it on. Messages (in German, for the players' server)
go out one after the other from a single background task, so they arrive in the order the events
happened and a slow or unreachable Discord never holds up a table.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import re
from typing import TYPE_CHECKING, Any, Callable
from urllib.error import HTTPError
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    from .tables.table import Table

log = logging.getLogger(__name__)

BIG_RAISE_MULTIPLE = 10
MAX_MESSAGE = 2000  # Discord's limit for the content of one message
QUEUE_SIZE = 200  # messages waiting while Discord is slow; newer ones are dropped beyond that
POST_TIMEOUT = 5.0

_MARKDOWN = re.compile(r"([\\*_~`|>#\[\]()-])")


def _md(text: Any) -> str:
    """Escape Discord markdown, so a bot called "**x**" shows up as written."""
    return _MARKDOWN.sub(r"\\\1", str(text))


def _chips(n: Any) -> str:
    """1500 -> "1.500" (German thousands separator)."""
    return f"{n:,}".replace(",", ".") if isinstance(n, int) else str(n)


def _decimal(x: float) -> str:
    """37.5 -> "37,5", 10.0 -> "10"."""
    return f"{x:.1f}".removesuffix(".0").replace(".", ",")


def _format_event(
    event: dict[str, Any],
    *,
    table_title: str,
    big_blind: int,
) -> str | None:
    """Turn a tournament event into a German live-commentary line, or None if it is not worth one."""

    event_type = event.get("type")
    table = _md(table_title or "Turniertisch")

    if event_type == "action":
        name = _md(event.get("name") or "Ein Spieler")

        # all-in, whether by raise or by call
        if event.get("all_in"):
            bet = _chips(event.get("bet", 0))
            pot = _chips(event.get("pot", 0))

            messages = [
                f"🔥 **ALL-IN!**\n"
                f"**{name}** geht mit {bet} Chips im aktuellen Einsatz all-in! "
                f"Im Pot liegen jetzt {pot} Chips.",

                f"💣 **ALLES ODER NICHTS!**\n"
                f"**{name}** stellt {bet} Chips in die Mitte! "
                f"Der Pot wächst auf satte {pot} Chips an. Was für ein Move!",

                f"🚨 **ALL-IN AM {table}!**\n"
                f"**{name}** riskiert {bet} Chips! "
                f"Im Pot befinden sich mittlerweile {pot} Chips. Jetzt wird's ernst!",

                f"⚡ **VOLLES RISIKO!**\n"
                f"**{name}** geht mit {bet} Chips all-in! "
                f"{pot} Chips liegen bereits im Pot. Wer hält dem Druck stand?",

                f"🎯 **CHIPS IN DIE MITTE!**\n"
                f"**{name}** macht ernst und geht für {bet} Chips all-in! "
                f"Der Pot steht jetzt bei {pot} Chips. Die Spannung steigt!"
            ]

            return random.choice(messages)

        # big raise: to at least BIG_RAISE_MULTIPLE big blinds
        amount = event.get("amount")

        if (
            event.get("action") == "raise"
            and isinstance(amount, (int, float))
            and not isinstance(amount, bool)
            and big_blind > 0
            and amount >= BIG_RAISE_MULTIPLE * big_blind
        ):
            formatted_amount = _chips(amount)
            multiplier = _decimal(amount / big_blind)

            messages = [
                f"🚨 **DICKER RAISE!**\n"
                f"**{name}** erhöht auf **{formatted_amount} Chips** "
                f"({multiplier}x Big Blind). Da wird ordentlich Druck gemacht! 💥",

                f"💥 **WAS FÜR EIN RAISE!**\n"
                f"**{name}** legt nach und erhöht auf **{formatted_amount} Chips** "
                f"({multiplier}x BB). Das ist mal eine Ansage!",

                f"🔥 **ORDENTLICH DRUCK AM TISCH!**\n"
                f"**{name}** macht ein Raise auf **{formatted_amount} Chips** "
                f"({multiplier}x Big Blind). Da müssen die Gegner erst mal mithalten!",

                f"🚀 **RAISE MIT WUMMS!**\n"
                f"**{name}** schraubt den Einsatz auf **{formatted_amount} Chips** "
                f"({multiplier}x BB) hoch. Hier wird nicht gekleckert!",

                f"😈 **EINE KLARE ANSAGE!**\n"
                f"**{name}** erhöht auf satte **{formatted_amount} Chips** "
                f"({multiplier}x Big Blind). Die Konkurrenz steht unter Druck!",

                f"⚡ **GROSSER MOVE!**\n"
                f"**{name}** feuert ein Raise über **{formatted_amount} Chips** "
                f"({multiplier}x BB) ab. Da zeigt jemand Präsenz!"
            ]

            return random.choice(messages)

    elif event_type == "tournament_end":
        if not event.get("winner"):
            return None
        winner = _md(event["winner"])

        messages = [
            f"🏆 **TURNIERSIEG!** 🏆\n"
            f"👑 **{winner}** gewinnt das gesamte Turnier!\n"
            "Was für eine Performance am Tisch! GG! 🎉",

            f"👑 **DER CHAMPION STEHT FEST!** 👑\n"
            f"🏆 **{winner}** holt sich den Turniersieg!\n"
            "Alle Gegner sind bezwungen – was für eine Leistung! GG! 🥳",

            f"🥇 **SIEG! SIEG! SIEG!** 🥇\n"
            f"**{winner}** setzt sich gegen das gesamte Feld durch "
            "und gewinnt das Turnier!\nWas für ein Lauf! 🏆",

            f"🎉 **GLÜCKWUNSCH ZUM TURNIERSIEG!** 🎉\n"
            f"🏆 **{winner}** krönt sich zum Champion!\n"
            "Der letzte Gegner ist geschlagen. Eine starke Vorstellung!",

            f"🔥 **DER POKAL GEHT AN ... {winner.upper()}!** 🔥\n"
            f"**{winner}** gewinnt das komplette Turnier!\n"
            "Was für ein Finale, was für ein Champion! 🏆",

            f"🏆 **MISSION ERFÜLLT!** 🏆\n"
            f"**{winner}** lässt die gesamte Konkurrenz hinter sich "
            "und sichert sich den Turniersieg!\nGG an den Champion! 👑"
        ]

        return random.choice(messages)

    elif event_type == "eliminated":
        name = _md(event.get("name") or "Ein Spieler")
        place = event.get("place")

        # runner-up
        if place == 2:
            messages = [
                f"💥 **TURNIER AUS!**\n"
                f"**{name}** scheidet auf Platz 2 aus. "
                "Knapp am ganz großen Triumph vorbei! 🥈",

                f"🥈 **RUNNER-UP!**\n"
                f"Für **{name}** reicht es am Ende für Platz 2. "
                "Der Turniersieg war zum Greifen nah!",

                f"💔 **SO KNAPP AM TITEL VORBEI!**\n"
                f"**{name}** beendet das Turnier auf dem zweiten Platz. "
                "Ein starkes Ergebnis, auch wenn der ganz große Wurf ausbleibt.",

                f"🎭 **DAS FINALE IST ENTSCHIEDEN!**\n"
                f"**{name}** landet auf Platz 2 und muss sich geschlagen geben. "
                "Heute reicht es knapp nicht für die Krone! 🥈",

                f"🃏 **GAME OVER AUF PLATZ 2!**\n"
                f"Für **{name}** endet die Reise als Zweitplatzierter. "
                "Nur ein Schritt hat zum Turniersieg gefehlt!",

                f"🥈 **SILBER STATT GOLD!**\n"
                f"**{name}** scheidet als Zweiter aus. "
                "Ganz nah dran am Titel, aber heute bleibt nur Platz 2."
            ]

            return random.choice(messages)

        # every other known place, from 3rd down
        if isinstance(place, int) and not isinstance(place, bool) and place > 2:
            messages = [
                f"💥 **PLAYER OUT!**\n"
                f"Für **{name}** ist Schluss — Platz **{place}**. "
                "Der Traum vom Titel ist geplatzt! 🃏",

                f"🚪 **AUSGESCHIEDEN!**\n"
                f"**{name}** beendet das Turnier auf Platz **{place}**. "
                "Diesmal reicht es leider nicht für den ganz großen Wurf.",

                f"💔 **DAS WAR'S!**\n"
                f"**{name}** muss das Turnier auf Rang **{place}** verlassen. "
                "Die Reise endet hier!",

                f"🃏 **NÄCHSTER SPIELER MUSS GEHEN!**\n"
                f"Für **{name}** ist auf Platz **{place}** Schluss. "
                "Der Traum vom Titel lebt für die anderen weiter!",

                f"🚨 **ELIMINIERT!**\n"
                f"**{name}** scheidet auf Platz **{place}** aus dem Turnier aus. "
                "Die Konkurrenz wird kleiner!",

                f"♠️ **KEIN WEITERKOMMEN MEHR!**\n"
                f"**{name}** beendet das Turnier auf Platz **{place}**. "
                "Jetzt heißt es zuschauen und auf das nächste Turnier warten!",

                f"💥 **CHIPS WEG, TURNIER VORBEI!**\n"
                f"Für **{name}** endet das Turnier auf Rang **{place}**. "
                "Der nächste Spieler muss seine Sachen packen!"
            ]

            return random.choice(messages)

        # out without a known place
        messages = [
            f"💥 **PLAYER OUT!**\n"
            f"**{name}** scheidet aus dem Turnier aus!",

            f"🚪 **FEIERABEND AM TISCH!**\n"
            f"Für **{name}** ist das Turnier vorbei!",

            f"🃏 **DAS WAR'S FÜR DICH!**\n"
            f"**{name}** muss das Turnier verlassen. Der nächste bitte!",

            f"💔 **AUS UND VORBEI!**\n"
            f"Für **{name}** endet die Pokerreise an dieser Stelle.",

            f"🚨 **ELIMINATION!**\n"
            f"**{name}** ist raus! Ein Platz weniger im Kampf um den Titel.",

            f"♠️ **DER NÄCHSTE MUSS GEHEN!**\n"
            f"**{name}** scheidet aus dem Turnier aus. Weiter geht's!"
        ]

        return random.choice(messages)

    return None


def post_webhook(url: str, message: str) -> None:
    """Send one message to a Discord webhook (blocking; runs in a worker thread)."""
    payload = {"content": message, "allowed_mentions": {"parse": []}}
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        # Discord rejects urllib's default user agent with 403 (Cloudflare error 1010)
        headers={"Content-Type": "application/json", "User-Agent": "poker-pi (discord commentator)"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=POST_TIMEOUT):
            pass
    except HTTPError as e:
        detail = e.read(300).decode("utf-8", "replace").strip()
        raise RuntimeError(f"Discord answered HTTP {e.code}: {detail}") from None


Poster = Callable[[str, str], None]


class DiscordCommentator:
    """Formats tournament events and posts them to the webhook, strictly in order."""

    def __init__(self, url: str, post: Poster = post_webhook) -> None:
        url = url.strip()
        if url and not url.startswith("https://"):
            log.warning("DISCORD_TOURNAMENT_WEBHOOK_URL is not an https:// URL; Discord commentary is off")
            url = ""
        self.url = url
        self._post = post
        self._queue: asyncio.Queue[str] | None = None
        self._worker: asyncio.Task[None] | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.url)

    def start(self) -> None:
        if not self.enabled:
            return
        self._queue = asyncio.Queue(QUEUE_SIZE)
        self._worker = asyncio.create_task(self._run(), name="discord-commentator")
        log.info("Discord commentary is on")

    async def stop(self, drain: float = 3.0) -> None:
        """Give queued messages (e.g. the winner) a moment to go out, then stop the worker."""
        if self._worker is None:
            return
        if self._queue is not None:
            try:
                await asyncio.wait_for(self._queue.join(), drain)
            except asyncio.TimeoutError:
                log.warning("Discord commentary stopped with %d messages unsent", self._queue.qsize())
        self._worker.cancel()
        try:
            await self._worker
        except asyncio.CancelledError:
            pass
        self._worker = None

    def on_event(self, table: "Table", event: dict[str, Any]) -> None:
        """Table event hook. Never raises: commentary must not break a tournament."""
        if self._queue is None:
            return
        try:
            message = _format_event(event, table_title=table.title,
                                    big_blind=table.blinds.big if table.blinds else 0)
        except Exception:
            log.exception("Could not format %s event for Discord", event.get("type"))
            return
        if message is None:
            return
        try:
            self._queue.put_nowait(message[:MAX_MESSAGE])
        except asyncio.QueueFull:
            log.warning("Discord queue is full, dropping a %s message", event.get("type"))

    async def _run(self) -> None:
        assert self._queue is not None
        while True:
            message = await self._queue.get()
            try:
                await asyncio.to_thread(self._post, self.url, message)
            except Exception as e:  # network trouble, HTTP errors: log and carry on
                log.warning("Could not send a message to Discord: %s", e)
            finally:
                self._queue.task_done()
