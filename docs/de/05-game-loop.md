# Spielablauf & Timeouts

Diese Seite erklärt, was im Lauf der Zeit passiert: wie schnell das Spiel läuft, wie lange dein Bot
nachdenken darf und was passiert, wenn er langsam ist, abstürzt oder die Internetverbindung verliert.

## Die empfohlene Bot-Struktur

```
Token prüfen:                 GET  /api/v1/bot/me
(optional) anmelden:          GET  /api/v1/bot/tournaments → POST .../register
Endlosschleife:
    try:
        r = GET /api/v1/bot/turn?wait=25        (Client-Timeout: 40 s)
    bei Netzwerkfehler:
        Fehler ausgeben, 2 s schlafen, continue
    if r.status == 204: continue                (nicht dran, nochmal fragen)
    if r.status != 200: r.body ausgeben, 2 s schlafen, continue
    state  = r.body parsen
    action = decide(state)                      ← dein Code
    r = POST /api/v1/bot/action {turn_id, ...action}
    if r.status == 422:                         (ungültiger Zug: Grund ausgeben, sicher spielen)
        POST /api/v1/bot/action {turn_id, "check" falls legal.check sonst "fold"}
```

Alle Starter-Bots folgen genau dieser Struktur. Du musst nur `decide` ersetzen.

## Bedenkzeit: 15 Sekunden

Ab dem Moment, in dem ein Zug geöffnet wird, hat dein Bot **15 Sekunden** zum Antworten
(`deadline_ms` sagt dir, wie viele Millisekunden übrig sind). Das reicht für die meisten Strategien,
inklusive ein paar tausend Monte-Carlo-Simulationen.

Antwortest du nicht rechtzeitig:

1. Der Server handelt für dich: **check**, wenn möglich, sonst **fold**. Es wird ein
   `player_status`-Event mit `"status": "timeout"` geloggt.
2. Nach **3 Timeouts hintereinander** ist dein Bot **sitting out**. Er bleibt im Turnier, zahlt
   weiter Blinds und Antes und wird automatisch gefoldet, aber der Server wartet nur noch
   **3 Sekunden** statt 15 auf ihn. Sobald dein Bot einen Zug rechtzeitig beantwortet, ist er wieder
   dabei (`"status": "back"`).

Ein abgestürzter Bot verliert also langsam Chips, hält aber nie das Spiel für alle anderen auf.

## Getrennte Bots

Hat der Server **60 Sekunden** lang **gar keinen Request** von deinem Bot bekommen, gilt er als
**disconnected**. Dann wartet der Server überhaupt nicht mehr und checkt oder foldet sofort. Sobald
dein Bot wieder einen Request schickt (z. B. `GET /turn`), ist er wieder verbunden.

Die Webseite zeigt den Verbindungsstatus eines Bots mit einem grünen Punkt auf der Bots-Seite und
einem Label am Tisch.

> **Bevor ein Turnier startet**, stell sicher, dass dein Bot läuft und pollt. Ein Bot, der beim Start
> nicht verbunden ist, spielt seine ersten Hände auf Autopilot (check/fold).

## Tempo: warum Turniere absichtlich langsam sind

Bots entscheiden in Millisekunden, viel zu schnell für menschliche Zuschauer. Im Turnier wartet der
Server deshalb:

- mindestens **2 Sekunden** zwischen zwei Aktionen,
- **1,5 Sekunden**, bevor Flop, Turn und River ausgeteilt werden und bevor der Pot vergeben wird,
- **4 Sekunden** zwischen zwei Händen.

Diese Wartezeit ist **nicht** deine Bedenkzeit. Dein Zug öffnet sofort, und deine 15 Sekunden laufen
direkt los. Antwortest du nach 50 ms, hält der Server deine Aktion einfach fest, bis die 2 Sekunden
um sind. Durch Nachdenken verlierst du also nichts. Dein Bot muss dafür nichts Besonderes tun. Es
heißt nur, dass `GET /turn` manchmal etwas länger braucht.

Übungstische mit `"speed": "fast"` haben gar keine Pausen.

## Fehler und Wiederholungen

| Situation | Was tun |
|---|---|
| Netzwerkfehler / Timeout beim Warten auf einen Zug | 1 bis 2 Sekunden warten, dann nochmal fragen. Züge gehen nicht verloren: Ist dein Zug inzwischen geöffnet worden, liefert das nächste `GET /turn` ihn sofort. |
| Netzwerkfehler beim Senden einer Aktion | **Dieselbe** Aktion nochmal schicken. Duplikate werden erkannt und akzeptiert. |
| `422` | `detail` ausgeben, dann eine sichere Aktion (check/fold) schicken. Der Zug ist noch offen. |
| `409` | Der Zug ist vorbei. Einfach mit dem nächsten `GET /turn` weitermachen. |
| `401` | Falscher Token. Anhalten und reparieren. |
| `429` | Zu viele Requests. Eine Sekunde schlafen. Wahrscheinlich läuft deine Schleife ohne `wait`. |
| `5xx` | Serverproblem. Ein paar Sekunden warten und weitermachen. |

## Rate-Limit

Jeder Bot darf höchstens **60 Requests pro Sekunde** schicken. Ein normaler Bot schickt etwa 2 Requests
pro Entscheidung, du kommst also nie in die Nähe, außer deine Schleife ist kaputt, z. B. wenn du
`/turn` mit `wait=0` ohne Pause in einer Schleife aufrufst.

## Mehrere Tische gleichzeitig

Ein Bot kann gleichzeitig an einem Turniertisch und einem Übungstisch sitzen. `GET /turn` liefert den
dringendsten offenen Zug von irgendeinem Tisch, und `table_id` / `tournament_id` im Zustand sagen dir,
wo er ist. Wenn du die Tische trennen willst, lass zwei Schleifen laufen, jede mit `?table_id=...`.

<details>
<summary>Warum gibt es keine Websocket- / Push-API für Bots?</summary>

Absichtlich, damit es einfach bleibt. Long-Polling funktioniert mit jeder HTTP-Bibliothek in jeder
Sprache, kommt durch jede Firewall und jeden Proxy und braucht weder Threads noch async-Code. Bots
brauchen nicht mehr als eine Entscheidung alle paar Sekunden, ein Push-Kanal würde also nichts schneller machen.

(Zuschauer im Browser bekommen sehr wohl einen Push-Stream, per Server-Sent Events, aber der enthält
keine Information, die dein Bot nicht ohnehin bekommt.)
</details>
