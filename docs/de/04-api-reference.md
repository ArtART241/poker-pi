# API-Referenz

Basis-URL: `https://poker.example.com`. Alle Bodies sind JSON (`Content-Type: application/json`).

Jeder Endpunkt unter `/api/v1/bot/` erfordert den Header

```
Authorization: Bearer <token>
```

Eine interaktive Fassung dieser Seite, in der sich jeder Request ausprobieren lässt, ist die
[Swagger UI](https://poker.example.com/docs). Die maschinenlesbare Spezifikation liegt unter
[/openapi.yaml](https://poker.example.com/openapi.yaml) (OpenAPI 3.1).

<details>
<summary>Einen Client aus der Spezifikation erzeugen</summary>

Die Spezifikation eignet sich für Client-Generatoren wie OpenAPI Generator; getestet wurde sie mit
den Generatoren `dart` und `dart-dio`. Jede Antwort ist ein benannter Typ, und alle Felder, die `null`
sein können, sind als optional deklariert. Solche Felder sind im JSON dennoch immer vorhanden (mit dem
Wert `null`), mit einer Ausnahme: Events in `action_log` / `events` enthalten nur die Felder, die zu
ihrem `type` gehören.
</details>

## Übersicht

| Methode | Pfad | Zweck |
|---|---|---|
| `GET` | `/api/v1/bot/me` | Identität des Bots; geeignet zum Testen des Tokens. |
| `GET` | `/api/v1/bot/turn?wait=25` | **Auf einen Zug warten** (Long-Poll). |
| `POST` | `/api/v1/bot/action` | **Eine Entscheidung senden.** |
| `GET` | `/api/v1/bot/tournaments` | Kommende, laufende und kürzlich beendete Turniere. |
| `POST` | `/api/v1/bot/tournaments/{id}/register` | Für ein Turnier anmelden. |
| `DELETE` | `/api/v1/bot/tournaments/{id}/register` | Abmelden (vor dem Start). |
| `POST` | `/api/v1/bot/practice` | Übungstisch gegen Haus-Bots starten. |
| `GET` | `/api/v1/bot/practice` | Status des Übungstischs. |
| `DELETE` | `/api/v1/bot/practice` | Übungstisch beenden. |
| `GET` | `/api/v1/bot/hands` | Beendete Hände, an denen der Bot beteiligt war. |
| `GET` | `/api/v1/bot/hands/{id}` | Vollständiger Verlauf einer beendeten Hand (alle Karten). |

## GET /api/v1/bot/turn

Wartet, bis der Bot eine Entscheidung treffen muss, und liefert dann den vollständigen Spielzustand.

| Query-Parameter | Standard | Bedeutung |
|---|---|---|
| `wait` | `25` | Wartezeit in Sekunden (0 bis 30). Passiert in dieser Zeit nichts: `204 No Content`. |
| `table_id` | keiner | Nur auf Züge an diesem Tisch warten (nützlich, wenn ein Bot gleichzeitig an einem Übungstisch *und* in einem Turnier spielt). |

**Antworten:** `200` mit dem unten gezeigten Zustand, oder `204` mit **leerem Body** (keine
Entscheidung fällig; erneut fragen).

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
| `turn_id` | Kennzeichnet diese Entscheidung; sie muss mit der Aktion zurückgeschickt werden. |
| `deadline_ms` | Verbleibende Millisekunden. Danach checkt (wenn möglich) oder foldet der Server für den Bot. |
| `table_id`, `tournament_id`, `practice` | Wo die Hand gespielt wird. `tournament_id` ist an Übungstischen `null`. |
| `hand_id` | Global eindeutige ID der Hand (für `/hands/{id}`). |
| `hand_no` | Nummer der Hand an diesem Tisch: 1, 2, 3, ... |
| `seat` | Platz des Bots, 0 bis 8, im Uhrzeigersinn. |
| `hole_cards` | Die zwei privaten Karten des Bots. |
| `stack` | Chips **dahinter**, ohne bereits gesetzte Chips. |
| `bet` | Auf **dieser Straße** bereits gesetzte Chips. |
| `street` | `preflop`, `flop`, `turn` oder `river`. |
| `board` | Gemeinschaftskarten: 0, 3, 4 oder 5. |
| `pot` | **Alle** Chips in der Mitte, einschließlich aller Einsätze der aktuellen Straße. |
| `current_bet` | Der höchste Einsatz auf dieser Straße. |
| `to_call` | Chips, die ein Call hinzufügen würde (0, wenn Checken möglich ist). |
| `legal.fold` | Immer `true`. |
| `legal.check` | `true`, wenn Checken erlaubt ist. |
| `legal.call` | Chips, die ein Call hinzufügen würde, oder `null`, wenn es nichts zu callen gibt. Kann bei einem kurzen Stack kleiner als `current_bet - bet` sein (All-in-Call). |
| `legal.raise` | `{"min", "max"}` für **Raise auf**, oder `null`, wenn Raisen nicht erlaubt ist. `max` = All-in. |
| `blinds` | Aktueller Small/Big Blind, Ante, Level und Anzahl Hände bis zur nächsten Erhöhung. |
| `button` | Platz des Dealer-Buttons. |
| `players` | Alle Spieler dieser Hand, nach Platz sortiert. `status` ist `active`, `folded` oder `all_in`. `committed` ist der Gesamteinsatz in dieser Hand. |
| `action_log` | Alle öffentlichen Ereignisse dieser Hand in Reihenfolge. |

<details>
<summary>Position relativ zum Button</summary>

Aus `players` (nach Platz sortiert) werden die Platznummern genommen und darin der Index des
Button-Platzes und des eigenen Platzes bestimmt. Bei `n` Spielern gilt:

```
position = (eigener_index - button_index) mod n      0 = Button, 1 = Small Blind, 2 = Big Blind, ...
```

Bei zwei Spielern (Heads-up) ist der Button zugleich der Small Blind.
</details>

## POST /api/v1/bot/action

```json
{ "turn_id": "t_c69e59e7862086fb", "action": "raise", "amount": 120 }
```

| Feld | Bedeutung |
|---|---|
| `turn_id` | Aus `GET /turn`. |
| `action` | `fold`, `check`, `call` oder `raise`. |
| `amount` | Nur bei `raise`: der **Gesamt**einsatz, **auf** den erhöht wird (zwischen `legal.raise.min` und `max`). |

Zusätzlich akzeptiert der Server:
- `"bet"` als Synonym für `raise`,
- `"allin"` / `"all_in"`: Raise auf das Maximum (oder Call, wenn Raisen nicht möglich ist),
- `"call"`, wenn es nichts zu callen gibt: wird als `check` behandelt.

**Antworten:**

| Code | Body | Bedeutung |
|---|---|---|
| `200` | `{"accepted": true, "action": "raise", "amount": 120}` | Angenommen. `action` ist die tatsächlich ausgeführte Aktion (z. B. `check`, wenn `call` ohne offenen Einsatz gesendet wurde). |
| `422` | `{"detail": "raise amount 25 is out of range: raise TO between 40 and 1480"}` | Nicht erlaubt. **Der Zug bleibt offen**; vor Ablauf der Frist kann eine korrigierte Aktion gesendet werden. |
| `409` | `{"detail": "this turn is no longer open ..."}` | Der Zug ist abgelaufen oder wurde bereits anders beantwortet. |
| `403` | `{"detail": "this turn belongs to another bot"}` | Falsche `turn_id`. |

**Exakt denselben** Request zweimal zu senden (etwa als Wiederholung nach einem Netzwerkfehler)
ist unbedenklich und liefert erneut `200`.

> **Fehlerhafte Requests** (Body kein JSON, `turn_id` fehlt, `amount` keine Zahl, ein Query-Parameter
> außerhalb des Bereichs) werden ebenfalls mit `422` und einem einfachen `detail`-String beantwortet,
> z. B. `{"detail": "Invalid request: body.turn_id: Field required"}`.

## Events im `action_log`

Jeder Eintrag hat einen `type`. Platzbezogene Events enthalten außerdem `seat` und `name`. Felder,
die ein Typ nicht verwendet, entfallen.

| `type` | Felder | Bedeutung |
|---|---|---|
| `hand_start` | `hand_id`, `hand_no`, `level`, `button`, `small_blind`, `big_blind`, `ante`, `players[{seat, name, player_id, stack}]` | Eine neue Hand. Stacks *vor* den Blinds. |
| `post` | `blind` (`small` / `big` / `ante`), `amount`, `all_in` | Pflichteinsatz. |
| `action` | `street`, `action`, `amount`, `bet`, `stack`, `all_in`, `pot` | Ein Spieler hat gehandelt. `amount`: hinzugefügte Chips bei `call`, neuer Gesamteinsatz bei `raise`, `null` bei `fold` / `check`. `bet` / `stack` gelten nach der Aktion. |
| `street` | `street`, `cards` (neue Karten), `board` (alle), `pot` | Flop, Turn oder River ausgeteilt. |
| `uncalled` | `amount` | Ein nicht gecallter Teil eines Einsatzes wurde zurückgegeben. |
| `showdown` | `hands[{seat, name, cards}]` | Karten aufgedeckt. Am Ende oder früher, wenn alle All-in sind. |
| `win` | `pot` (0 = Hauptpot, 1+ = Side Pots), `amount`, `winners[{seat, name, amount}]`, `hand` (z. B. `"Two Pair"`, `null` ohne Showdown) | Wer welchen Pot gewonnen hat. |
| `hand_end` | `board`, `results[{seat, name, player_id, start_stack, stack, net, cards}]` | Endergebnis (nur in beendeten Händen). |
| `player_status` | `status`: `timeout`, `sitting_out`, `disconnected`, `connected`, `back` | Änderung der Verbindung eines Bots (siehe [Spielablauf](#/docs/game-loop)). |

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
UTC (ISO 8601). `registered` gibt an, ob der anfragende Bot angemeldet ist.

### POST / DELETE /api/v1/bot/tournaments/{id}/register

An- oder Abmeldung. Antwort: `{"tournament_id": 7, "registered": true}`. Die Antwort ist `409`, wenn
das Turnier bereits läuft oder voll ist (9 Bots, Reihenfolge der Anmeldung). Sind zur Startzeit
weniger als 2 Bots angemeldet, wird das Turnier abgesagt.

## Übungstische

### POST /api/v1/bot/practice

```json
{ "opponents": ["random", "station", "tight"], "speed": "fast", "starting_stack": 1500 }
```

Alle Felder sind optional. `opponents` darf jeden Typ mehrfach enthalten (1 bis 8 Gegner):

| Typ | Name | Spielweise |
|---|---|---|
| `random` | Randy Random | zufällige Züge |
| `station` | Carl Callstation | callt immer, raist nie |
| `tight` | Tina Tight | nur gute Hände, setzt starke Hände |

`speed`: `fast` (keine Pausen, viele Hände pro Minute) oder `live` (Turniertempo, zum Zuschauen geeignet).

Die Antwort enthält `table_id` und `watch_url`, den Link zum Tisch im Browser. Die Züge kommen über
das normale `GET /turn`. Der Tisch endet, wenn der Bot ausscheidet oder gewinnt, keine Züge mehr
abfragt oder nach 300 Händen. Ein neues `POST /practice` ersetzt den alten Tisch.
`GET /practice` zeigt den Status, `DELETE /practice` beendet ihn.

## Hand-Historie

- `GET /api/v1/bot/hands?tournament_id=7&limit=50`: beendete Hände des Bots, neueste zuerst. Weitere
  Filter: `table_id`; zum Blättern `before=<hand id>`.
- `GET /api/v1/bot/hands/{id}`: die vollständige Event-Liste **einschließlich aller Hole Cards**
  (auch von Spielern, die gefoldet haben). Nur für beendete Hände.

## Öffentliche Endpunkte (ohne Token)

Diese nutzt die Webseite; Bots können sie ebenfalls verwenden, z. B. für Statistiken.

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
