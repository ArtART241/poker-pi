# HTTP & REST für Einsteiger

Du kannst programmieren, hast aber noch nie etwas geschrieben, das mit einem Webserver redet? Diese
Seite erklärt alles, was du für poker-pi brauchst, und nicht mehr. Lies sie einmal durch, dann ergibt
der Rest der Doku Sinn.

## HTTP in 60 Sekunden

HTTP ist ein **Request/Response**-Protokoll. Dein Programm (der *Client*) schickt einen **Request**
an einen *Server*, und der Server schickt genau eine **Response** zurück. Das war's. Es gibt keine
dauerhafte Verbindung, um die du dich kümmern musst.

Ein Request besteht aus:

| Teil | Beispiel | Bedeutung |
|---|---|---|
| **Methode** | `GET`, `POST`, `DELETE` | Was du tun willst. `GET` = etwas lesen, `POST` = etwas schicken / etwas auslösen, `DELETE` = etwas entfernen. |
| **URL** | `https://poker.example.com/api/v1/bot/turn?wait=25` | Wohin. Der Teil nach `?` ist der *Query-String*: zusätzliche Parameter als `key=value&key2=value2`. |
| **Header** | `Authorization: Bearer pk_...` | Metadaten als `Name: Wert`-Zeilen, z. B. wer du bist oder welches Format der Body hat. |
| **Body** | `{"turn_id": "t_1", "action": "call"}` | Optionale Daten, meist nur bei `POST`. Hier immer JSON. |

Eine Response besteht aus:

| Teil | Beispiel | Bedeutung |
|---|---|---|
| **Statuscode** | `200`, `204`, `401`, `422` | Eine Zahl, die sagt, wie es gelaufen ist (Tabelle unten). |
| **Header** | `Content-Type: application/json` | Metadaten. |
| **Body** | `{"name": "MeinBot", ...}` | Die eigentliche Antwort, hier immer JSON (oder leer). |

So sieht ein echter Request auf der Leitung aus. Es ist einfach Text:

```http
POST /api/v1/bot/action HTTP/1.1
Host: poker.example.com
Authorization: Bearer pk_3Jk9xQ...
Content-Type: application/json
Content-Length: 46

{"turn_id": "t_3f9a0c1b", "action": "call"}
```

Und die Antwort:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"accepted": true, "action": "call", "amount": null}
```

Das schreibst du nie von Hand. Die HTTP-Bibliothek deiner Sprache baut es für dich. Aber es hilft zu
wissen, dass keine Magie dahintersteckt.

<details>
<summary>Und HTTPS?</summary>

HTTPS ist HTTP in einer verschlüsselten Verbindung (TLS). Deine HTTP-Bibliothek erledigt das
automatisch, wenn die URL mit `https://` beginnt. Du musst nichts tun, außer dass dein System aktuelle
Root-Zertifikate haben sollte. Bei Zertifikatsfehlern schau in die [FAQ](#/docs/faq).
</details>

## Statuscodes, die dir begegnen

| Code | Name | Was er für deinen Bot bedeutet |
|---|---|---|
| `200` | OK | Alles hat geklappt. Der Body enthält die Antwort. |
| `204` | No Content | Hat geklappt, aber es gibt nichts zu berichten. Bei `GET /turn` heißt das *"du bist noch nicht dran, frag nochmal"*. Der Body ist **leer**, also nicht als JSON parsen! |
| `401` | Unauthorized | Token fehlt oder ist falsch. |
| `403` | Forbidden | Du wolltest den Zug eines anderen Bots beantworten. |
| `404` | Not Found | Falsche URL oder unbekannte ID. |
| `409` | Conflict | Der Zug ist vorbei (du warst zu langsam oder hast schon geantwortet). |
| `422` | Unprocessable Entity | Dein Request wurde verstanden, ist aber nicht erlaubt, z. B. ein zu kleiner Raise. Der Body sagt, warum. |
| `429` | Too Many Requests | Du schickst zu viele Requests. Mach langsamer. |
| `5xx` | Server Error | Nicht deine Schuld. Kurz warten und nochmal versuchen. |

Die Faustregel: **2xx = gut, 4xx = dein Request hat ein Problem, 5xx = der Server hat ein Problem.**

> Jede Fehlerantwort von poker-pi hat einen JSON-Body wie `{"detail": "Erklärung"}`.
> **Gib `detail` immer aus, wenn etwas schiefgeht.** Da steht genau drin, was du ändern musst.

## JSON

JSON ist das Textformat für Daten im Web. Wenn du Python-Dicts oder JavaScript-Objekte kennst, kennst
du es schon:

```json
{
  "hole_cards": ["Ah", "Td"],
  "stack": 1480,
  "legal": { "check": false, "call": 20, "raise": { "min": 40, "max": 1500 } },
  "board": []
}
```

- `{ }` ist ein *Objekt* (Map/Dictionary: String-Schlüssel → Werte)
- `[ ]` ist ein *Array* (eine Liste)
- Werte: Strings in `"doppelten Anführungszeichen"`, Zahlen, `true`/`false`, `null`

Jede Sprache kann JSON-Text in native Datenstrukturen umwandeln und zurück:

| Sprache | JSON lesen | JSON schreiben |
|---|---|---|
| Python | `json.loads(text)` → dict | `json.dumps(obj)` |
| JavaScript | `JSON.parse(text)` | `JSON.stringify(obj)` |
| Go | `json.Unmarshal(bytes, &structVar)` | `json.Marshal(v)` |
| Java | kein eingebauter Parser; der Starter-Bot hat einen kleinen dabei, oder Gson/Jackson | |
| C++ | kein eingebauter Parser; der Starter-Bot hat einen kleinen dabei, oder nlohmann/json | |

<details>
<summary>Tipp: null vs. fehlend vs. 0</summary>

Bei poker-pi hat `null` eine Bedeutung. `"call": null` heißt *"es gibt nichts zu callen"* und
`"raise": null` heißt *"du darfst nicht raisen"*. In typisierten Sprachen bildest du das auf
`Optional`, Pointer (`*int` in Go) oder einen Nullable-Typ ab, nicht auf `0`. Sonst wird aus "kann nicht
raisen" ein "raise auf 0", und der Server lehnt das ab.
</details>

## REST

"REST" ist nur ein Stil, HTTP-APIs zu entwerfen. **Dinge** haben URLs (`/tournaments/3`), und die
HTTP-Methode sagt, was du mit ihnen machst:

```
GET    /api/v1/bot/tournaments                 → Turniere auflisten
POST   /api/v1/bot/tournaments/3/register      → für Turnier 3 anmelden
DELETE /api/v1/bot/tournaments/3/register      → von Turnier 3 abmelden
```

Mehr steckt nicht dahinter. Mehr über REST musst du nicht wissen.

## Bearer-Tokens

Der Server muss wissen, **welcher Bot** einen Request schickt. Deshalb trägt jeder Request an
`/api/v1/bot/...` deinen Token in einem Header:

```
Authorization: Bearer pk_3Jk9xQ7mR2...
```

- `Authorization` ist der Header-Name (ein Standard-HTTP-Header).
- `Bearer` heißt *"wer diesen Token trägt (besitzt), darf rein"*. Das ist der Token-Typ.
- Dann genau ein Leerzeichen, dann dein Token.

Das ist der ganze Mechanismus. Kein Login, keine Session, keine Cookies. Jeder Request wird für sich geprüft.

<details>
<summary>Typische Fehler mit dem Token</summary>

- Das Wort `Bearer` (und das Leerzeichen danach) vergessen.
- `Authorisation` geschrieben (britisch). Der Header heißt `Authorization` mit z.
- Token mit Zeilenumbruch oder Leerzeichen am Ende kopiert.
- Token in die URL gepackt (`?token=...`). Das funktioniert nicht, und URLs landen in Logs.
- Token auf GitHub committet. Nimm stattdessen eine Umgebungsvariable.

Wenn du glaubst, dein Token ist rausgekommen, kann der Organisator einen neuen ausstellen (`rotate-token`), und
der alte funktioniert sofort nicht mehr.
</details>

## Long-Polling: warum `GET /turn` "hängt"

Dein Bot muss herausfinden, wann er dran ist. Dafür gibt es drei Wege:

1. **Polling**: alle 100 ms "bin ich dran?" fragen. Einfach, verschwendet aber die Ressourcen des
   Servers, und der Server ist ein Raspberry Pi. Bitte nicht.
2. **Push**: der Server ruft *dein* Programm auf. Dann müsste dein Laptop aus dem Internet erreichbar
   sein, und das ist umständlich.
3. **Long-Polling**: du fragst "bin ich dran?", und der Server **antwortet erst, wenn du es bist**
   (oder nach 25 Sekunden). Sobald du dran bist, bekommst du die Antwort sofort.

poker-pi nutzt **Long-Polling**. Für dich heißt das:

```
Endlosschleife:
    response = GET /api/v1/bot/turn?wait=25      # kann bis zu 25 Sekunden dauern, das ist normal!
    if response.status == 204: continue          # nichts passiert, nochmal fragen
    state = JSON aus response parsen
    action = decide(state)
    POST /api/v1/bot/action  {turn_id, action}
```

> **Wichtig:** Stell den **Timeout deines HTTP-Clients höher als 25 Sekunden**, z. B. 40 s. Manche
> Bibliotheken haben standardmäßig 10 oder 30 Sekunden und würden den Request abbrechen, bevor der
> Server antwortet.

<details>
<summary>Blockiert ein hängender Request nicht mein Programm?</summary>

Ja, der Thread, der den Request schickt, wartet. Genau das willst du: Dein Bot hat nichts anderes zu
tun, solange er nicht dran ist. Du brauchst keine Threads, kein async/await und keine Callbacks. Eine
ganz normale blockierende `while`-Schleife ist perfekt.

Wenn du nebenbei etwas berechnen *willst* (z. B. Tabellen vorberechnen), nimm einen eigenen Thread.
Das ist optional.
</details>

## Im Browser ausprobieren: Swagger UI

Der Server dokumentiert sich selbst. Öffne **[/docs](https://poker.example.com/docs)**:

1. Oben rechts auf **Authorize** klicken, Token einfügen (ohne `Bearer `), bestätigen.
2. Einen Endpunkt aufklappen, z. B. `GET /api/v1/bot/me`, auf **Try it out** und dann **Execute** klicken.
3. Du siehst den genauen Request (als curl-Befehl), den Statuscode und die Antwort.

So verstehst du am schnellsten, was jeder Endpunkt zurückgibt. Die maschinenlesbare Spezifikation
liegt unter [/openapi.yaml](https://poker.example.com/openapi.yaml). Manche Tools erzeugen daraus
Client-Code, für diese API ist das aber übertrieben.

## Nimm die Standardbibliothek

Du brauchst keine Frameworks. Jeder Starter-Bot nutzt nur, was die Sprache mitbringt:

| Sprache | HTTP | JSON |
|---|---|---|
| Python | `urllib.request` (oder `requests`, wenn du magst: `pip install requests`) | `json` |
| Java 11+ | `java.net.http.HttpClient` | nicht eingebaut (im Starter enthalten) |
| Go | `net/http` | `encoding/json` |
| C++ | nicht eingebaut, nimm **libcurl** | nicht eingebaut (im Starter enthalten) |
| JavaScript (Node 18+) | eingebautes `fetch` | eingebautes `JSON` |
| C# | `System.Net.Http.HttpClient` | `System.Text.Json` |
| Rust | Crates `ureq` oder `reqwest` | Crate `serde_json` |
