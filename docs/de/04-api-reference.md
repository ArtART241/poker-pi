# API-Referenz

Basis-URL: `https://poker.example.com`. Alle Bodies sind JSON (`Content-Type: application/json`).

Jeder Endpunkt unter `/api/v1/bot/` braucht den Header

```
Authorization: Bearer <dein Token>
```

Die interaktive Version dieser Seite, in der du jeden Request ausprobieren kannst, ist die
[Swagger UI](https://poker.example.com/docs). Die maschinenlesbare Spezifikation liegt unter
[/openapi.yaml](https://poker.example.com/openapi.yaml).

## Übersicht

| Methode | Pfad | Zweck |
|---|---|---|
| `GET` | `/api/v1/bot/me` | Wer bin ich? Gut, um den Token zu testen. |
| `GET` | `/api/v1/bot/turn?wait=25` | **Auf deinen Zug warten** (Long-Poll). |
| `POST` | `/api/v1/bot/action` | **Deine Entscheidung schicken.** |
| `GET` | `/api/v1/bot/tournaments` | Kommende, laufende und letzte Turniere. |
| `POST` | `/api/v1/bot/tournaments/{id}/register` | Für ein Turnier anmelden. |
| `DELETE` | `/api/v1/bot/tournaments/{id}/register` | Abmelden (vor dem Start). |
| `POST` | `/api/v1/bot/practice` | Übungstisch gegen Haus-Bots starten. |
| `GET` | `/api/v1/bot/practice` | Status deines Übungstischs. |
| `DELETE` | `/api/v1/bot/practice` | Übungstisch beenden. |
| `GET` | `/api/v1/bot/hands` | Beendete Hände, an denen du beteiligt warst. |
| `GET` | `/api/v1/bot/hands/{id}` | Kompletter Verlauf einer beendeten Hand (alle Karten). |

## GET /api/v1/bot/turn

Wartet, bis dein Bot eine Entscheidung treffen muss, und liefert dann den kompletten Spielzustand.

| Query-Parameter | Standard | Bedeutung |
|---|---|---|
| `wait` | `25` | Sekunden zu warten (0 bis 30). Passiert in der Zeit nichts: `204 No Content`. |
| `table_id` | keiner | Nur auf Züge an diesem Tisch warten (praktisch, wenn du gleichzeitig an einem Übungstisch *und* einem Turnier spielst). |

**Antworten:** `200` mit dem Zustand unten, oder `204` mit **leerem Body** (einfach nochmal fragen).

```json
{
  "turn_id": "t_c69e59e7862086fb",
  "deadline_ms": 14991,
  "table_id": "t7",
  "tournament_id": 7,
  "practice": false,
  "hand_id": 41,
  "hand_no": 12,
  "seat": 0,
  "name": "DocBot",
  "hole_cards": ["Jc", "Ac"],
  "stack": 1480,
  "bet": 0,
  "street": "turn",
  "board": ["7d", "Ad", "7h", "4s"],
  "pot": 40,
  "current_bet": 0,
  "to_call": 0,
  "legal": {
    "fold": true,
    "check": true,
    "call": null,
    "raise": { "min": 20, "max": 1480 }
  },
  "blinds": { "small": 10, "big": 20, "ante": 0, "level": 1, "hands_until_next_level": 9 },
  "button": 6,
  "players": [
    { "seat": 0, "name": "DocBot", "stack": 1480, "bet": 0, "committed": 20, "status": "active", "is_you": true },
    { "seat": 3, "name": "Carl Callstation", "stack": 1480, "bet": 0, "committed": 20, "status": "active", "is_you": false },
    { "seat": 6, "name": "Tina Tight", "stack": 1500, "bet": 0, "committed": 0, "status": "folded", "is_you": false }
  ],
  "action_log": [ "... siehe 'Events' unten ..." ]
}
```

| Feld | Bedeutung |
|---|---|
| `turn_id` | Kennzeichnet diese Entscheidung. Schick sie mit deiner Aktion zurück. |
| `deadline_ms` | Verbleibende Millisekunden zum Antworten. Danach checkt (wenn möglich) oder foldet der Server für dich. |
| `table_id`, `tournament_id`, `practice` | Wo die Hand gespielt wird. `tournament_id` ist an Übungstischen `null`. |
| `hand_id` | Global eindeutige ID der Hand (später für `/hands/{id}`). |
| `hand_no` | Nummer der Hand an diesem Tisch: 1, 2, 3, ... |
| `seat` | Dein Platz, 0 bis 8. Die Plätze gehen im Uhrzeigersinn um den Tisch. |
| `hole_cards` | Deine zwei privaten Karten. |
| `stack` | Deine Chips **dahinter**, ohne das, was du schon gesetzt hast. |
| `bet` | Was du **auf dieser Straße** schon gesetzt hast. |
| `street` | `preflop`, `flop`, `turn` oder `river`. |
| `board` | Gemeinschaftskarten: 0, 3, 4 oder 5. |
| `pot` | **Alle** Chips in der Mitte, inklusive aller Einsätze der aktuellen Straße. |
| `current_bet` | Der höchste Einsatz auf dieser Straße. |
| `to_call` | Chips, die du mit einem Call dazulegen würdest (0, wenn du checken kannst). |
| `legal.fold` | Immer `true`. |
| `legal.check` | `true`, wenn du checken darfst. |
| `legal.call` | Chips, die ein Call dazulegt, oder `null`, wenn es nichts zu callen gibt. Kann kleiner als `current_bet - bet` sein, wenn du zu wenig hast (All-in-Call). |
| `legal.raise` | `{"min", "max"}` für **Raise AUF**, oder `null`, wenn du nicht raisen darfst. `max` = All-in. |
| `blinds` | Aktueller Small/Big Blind, Ante, Level-Nummer und Hände bis zur nächsten Erhöhung. |
| `button` | Platz des Dealer-Buttons. |
| `players` | Alle Spieler dieser Hand, nach Platz sortiert. `status` ist `active`, `folded` oder `all_in`. `committed` ist, was sie in der ganzen Hand in den Pot gelegt haben. |
| `action_log` | Alles Öffentliche, was in dieser Hand bisher passiert ist, in Reihenfolge. |

<details>
<summary>Wie finde ich meine Position relativ zum Button?</summary>

```python
seats = [p["seat"] for p in state["players"]]          # nach Platz sortiert
n = len(seats)
button_idx = seats.index(state["button"])
my_idx = seats.index(state["seat"])
position = (my_idx - button_idx) % n   # 0 = Button, 1 = Small Blind, 2 = Big Blind, ...
```

Mit nur 2 Spielern (Heads-up) *ist* der Button der Small Blind.
</details>

## POST /api/v1/bot/action

```json
{ "turn_id": "t_c69e59e7862086fb", "action": "raise", "amount": 120 }
```

| Feld | Bedeutung |
|---|---|
| `turn_id` | Aus `GET /turn`. |
| `action` | `fold`, `check`, `call` oder `raise`. |
| `amount` | Nur bei `raise`: der **Gesamt**einsatz, **auf** den du erhöhst (zwischen `legal.raise.min` und `max`). |

Um dir das Leben leichter zu machen, akzeptiert der Server auch:
- `"bet"` als anderes Wort für `raise`,
- `"allin"` / `"all_in"`: auf das Maximum raisen (oder callen, wenn Raisen nicht möglich ist),
- `"call"`, wenn es nichts zu callen gibt: Das zählt als `check`.

**Antworten:**

| Code | Body | Bedeutung |
|---|---|---|
| `200` | `{"accepted": true, "action": "raise", "amount": 120}` | Angenommen. `action` ist, was tatsächlich ausgeführt wurde (z. B. `check`, wenn du `call` ohne offenen Einsatz geschickt hast). |
| `422` | `{"detail": "raise amount 25 is out of range: raise TO between 40 and 1480"}` | Nicht erlaubt. **Der Zug ist noch offen**, du kannst vor der Deadline eine korrigierte Aktion schicken. |
| `409` | `{"detail": "this turn is no longer open ..."}` | Zu spät, der Zug ist abgelaufen, oder du hast schon anders geantwortet. |
| `403` | `{"detail": "this turn belongs to another bot"}` | Falsche `turn_id`. |

**Exakt denselben** Request zweimal zu schicken (z. B. als Retry nach einem Netzwerkfehler) ist
unproblematisch und liefert wieder `200`.

> **Validierungsfehler:** Ist der Body kaputt (kein JSON, `turn_id` fehlt, `amount` ist keine Zahl),
> bekommst du `422` mit `detail` als **Liste**, die das Problem beschreibt, z. B.
> `{"detail": [{"type": "missing", "loc": ["body", "turn_id"], "msg": "Field required"}]}`.

## Events im `action_log`

Jeder Eintrag hat einen `type`. Platzbezogene Events haben außerdem `seat` und `name`.

| `type` | Felder | Bedeutung |
|---|---|---|
| `hand_start` | `hand_id`, `hand_no`, `level`, `button`, `small_blind`, `big_blind`, `ante`, `players[{seat, name, player_id, stack}]` | Eine neue Hand. Stacks *vor* den Blinds. |
| `post` | `blind` (`small` / `big` / `ante`), `amount`, `all_in` | Pflichteinsatz. |
| `action` | `street`, `action`, `amount`, `bet`, `stack`, `all_in`, `pot` | Ein Spieler hat gehandelt. `amount`: dazugelegte Chips bei `call`, neuer Gesamteinsatz bei `raise`, `null` bei `fold` / `check`. `bet` / `stack` gelten nach der Aktion. |
| `street` | `street`, `cards` (neue Karten), `board` (alle), `pot` | Flop, Turn oder River ausgeteilt. |
| `uncalled` | `amount` | Ein nicht gecallter Teil eines Einsatzes wurde zurückgegeben. |
| `showdown` | `hands[{seat, name, cards}]` | Karten aufgedeckt. Passiert am Ende oder früher, wenn alle All-in sind. |
| `win` | `pot` (0 = Hauptpot, 1+ = Side Pots), `amount`, `winners[{seat, name, amount}]`, `hand` (z. B. `"Two Pair"`, `null`, wenn keiner zeigen musste) | Wer welchen Pot gewonnen hat. |
| `hand_end` | `board`, `results[{seat, name, player_id, start_stack, stack, net, cards}]` | Endergebnis (nur in beendeten Händen). |
| `player_status` | `status`: `timeout`, `sitting_out`, `disconnected`, `connected`, `back` | Mit der Verbindung eines Bots ist etwas passiert (siehe [Spielablauf](#/docs/game-loop)). |

## Turniere

### GET /api/v1/bot/tournaments

```json
[
  {
    "id": 7, "name": "Friday Night Poker", "status": "registering",
    "start_at": "2026-10-16T18:00:00+00:00", "started_at": null, "finished_at": null, "note": null,
    "table_id": "t7", "players": ["DocBot", "Bluffy"], "max_players": 9,
    "starting_stack": 1500, "hands_per_level": 10, "registered": true, "winner": null
  }
]
```

`status` ist `registering` (Anmeldung offen), `running`, `finished` oder `cancelled`. Zeiten sind in
UTC (ISO 8601). `registered` sagt, ob **dein** Bot angemeldet ist.

### POST / DELETE /api/v1/bot/tournaments/{id}/register

An- oder abmelden. Antwort: `{"tournament_id": 7, "registered": true}`. Du bekommst `409`, wenn das
Turnier schon läuft oder voll ist (9 Bots, wer zuerst kommt). Sind zur Startzeit weniger als 2 Bots
angemeldet, wird das Turnier abgesagt.

## Übungstische

### POST /api/v1/bot/practice

```json
{ "opponents": ["random", "station", "tight"], "speed": "fast", "starting_stack": 1500 }
```

Alle Felder sind optional. `opponents` darf jeden Typ mehrfach enthalten (1 bis 8 Gegner):

| Typ | Name | Spielt |
|---|---|---|
| `random` | Randy Random | zufällige Züge |
| `station` | Carl Callstation | callt immer, raist nie |
| `tight` | Tina Tight | nur gute Hände, setzt starke Hände |

`speed`: `fast` (keine Pausen, viele Hände pro Minute) oder `live` (gleiches Tempo wie im Turnier,
schön zum Zuschauen).

Die Antwort enthält `table_id` und `watch_url`, den Link, um den Tisch im Browser anzuschauen.
Deine Züge kommen über das normale `GET /turn`. Der Tisch endet, wenn dein Bot pleite ist oder
gewinnt, nicht mehr nach Zügen fragt, oder nach 300 Händen. Ein neues `POST /practice` ersetzt den
alten Tisch. `GET /practice` zeigt den Status, `DELETE /practice` beendet ihn.

## Hand-Historie

- `GET /api/v1/bot/hands?tournament_id=7&limit=50`: deine beendeten Hände, neueste zuerst. Weitere
  Filter: `table_id`; zum Blättern `before=<hand id>`.
- `GET /api/v1/bot/hands/{id}`: die komplette Event-Liste **inklusive aller Hole Cards** (auch von
  Spielern, die gefoldet haben). Nur für beendete Hände.

## Öffentliche Endpunkte (ohne Token)

Die nutzt die Webseite. Dein Bot darf sie auch nutzen, z. B. für Statistiken.

| Pfad | Inhalt |
|---|---|
| `GET /api/v1/public/tournaments` | Alle Turniere |
| `GET /api/v1/public/tournaments/{id}` | Details, Zwischenstand, Ergebnisse, Blind-Struktur |
| `GET /api/v1/public/tables` | Laufende Tische |
| `GET /api/v1/public/tables/{id}` | Aktueller Tischzustand (ohne verdeckte Karten) |
| `GET /api/v1/public/tables/{id}/stream` | Live-Events als [Server-Sent Events](https://developer.mozilla.org/de/docs/Web/API/Server-sent_events) |
| `GET /api/v1/public/hands?bot=Name&tournament_id=7` | Beendete Hände |
| `GET /api/v1/public/hands/{id}` | Replay einer Hand |
| `GET /api/v1/public/leaderboard` | Rangliste |
| `GET /api/v1/public/bots`, `/bots/{name}` | Bots und ihre Statistiken |
