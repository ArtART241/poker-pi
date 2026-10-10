# Erste Schritte

poker-pi veranstaltet No-Limit-Texas-Hold'em-Turniere, in denen jeder Spieler ein Programm ist.
Jede Teilnehmerin und jeder Teilnehmer schreibt einen Bot, der sich per HTTP mit dem Server
verbindet, bei jeder anstehenden Entscheidung den Spielzustand erhält und mit einer Aktion
antwortet: Fold, Check, Call oder Raise. Zuschauer verfolgen die Spiele live im Browser.

Jede Programmiersprache ist geeignet, sofern sie HTTP-Requests senden sowie JSON lesen und
schreiben kann. Der Server macht keine Annahmen darüber, wie ein Bot umgesetzt ist.

> Die Dokumentation setzt allgemeine Programmiererfahrung voraus, aber keine Kenntnisse in
> Webentwicklung. [HTTP-Grundlagen](#/docs/web-basics) erläutert die wenigen benötigten Konzepte.

## Voraussetzungen

1. **Ein Bot-Token.** Der Organisator stellt pro Bot einen aus. Es handelt sich um eine lange
   geheime Zeichenkette wie `pk_3Jk9...`, die den Bot identifiziert und wie ein Passwort zu
   behandeln ist.
2. **Ein HTTP-Client und eine JSON-Bibliothek** in der gewählten Sprache. Die meisten Sprachen
   bringen beides in der Standardbibliothek oder in einem verbreiteten Paket mit.
3. **Ein Rechner, der online bleibt**, solange ein Turnier läuft. Ein Laptop, ein Raspberry Pi
   oder ein kleiner Server sind gleichermaßen geeignet.

Server-Adresse:

```
https://poker.example.com
```

## Funktionsweise eines Bots

Ein Bot wiederholt zwei Requests, solange er läuft:

```
   Bot                                           Poker-Server
    |                                                 |
    |  GET /api/v1/bot/turn?wait=25  ---------------> |   steht eine Entscheidung an?
    |                                                 |   (die Anfrage bleibt offen, bis
    |                                                 |    der Bot an der Reihe ist, max. 25 s)
    | <---------------  200 OK + Spielzustand (JSON)  |
    |                                                 |
    |  POST /api/v1/bot/action  ---------------------> |   {"turn_id": "...", "action": "call"}
    | <---------------  200 OK                        |
    |                                                 |
    |  GET /api/v1/bot/turn?wait=25  ---------------> |   ...und so weiter
```

Steht innerhalb von 25 Sekunden keine Entscheidung an, antwortet der Server mit
**204 No Content** (einer leeren Antwort), und der Bot fragt erneut. Das ist das gesamte
Protokoll; alles Weitere ist optional.

Als Pseudocode:

```
Endlosschleife:
    response = GET /api/v1/bot/turn?wait=25           (Client-Timeout: 40 s)
    falls response.status == 204: weiter
    state  = JSON parsen
    action = decide(state)                             (die eigene Logik des Bots)
    POST /api/v1/bot/action  { "turn_id": state.turn_id, ...action }
```

Jeder Request enthält den Token im Header `Authorization: Bearer <token>`.

## Die API von Hand ausprobieren

Die folgenden Schritte verwenden `curl`, einen HTTP-Client für die Kommandozeile, der unter macOS,
Linux und Windows 10/11 vorhanden ist (in der PowerShell als `curl.exe` aufzurufen). Sie zeigen
genau, was ein Bot mit dem Server austauscht.

**1. Token prüfen.**

```bash
curl -H "Authorization: Bearer pk_TOKEN" https://poker.example.com/api/v1/bot/me
```

Die Antwort enthält den Namen des Bots. `{"detail":"Invalid or revoked token."}` bedeutet, dass
der Token nicht vollständig kopiert wurde.

**2. Übungstisch starten** gegen eingebaute Gegner (Ergebnisse zählen nicht):

```bash
curl -X POST -H "Authorization: Bearer pk_TOKEN" https://poker.example.com/api/v1/bot/practice
```

Die Antwort enthält eine `watch_url`, unter der der Tisch im Browser zu sehen ist.

**3. Nach einem Zug fragen.**

```bash
curl -H "Authorization: Bearer pk_TOKEN" "https://poker.example.com/api/v1/bot/turn?wait=25"
```

Das JSON enthält die Hole Cards, das Board, den Pot und vor allem `legal`: die Züge, die gerade
erlaubt sind.

**4. Aktion senden** mit der `turn_id` aus Schritt 3:

```bash
curl -X POST -H "Authorization: Bearer pk_TOKEN" -H "Content-Type: application/json" \
     -d '{"turn_id": "t_...", "action": "call"}' \
     https://poker.example.com/api/v1/bot/action
```

Eine Entscheidung muss innerhalb von 15 Sekunden eintreffen, sonst checkt oder foldet der Server
für den Bot. Von Hand ist das knapp; der Ablauf dient vor allem dazu, die Daten kennenzulernen.

<details>
<summary>Die verwendeten curl-Optionen</summary>

- `-H "Name: Wert"` fügt einen Request-Header hinzu (hier: den Token und das Body-Format).
- `-X POST` ändert die Methode vom Standard `GET` auf `POST`.
- `-d '...'` sendet den angegebenen Text als Request-Body.
</details>

<details>
<summary>Den Token aus dem Quellcode heraushalten</summary>

Üblich ist, den Token aus einer Umgebungsvariable (zum Beispiel `POKER_TOKEN`) oder aus einer
Konfigurationsdatei zu lesen, die nicht versioniert wird. Wer den Token besitzt, kann als dieser
Bot spielen; er sollte daher nicht in einem öffentlichen Repository landen. Bei einem Leak kann der
Organisator einen neuen Token ausstellen; der alte wird sofort ungültig.
</details>

## Swagger UI

Der Server dokumentiert sich unter [/docs](https://poker.example.com/docs) selbst. Nach einem
Klick auf *Authorize* und Eingabe des Tokens lässt sich jeder Endpunkt mit *Try it out* direkt im
Browser aufrufen; zu jedem Aufruf wird der entsprechende `curl`-Befehl angezeigt. Die
maschinenlesbare Spezifikation liegt unter [/openapi.yaml](https://poker.example.com/openapi.yaml).

## Übung und Turniere

- **Übungstische** (`POST /api/v1/bot/practice`) setzen einen Bot gegen eingebaute Gegner und
  lassen sich jederzeit starten. Sie sind der vorgesehene Weg, einen Bot zu testen.
- **Turniere** werden im Voraus angesetzt und in der Lobby angezeigt. Ein Bot meldet sich mit
  `POST /api/v1/bot/tournaments/{id}/register` an und muss nur beim Turnierstart laufen und pollen.
  Die Züge kommen über dieselbe `GET /turn`-Schleife.

## Hausregeln

- Ein Bot pro Person und Turnier.
- Bots dürfen keine Informationen austauschen oder zusammenarbeiten.
- Der Server ist ein Raspberry Pi: Bots sollten das Long-Polling (`wait=25`) nutzen statt in einer
  engen Schleife zu fragen. Requests ohne Wirkung sind auf 60 pro Sekunde begrenzt.
- Tokens sind persönlich und vertraulich zu behandeln.
- Fehler im Server sollten gemeldet und nicht ausgenutzt werden.

## Weiterführend

- [HTTP-Grundlagen](#/docs/web-basics): Requests, JSON, Statuscodes, Bearer-Tokens und Long-Polling.
- [Pokerregeln](#/docs/poker-rules): Texas Hold'em und das Turnierformat.
- [API-Referenz](#/docs/api-reference): alle Endpunkte und Felder.
- [Spielablauf & Timeouts](#/docs/game-loop): Tempo, Zeitlimits und Fehlerbehandlung.
- [Strategie-Hinweise](#/docs/strategy): Ideen für bessere Entscheidungen.
- [FAQ](#/docs/faq): häufige Fehler und ihre Ursachen.
