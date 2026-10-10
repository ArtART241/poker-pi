# Spielablauf & Timeouts

Diese Seite beschreibt den zeitlichen Ablauf des Spiels: wie schnell es läuft, wie viel Zeit ein Bot
für eine Entscheidung hat und was geschieht, wenn ein Bot langsam ist, abstürzt oder die Verbindung
verliert.

## Empfohlene Struktur eines Bots

```
Token prüfen:                 GET  /api/v1/bot/me
(optional) anmelden:          GET  /api/v1/bot/tournaments → POST .../register
Endlosschleife:
    try:
        r = GET /api/v1/bot/turn?wait=25        (Client-Timeout: 40 s)
    bei Netzwerkfehler:
        Fehler ausgeben, 2 s warten, weiter
    falls r.status == 204: weiter               (keine Entscheidung fällig, erneut fragen)
    falls r.status != 200: r.body ausgeben, 2 s warten, weiter
    state  = r.body parsen
    action = decide(state)                      ← die eigene Logik des Bots
    r = POST /api/v1/bot/action {turn_id, ...action}
    falls r.status == 422:                      (ungültiger Zug: Grund ausgeben, sicher spielen)
        POST /api/v1/bot/action {turn_id, "check" falls legal.check sonst "fold"}
```

Alles außer `decide` ist Infrastruktur, die selten angepasst werden muss.

## Bedenkzeit: 15 Sekunden

Ab dem Öffnen eines Zuges hat ein Bot **15 Sekunden** Zeit (`deadline_ms` enthält die verbleibenden
Millisekunden). Das genügt für die meisten Strategien, einschließlich mehrerer tausend
Monte-Carlo-Simulationen.

Trifft keine Antwort rechtzeitig ein:

1. Der Server handelt für den Bot: **check**, wenn möglich, sonst **fold**. Ein
   `player_status`-Event mit `"status": "timeout"` wird protokolliert.
2. Nach **3 Timeouts in Folge** ist der Bot **sitting out**. Er bleibt im Turnier, zahlt weiterhin
   Blinds und Antes und wird automatisch gefoldet; der Server wartet dann aber nur noch
   **3 Sekunden** statt 15. Sobald der Bot einen Zug rechtzeitig beantwortet, ist er wieder dabei
   (`"status": "back"`).

Ein abgestürzter Bot verliert dadurch langsam Chips, hält das Spiel aber nie auf.

## Getrennte Bots

Hat der Server **60 Sekunden** lang **keinen Request** eines Bots erhalten, gilt dieser als
**disconnected**. Der Server wartet dann nicht mehr und checkt oder foldet sofort. Der nächste
Request des Bots (z. B. `GET /turn`) markiert ihn wieder als verbunden.

Die Webseite zeigt den Verbindungsstatus mit einem grünen Punkt auf der Bots-Seite und einem Label am Tisch.

> Ein Bot sollte **vor dem Turnierstart** laufen und pollen. Ein Bot, der zu Beginn nicht verbunden
> ist, spielt seine ersten Hände auf Autopilot (check/fold).

## Tempo: warum Turniere absichtlich langsam sind

Bots entscheiden in Millisekunden, was für Zuschauer zu schnell ist. Im Turnier wartet der Server daher:

- mindestens **2 Sekunden** zwischen zwei Aktionen,
- **1,5 Sekunden**, bevor Flop, Turn und River ausgeteilt werden und bevor der Pot vergeben wird,
- **4 Sekunden** zwischen zwei Händen.

Diese Pausen verkürzen die Bedenkzeit **nicht**. Ein Zug öffnet sofort, und seine 15 Sekunden laufen
direkt los; eine Antwort nach 50 ms wird lediglich zurückgehalten, bis die 2 Sekunden vergangen
sind. Auf Seiten des Bots ist dafür nichts zu tun; `GET /turn` antwortet nur etwas später.

Übungstische mit `"speed": "fast"` haben keine Pausen.

## Fehler und Wiederholungen

| Situation | Vorgehen |
|---|---|
| Netzwerkfehler / Timeout beim Warten auf einen Zug | 1 bis 2 Sekunden warten, dann erneut fragen. Züge gehen nicht verloren: Ein offener Zug wird beim nächsten `GET /turn` sofort geliefert. |
| Netzwerkfehler beim Senden einer Aktion | **Dieselbe** Aktion erneut senden. Duplikate werden erkannt und akzeptiert. |
| `422` | `detail` ausgeben, dann eine sichere Aktion (check/fold) senden. Der Zug ist noch offen. |
| `409` | Der Zug ist vorbei; mit dem nächsten `GET /turn` fortfahren. |
| `401` | Ungültiger Token; Wiederholen hilft nicht. |
| `429` | Zu viele Requests ohne Wirkung, meist eine Schleife ohne `wait`. Eine Sekunde pausieren. |
| `5xx` | Serverproblem. Einige Sekunden warten und fortfahren. |

## Rate-Limit

Jeder Bot darf höchstens **60 unproduktive Requests pro Sekunde** senden: Requests ohne Wirkung,
etwa ein leeres `GET /turn` (die `204`-Antwort) oder ein fehlschlagender Request. Requests, die einen
Zug liefern oder eine angenommene Aktion übermitteln, zählen nicht. Ein schneller Bot an einem
schnellen Übungstisch wird daher nie gebremst. Das Limit erreicht nur eine fehlerhafte Schleife,
z. B. `/turn` mit `wait=0` ohne Pause oder eine abgelehnte Aktion, die immer wieder gesendet wird.

## Mehrere Tische gleichzeitig

Ein Bot kann gleichzeitig an einem Turniertisch und einem Übungstisch sitzen. `GET /turn` liefert
den dringendsten offenen Zug von beliebigen Tischen; `table_id` / `tournament_id` im Zustand
bezeichnen den Tisch. Um Tische zu trennen, können zwei Schleifen laufen, jede mit `?table_id=...`.

<details>
<summary>Warum gibt es keine Websocket- oder Push-API für Bots?</summary>

Long-Polling funktioniert mit jeder HTTP-Bibliothek, passiert Firewalls und Proxys und benötigt
weder Threads noch async-Code. Bots treffen höchstens alle paar Sekunden eine Entscheidung; ein
Push-Kanal würde nichts beschleunigen.

(Zuschauer im Browser erhalten einen Push-Stream per Server-Sent Events, der jedoch keine
Informationen über das hinaus enthält, was Bots ohnehin bekommen.)
</details>
