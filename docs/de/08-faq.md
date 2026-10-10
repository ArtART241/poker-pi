# FAQ & Fehlersuche

## Mein Bot bekommt `401 Unauthorized`

- Ist der Header genau `Authorization: Bearer <token>`? Das Wort `Bearer`, ein Leerzeichen, dann der Token.
- Ist die Umgebungsvariable **im selben Terminal** gesetzt, in dem du den Bot startest? Prüf mit
  `echo $POKER_TOKEN` (PowerShell: `echo $env:POKER_TOKEN`).
- Beim Kopieren keine zusätzlichen Leerzeichen oder Zeilenumbrüche erwischt?
- Wurde dein Token ersetzt (`rotate-token`)? Dann funktioniert der alte nicht mehr. Frag den Organisator.

## `GET /turn` dauert ewig und liefert dann nichts

Das ist richtig so! Es wartet bis zu 25 Sekunden auf deinen Zug und antwortet mit `204` (leer), wenn
nichts passiert. Dein Bot bekommt nur Züge, wenn er an einem Tisch sitzt:
- **Turnier**: erst, wenn es gestartet ist. Schau in die Lobby. Vorher bekommst du nur `204`s.
- **Übung**: starte eine mit `POST /api/v1/bot/practice` (oder `python3 bot.py practice`).

`GET /api/v1/bot/me` zeigt unter `tables`, wo dein Bot gerade sitzt.

## Meine HTTP-Bibliothek bricht nach 10/30 Sekunden ab

Ihr Standard-Timeout ist kürzer als das Long-Polling. Setz ihn für `GET /turn` auf mindestens **30,
besser 40 Sekunden**, oder nimm ein kürzeres Warten wie `?wait=10`.

## `422` mit "cannot check"

Jemand hat gesetzt, du musst also `call`, `raise` oder `fold`. Schau auf `legal.check`.

## `422` mit "raise amount ... is out of range"

Denk dran, es ist **Raise AUF**: `amount` ist dein *Gesamt*einsatz auf dieser Straße. Nimm einen Wert
zwischen `legal.raise.min` und `legal.raise.max`. Wenn `legal.raise` `null` ist, darfst du gar nicht raisen.

## `422` mit `"type": "missing"` oder `"json_invalid"`

Der Body ist kein gültiges JSON, oder ein Feld fehlt. Typische Ursachen:
- `Content-Type: application/json` vergessen,
- JSON von Hand zusammengebaut, mit Tippfehler (nimm deine JSON-Bibliothek!),
- `amount` als String mit Leerzeichen oder als Kommazahl geschickt.

## `409 Conflict`

Der Zug ist vorbei: Dein Bot war zu langsam (über 15 s) oder hat schon geantwortet. Einfach mit dem
nächsten `GET /turn` weitermachen. Wenn das oft passiert, miss, wie lange `decide` braucht.

## `429 Too Many Requests`

Dein Bot schickt mehr als 60 Requests pro Sekunde, die nichts bewirken (leere Abfragen oder Fehler).
Höchstwahrscheinlich rufst du `/turn` mit `wait=0` in einer Schleife auf, oder du wiederholst nach
einem Fehler ohne Pause. Nimm `wait=25` und schlafe
nach Fehlern 1 bis 2 s.

## `403` / `1020` / eine HTML-Seite statt JSON

Die Seite liegt hinter Cloudflare, und das blockt manchmal Requests, die wie Angriffs-Tools aussehen.
Setz einen eigenen `User-Agent`-Header (die Starter-Bots tun das: `poker-pi-starter-bot/1.0`). Wenn es
weiter passiert, sag dem Organisator, welche Sprache/Bibliothek du nutzt.

## SSL- / Zertifikatsfehler

- **Python auf macOS** (python.org-Installer): *"Install Certificates.command"* in
  `/Programme/Python 3.x/` ausführen.
- **Java**: JDK aktualisieren. Sehr alte Versionen haben keine aktuellen Root-Zertifikate.
- **Firmen-/Uni-Netz** mit TLS-abfangendem Proxy: ein anderes Netz probieren (z. B. Handy-Hotspot).
- Schalte niemals die Zertifikatsprüfung ab, "damit es geht". Behebe die eigentliche Ursache.

## Lokal läuft mein Bot, gegen den echten Server nicht

- Ist `POKER_URL` wirklich `https://poker.example.com` (mit `https`, ohne `/api` am Ende)?
- Funktioniert `curl https://poker.example.com/api/v1/health` auf dem Rechner?
- Sitzt du hinter einem Proxy? Dann `HTTPS_PROXY` setzen (die meisten Bibliotheken beachten das).

## Ich sehe keine Ausgabe von meinem Bot

Ausgaben in Dateien/Pipes werden oft gepuffert. Python: `python3 -u bot.py`. C++: `std::cout << std::unitbuf`
oder `std::endl`. Java und Node geben sofort aus.

## Warum sehe ich die Karten meiner Gegner nicht?

Poker ist ein Spiel mit verdeckten Informationen. Gegnerkarten siehst du im `showdown`-Event am Ende
einer Hand und hinterher in der kompletten Hand-Historie (`GET /api/v1/bot/hands/{id}`). Nie während einer Hand.

## Darf mein Bot Machine Learning / ein LLM / eine riesige Lookup-Tabelle nutzen?

Ja, solange er innerhalb von 15 Sekunden antwortet und auf deiner eigenen Hardware läuft. Training mit
den öffentlichen Hand-Historien ist erlaubt und erwünscht.

## Darf ich zwei Bots laufen lassen?

Du darfst mehrere Bots besitzen (frag nach weiteren Tokens), aber nur **ein Bot pro Person und
Turnier**, und Bots dürfen nicht zusammenarbeiten.

## Mein Bot ist mitten im Turnier abgestürzt!

Schnell neu starten. Deine Chips sind noch da. Solange dein Bot weg ist, checkt oder foldet der Server
für ihn, und er zahlt weiter Blinds. Sobald er wieder nach einem Zug fragt, spielt er ganz normal weiter.

## Was passiert, wenn der Server neu startet?

Laufende Turniere machen automatisch bei der letzten abgeschlossenen Hand weiter. Die Hand, die gerade
lief, wird mit den Stacks von vor ihrem Beginn neu gespielt. Dein Bot pollt einfach weiter.

## Wo sehe ich, was mein Bot gemacht hat?

- Auf der Webseite: **Bots → dein Bot**, mit allen Händen und einem Replay für jede.
- Per API: `GET /api/v1/bot/hands`.
- In deinen eigenen Logs (empfohlen!).

## Ich hab einen Bug gefunden / eine Idee

Sag dem Organisator Bescheid, oder mach ein Issue oder einen Pull Request im Repository. Server-Bugs sind keine Strategie.
