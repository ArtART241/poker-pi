# FAQ

## Requests scheitern mit `401 Unauthorized`

- Der Header muss genau `Authorization: Bearer <token>` lauten: das Wort `Bearer`, ein Leerzeichen,
  der Token.
- Wird der Token aus einer Umgebungsvariable gelesen, muss diese in der Umgebung gesetzt sein, aus
  der der Bot gestartet wird.
- Kopierte Tokens enthalten manchmal ein Leerzeichen oder einen Zeilenumbruch am Ende.
- Ein ersetzter Token (`rotate-token`) funktioniert nicht mehr; der Organisator kann den neuen
  bereitstellen.

## `GET /turn` dauert lange und liefert nichts

Das ist zu erwarten. Der Request wartet bis zu 25 Sekunden auf einen Zug und antwortet mit `204`
(leer), wenn keiner geöffnet wird. Züge gibt es nur, solange der Bot an einem Tisch sitzt:
- **Turnier**: erst nach dem Start (siehe Lobby). Vorher liefert jede Abfrage `204`.
- **Übung**: nach `POST /api/v1/bot/practice`.

`GET /api/v1/bot/me` listet unter `tables` die Tische, an denen der Bot gerade sitzt.

## Der HTTP-Client bricht nach 10 oder 30 Sekunden ab

Der Standard-Timeout des Clients ist kürzer als das Long-Polling. Für `GET /turn` sollte er
mindestens 30 (besser 40) Sekunden betragen, alternativ kann eine kürzere Wartezeit wie `?wait=10`
verwendet werden.

## `422` mit "cannot check"

Ein anderer Spieler hat gesetzt; möglich sind `call`, `raise` oder `fold`. `legal.check` zeigt, ob
Checken erlaubt ist.

## `422` mit "raise amount ... is out of range"

`amount` ist der **Gesamt**einsatz auf der aktuellen Straße (Raise *auf*) und muss zwischen
`legal.raise.min` und `legal.raise.max` liegen. Ist `legal.raise` `null`, ist Raisen nicht möglich.

## `422` mit "Invalid request: ..."

Der Request ist fehlerhaft; `detail` nennt das Feld, z. B. `body.turn_id: Field required`. Der Body ist
kein gültiges JSON, oder ein Feld fehlt bzw. hat den falschen Typ. Typische Ursachen sind ein fehlender Header
`Content-Type: application/json`, von Hand zusammengesetztes JSON mit Syntaxfehler oder `amount` als
Kommazahl bzw. als String mit Leerzeichen.

## `409 Conflict`

Der Zug ist vorbei: Er wurde bereits beantwortet, oder die 15 Sekunden sind verstrichen. Der Bot kann
einfach mit dem nächsten `GET /turn` fortfahren. Tritt das häufig auf, lohnt es sich, die Laufzeit von
`decide` zu messen.

## `429 Too Many Requests`

Der Bot sendet mehr als 60 Requests pro Sekunde ohne Wirkung (leere Abfragen oder Fehler),
vermutlich durch `/turn` mit `wait=0` in einer Schleife oder durch Wiederholungen nach Fehlern ohne
Pause. `wait=25` und 1 bis 2 Sekunden Pause nach Fehlern vermeiden das.

## `403`, `1020` oder eine HTML-Seite statt JSON

Die Seite wird über Cloudflare ausgeliefert, das gelegentlich Requests blockiert, die wie
Angriffswerkzeuge aussehen. Ein aussagekräftiger `User-Agent`-Header hilft meist. Besteht das Problem
weiter, sollte der Organisator erfahren, welche HTTP-Bibliothek verwendet wird.

## Zertifikatsfehler

- Manche Laufzeitumgebungen bringen einen eigenen, möglicherweise veralteten Zertifikatsspeicher
  mit; ein Update der Laufzeit oder ihres Zertifikatspakets behebt das meist.
- Netzwerke mit TLS-abfangenden Proxys (manche Firmen- oder Hochschulnetze) können ebenfalls die
  Ursache sein; ein anderes Netz hilft, das zu bestätigen.
- Die Zertifikatsprüfung abzuschalten ist keine Lösung.

## Der Bot funktioniert lokal, aber nicht gegen den Server

- `POKER_URL` (oder das Äquivalent) sollte `https://poker.example.com` lauten, mit `https` und
  ohne `/api` am Ende.
- `curl https://poker.example.com/api/v1/health` sollte auf demselben Rechner
  `{"status":"ok"}` liefern.
- Hinter einem Proxy beachten die meisten HTTP-Bibliotheken die Umgebungsvariable `HTTPS_PROXY`.

## Log-Ausgaben erscheinen verzögert oder gar nicht

Viele Laufzeitumgebungen puffern die Standardausgabe, wenn sie in eine Datei oder Pipe umgeleitet
wird. Ein Flush nach jeder Zeile oder Zeilenpufferung lässt die Ausgabe sofort erscheinen.

## Warum sind die Karten der Gegner nicht sichtbar?

Poker ist ein Spiel mit verdeckten Informationen. Gegnerkarten erscheinen im `showdown`-Event am Ende
einer Hand und anschließend in der vollständigen Hand-Historie (`GET /api/v1/bot/hands/{id}`), nie
während einer Hand.

## Sind Machine Learning, LLMs oder große Lookup-Tabellen erlaubt?

Ja, solange der Bot innerhalb von 15 Sekunden antwortet und auf eigener Hardware läuft. Training mit
den öffentlichen Hand-Historien ist erlaubt.

## Kann eine Person mehrere Bots betreiben?

Mehrere Bots pro Person sind möglich (jeder benötigt einen eigenen Token), aber nur **ein Bot pro
Person und Turnier**, und Bots dürfen nicht zusammenarbeiten.

## Was passiert, wenn ein Bot während eines Turniers abstürzt?

Seine Chips bleiben am Tisch. Solange er fehlt, checkt oder foldet der Server für ihn, und er zahlt
weiter Blinds. Sobald er wieder pollt, spielt er normal weiter. Ein schneller Neustart begrenzt die
Verluste.

## Was passiert, wenn der Server neu startet?

Laufende Turniere setzen bei der letzten abgeschlossenen Hand fort. Die zu diesem Zeitpunkt laufende
Hand wird mit den Stacks von ihrem Beginn neu gespielt. Bots müssen lediglich weiter pollen.

## Wo lassen sich vergangene Hände eines Bots ansehen?

- Auf der Webseite unter **Bots → Name**, mit einem Replay für jede Hand.
- Über die API mit `GET /api/v1/bot/hands`.
- In den eigenen Logs des Bots.

## Fehler und Vorschläge melden

Fehler und Ideen können dem Organisator gemeldet oder als Issue bzw. Pull Request im Repository
eingereicht werden.
