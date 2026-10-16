
"""Discord live commentator for tournament poker events."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from typing import Any

log = logging.getLogger(__name__)

BIG_RAISE_MULTIPLE = 10

def _format_event(
    event: dict[str, Any],
    *,
    table_title: str,
    big_blind: int,
) -> str | None:
    """Turnier-Events in abwechslungsreichen deutschen Discord-Livekommentar umwandeln."""

    event_type = event.get("type")
    table = table_title or "Turniertisch"

    if event_type == "action":
        name = event.get("name", "Ein Spieler")

        # All-in: Raise oder Call
        if event.get("all_in"):
            bet = f"{event.get('bet', 0):,}".replace(",", ".")
            pot = f"{event.get('pot', 0):,}".replace(",", ".")

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

        # Großes Raise ab 10x Big Blind
        amount = event.get("amount")

        if (
            event.get("action") == "raise"
            and isinstance(amount, (int, float))
            and not isinstance(amount, bool)
            and big_blind > 0
            and amount >= BIG_RAISE_MULTIPLE * big_blind
        ):
            formatted_amount = f"{amount:,}".replace(",", ".")
            multiplier = amount / big_blind

            messages = [
                f"🚨 **DICKER RAISE!**\n"
                f"**{name}** erhöht auf **{formatted_amount} Chips** "
                f"({multiplier:.1f}x Big Blind). Da wird ordentlich Druck gemacht! 💥",

                f"💥 **WAS FÜR EIN RAISE!**\n"
                f"**{name}** legt nach und erhöht auf **{formatted_amount} Chips** "
                f"({multiplier:.1f}x BB). Das ist mal eine Ansage!",

                f"🔥 **ORDENTLICH DRUCK AM TISCH!**\n"
                f"**{name}** macht ein Raise auf **{formatted_amount} Chips** "
                f"({multiplier:.1f}x Big Blind). Da müssen die Gegner erst mal mithalten!",

                f"🚀 **RAISE MIT WUMMS!**\n"
                f"**{name}** schraubt den Einsatz auf **{formatted_amount} Chips** "
                f"({multiplier:.1f}x BB) hoch. Hier wird nicht gekleckert!",

                f"😈 **EINE KLARE ANSAGE!**\n"
                f"**{name}** erhöht auf satte **{formatted_amount} Chips** "
                f"({multiplier:.1f}x Big Blind). Die Konkurrenz steht unter Druck!",

                f"⚡ **GROSSER MOVE!**\n"
                f"**{name}** feuert ein Raise über **{formatted_amount} Chips** "
                f"({multiplier:.1f}x BB) ab. Da zeigt jemand Präsenz!"
            ]

            return random.choice(messages)

    elif event_type == "tournament_end":
        winner = event.get("winner")

        if not winner:
            return None

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
        name = event.get("name", "Ein Spieler")
        place = event.get("place")

        # Zweiter Platz
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

        # Alle anderen bekannten Platzierungen ab Platz 3
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

        # Ausscheiden ohne bekannte Platzierung
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

def _post_webhook(url: str, message: str) -> None:
    """Send a Discord webhook message. Runs in a worker thread."""
    payload = {
        "content": message,
        "allowed_mentions": {"parse": []},
    }
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        if not 200 <= response.status < 300:
            raise RuntimeError(f"Discord returned HTTP {response.status}")

async def _send(message: str) -> None:
    url = os.environ.get("DISCORD_TOURNAMENT_WEBHOOK_URL", "").strip()
    if not url:
        return

    try:
        await asyncio.to_thread(_post_webhook, url, message)
    except (HTTPError, URLError, TimeoutError, OSError, RuntimeError):
        log.exception("Could not send tournament event to Discord")

def schedule_tournament_event(
    event: dict[str, Any],
    *,
    table_title: str,
    big_blind: int,
) -> None:
    """Schedule a notification without blocking the poker event loop."""
    message = _format_event(
        event,
        table_title=table_title,
        big_blind=big_blind,
    )
    if message is None:
        return

    try:
        asyncio.get_running_loop().create_task(_send(message))
    except RuntimeError:
        log.warning("No running event loop; Discord notification skipped")