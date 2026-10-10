# HTTP-Grundlagen

Diese Seite fasst die Web-Konzepte zusammen, die ein Bot benötigt: HTTP-Requests und -Responses,
JSON, Statuscodes, Bearer-Tokens und Long-Polling. Wer REST-APIs kennt, kann sie überspringen.

## Requests und Responses

HTTP ist ein Request/Response-Protokoll. Ein Client sendet einen **Request** an einen Server und
erhält genau eine **Response**. Eine dauerhafte Verbindung muss nicht verwaltet werden.

Ein Request besteht aus:

| Teil | Beispiel | Bedeutung |
|---|---|---|
| **Methode** | `GET`, `POST`, `DELETE` | Art der Operation: `GET` liest, `POST` sendet Daten oder löst etwas aus, `DELETE` entfernt. |
| **URL** | `https://poker.example.com/api/v1/bot/turn?wait=25` | Das Ziel. Der Teil nach `?` ist der *Query-String* mit Parametern als `key=value&key2=value2`. |
| **Header** | `Authorization: Bearer pk_...` | Metadaten als `Name: Wert`-Zeilen, z. B. Zugangsdaten oder das Body-Format. |
| **Body** | `{"turn_id": "t_1", "action": "call"}` | Optionale Nutzdaten, meist nur bei `POST`. Bei poker-pi immer JSON. |

Eine Response besteht aus einem **Statuscode** (z. B. `200`), **Headern** und einem optionalen **Body**.

Auf der Leitung ist beides reiner Text:

```http
POST /api/v1/bot/action HTTP/1.1
Host: poker.example.com
Authorization: Bearer pk_3Jk9xQ...
Content-Type: application/json
Content-Length: 46

{"turn_id": "t_3f9a0c1b", "action": "call"}
```

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"accepted": true, "action": "call", "amount": null}
```

HTTP-Bibliotheken erzeugen und lesen diese Nachrichten; von Hand geschrieben werden sie nie.

<details>
<summary>HTTPS</summary>

HTTPS ist HTTP innerhalb einer verschlüsselten TLS-Verbindung. HTTP-Bibliotheken erledigen das für
`https://`-URLs automatisch, sofern das System aktuelle Root-Zertifikate hat. Zertifikatsfehler
behandelt die [FAQ](#/docs/faq).
</details>

## Statuscodes

| Code | Name | Bedeutung bei poker-pi |
|---|---|---|
| `200` | OK | Erfolg; der Body enthält das Ergebnis. |
| `204` | No Content | Erfolg ohne Inhalt. Bei `GET /turn`: noch keine Entscheidung fällig, erneut fragen. Der Body ist **leer** und darf nicht als JSON geparst werden. |
| `401` | Unauthorized | Token fehlt oder ist ungültig. |
| `403` | Forbidden | Versuch, den Zug eines anderen Bots zu beantworten. |
| `404` | Not Found | Unbekannte URL oder ID. |
| `409` | Conflict | Der Zug ist vorbei (schon beantwortet oder abgelaufen). |
| `422` | Unprocessable Entity | Der Request ist verständlich, aber nicht erlaubt, z. B. ein Raise unter dem Minimum. Der Body nennt den Grund. |
| `429` | Too Many Requests | Zu viele Requests ohne Wirkung; der Client sollte langsamer werden. |
| `5xx` | Server Error | Ein Problem auf dem Server; ein erneuter Versuch nach kurzer Pause ist sinnvoll. |

Faustregel: **2xx** Erfolg, **4xx** ein Problem mit dem Request, **5xx** ein Problem auf dem Server.

Jede Fehlerantwort von poker-pi hat einen JSON-Body der Form `{"detail": "Erklärung"}`. `detail`
zu protokollieren ist der schnellste Weg zur Ursache eines Problems.

## JSON

JSON ist das Datenformat aller Bodies:

```json
{
  "hole_cards": ["Ah", "Td"],
  "stack": 1480,
  "legal": { "check": false, "call": 20, "raise": { "min": 40, "max": 1500 } },
  "board": []
}
```

- `{ }` ist ein Objekt (String-Schlüssel mit Werten), `[ ]` ein Array.
- Werte sind Strings in doppelten Anführungszeichen, Zahlen, `true` / `false` oder `null`.

Nahezu jede Sprache bietet einen JSON-Parser, eingebaut oder als Standardpaket, der diesen Text in
native Maps/Listen oder typisierte Strukturen umwandelt und zurück.

<details>
<summary>null hat eine Bedeutung</summary>

Bei poker-pi trägt `null` Information: `"call": null` heißt, es gibt nichts zu callen, und
`"raise": null` heißt, Raisen ist nicht erlaubt. In statisch typisierten Sprachen entsprechen diese
Felder einem Optional- oder Nullable-Typ. Eine Abbildung auf `0` würde aus "kann nicht raisen"
ein "raise auf 0" machen, was der Server ablehnt.
</details>

## REST

REST bezeichnet einen Stil von HTTP-APIs, bei dem Ressourcen URLs haben und die Methode die
Operation ausdrückt:

```
GET    /api/v1/bot/tournaments                 → Turniere auflisten
POST   /api/v1/bot/tournaments/3/register      → für Turnier 3 anmelden
DELETE /api/v1/bot/tournaments/3/register      → von Turnier 3 abmelden
```

## Bearer-Tokens

Jeder Request an `/api/v1/bot/...` identifiziert den Bot über einen Header:

```
Authorization: Bearer pk_3Jk9xQ7mR2...
```

`Authorization` ist ein Standard-HTTP-Header; `Bearer` ist der Token-Typ ("wer diesen Token trägt,
ist berechtigt"), gefolgt von genau einem Leerzeichen und dem Token. Es gibt weder Login noch
Session: Jeder Request wird für sich geprüft.

<details>
<summary>Häufige Fehler</summary>

- Das Wort `Bearer` oder das Leerzeichen danach fehlt.
- Der Header ist `Authorisation` statt `Authorization` geschrieben.
- Der kopierte Token enthält ein Leerzeichen oder einen Zeilenumbruch am Ende.
- Der Token wird in der URL übergeben (`?token=...`); das wird nicht unterstützt, und URLs landen
  häufig in Logs.
</details>

## Long-Polling

Ein Bot muss erfahren, wann er an der Reihe ist. Drei Ansätze sind verbreitet:

1. **Polling**: wiederholtes Fragen, z. B. alle 100 ms. Einfach, aber belastend für den Server.
2. **Push**: Der Server ruft den Bot auf. Dazu müsste der Bot aus dem Internet erreichbar sein.
3. **Long-Polling**: Der Bot fragt, und der Server hält die Anfrage offen, bis es etwas zu melden
   gibt oder ein Timeout erreicht ist. Die Antwort kommt, sobald der Zug geöffnet wird.

poker-pi verwendet Long-Polling. `GET /api/v1/bot/turn?wait=25` kann bis zu 25 Sekunden dauern;
das ist das erwartete Verhalten. Daraus folgt:

- Der **Timeout des HTTP-Clients muss länger als die Wartezeit sein**, zum Beispiel 40 Sekunden.
  Manche Bibliotheken verwenden standardmäßig 10 oder 30 Sekunden.
- Eine einfache blockierende Schleife genügt. Threads, async-Code oder Callbacks sind nicht nötig.
