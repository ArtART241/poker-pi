# Erste Schritte

Willkommen bei **poker-pi**! Hier spielen keine Menschen Poker, sondern **Programme**, und eins davon
schreibst du. Dein Bot verbindet sich über das Internet mit dem Poker-Server, erfährt, wann er dran ist,
und antwortet mit einem Zug: Fold, Check, Call oder Raise. Alle anderen können die Spiele live im
Browser verfolgen.

Du kannst **jede Programmiersprache** verwenden, die HTTP-Requests verschicken kann: Python, Java, Go,
C++, JavaScript, Rust, C#, Kotlin und so weiter. Wenn deine Sprache mit einer Webseite reden kann,
kann sie hier Poker spielen.

> **Noch nie mit Webprogrammierung zu tun gehabt?** Kein Problem. Die Doku geht davon aus, dass du
> programmieren kannst, aber nicht weißt, wie das Web funktioniert. Die Seite
> [HTTP & REST für Einsteiger](#/docs/web-basics) erklärt alles, was du brauchst. Es ist weniger, als du denkst.

## Was du brauchst

1. **Einen Bot-Token** vom Organisator. Das ist eine lange geheime Zeichenkette wie `pk_3Jk9...`. Er
   identifiziert deinen Bot, wie ein Passwort. Halte ihn geheim.
2. **Eine Programmiersprache** deiner Wahl, auf deinem Rechner installiert.
3. **Einen Rechner, der online bleibt**, während ein Turnier läuft. Dein Laptop reicht, ein
   Raspberry Pi oder ein kleiner Server tut es auch.

Die Server-Adresse ist:

```
https://poker.example.com
```

## Die Idee auf einen Blick

Dein Bot macht nur zwei Dinge, immer wieder:

```
   dein Bot                                      Poker-Server
      |                                               |
      |  GET /api/v1/bot/turn?wait=25  -------------> |   "Bin ich dran?"
      |                                               |   (der Server hält die Anfrage offen,
      |                                               |    bis du dran BIST, max. 25 s)
      | <-------------  200 OK + Spielzustand (JSON)  |   "Ja! Du hast Ah Kd, der Pot ist 60..."
      |                                               |
      |  POST /api/v1/bot/action  -------------------> |   {"turn_id": "...", "action": "call"}
      | <-------------  200 OK                        |   "Angekommen."
      |                                               |
      |  GET /api/v1/bot/turn?wait=25  -------------> |   ...und wieder von vorn
```

Bist du innerhalb von 25 Sekunden nicht dran, antwortet der Server mit **204 No Content** (einer
leeren Antwort). Dann fragst du einfach nochmal. Das ist das ganze Protokoll.

## Schnellstart (10 Minuten)

### Schritt 1: Token testen

Öffne ein Terminal und führe das aus (Token durch deinen ersetzen):

```bash
curl -H "Authorization: Bearer pk_DEIN_TOKEN" https://poker.example.com/api/v1/bot/me
```

Du solltest so etwas wie `{"id":"b_...","name":"DeinBot",...}` sehen. Bekommst du
`{"detail":"Invalid or revoked token."}`, prüf, ob du den ganzen Token kopiert hast.

<details>
<summary>Was ist curl und hab ich das?</summary>

`curl` ist ein kleines Kommandozeilenprogramm, das HTTP-Requests verschickt. Es ist auf macOS, Linux
und Windows 10/11 vorinstalliert (in der PowerShell `curl.exe` statt `curl` tippen, weil `curl` dort
ein Alias für etwas anderes ist).

- `-H "Name: Wert"` fügt dem Request einen **Header** hinzu. Hier schickt er deinen Token mit.
- Ohne `-X` schickt curl einen `GET`-Request.
- `-X POST -d '{"a":1}' -H "Content-Type: application/json"` würde einen POST mit JSON-Body schicken.

Für deinen Bot brauchst du curl nie. Es ist nur praktisch zum Ausprobieren.
</details>

### Schritt 2: Starter-Bot holen

Im Repository liegt im Ordner `bots/` ein fertiger Starter-Bot für **Python, Java, Go, C++ und
JavaScript**. Jeder ist eine einzelne Datei mit rund 150 Zeilen und nutzt nur die Standardbibliothek
(C++ braucht libcurl). Such dir deine Sprache aus und kopier den Ordner.

| Sprache | Datei | Starten mit |
|---|---|---|
| Python 3.8+ | `bots/python/bot.py` | `python3 bot.py` |
| Java 17+ | `bots/java/Bot.java` | `java Bot.java` |
| Go 1.21+ | `bots/go/main.go` | `go run .` |
| C++17 | `bots/cpp/bot.cpp` | `make && ./bot` |
| Node.js 18+ | `bots/javascript/bot.mjs` | `node bot.mjs` |

Die [Sprach-Anleitungen](#/docs/language-guides) erklären das Setup für jede Sprache im Detail.

### Schritt 3: Dem Bot deinen Token geben

Die Starter-Bots lesen zwei **Umgebungsvariablen**:

- `POKER_TOKEN`: dein Token (Pflicht)
- `POKER_URL`: die Server-Adresse (optional, ohne Angabe `http://localhost:8000`)

macOS / Linux:

```bash
export POKER_TOKEN="pk_DEIN_TOKEN"
export POKER_URL="https://poker.example.com"
```

Windows PowerShell:

```powershell
$env:POKER_TOKEN = "pk_DEIN_TOKEN"
$env:POKER_URL = "https://poker.example.com"
```

<details>
<summary>Was ist eine Umgebungsvariable, und warum nicht einfach den Token in den Code schreiben?</summary>

Eine Umgebungsvariable ist ein benannter Wert, der in deiner Terminal-Sitzung lebt. Jedes Programm,
das du aus diesem Terminal startest, kann ihn lesen (`os.environ` in Python, `System.getenv` in Java,
`os.Getenv` in Go, `std::getenv` in C++, `process.env` in Node).

Wenn der Token nicht im Quellcode steht, kannst du deinen Code teilen (etwa auf GitHub), ohne den
Token zu verraten. Wer deinen Token hat, kann **als dein Bot** spielen.

Die Variablen gelten nur, solange das Terminalfenster offen ist. Schreib die `export`-Zeilen in
`~/.zshrc` / `~/.bashrc` (macOS/Linux), damit sie bleiben, oder nutze eine `.env`-Datei, die dein
Programm einliest (und committe sie nicht!).

In einer IDE (IntelliJ, VS Code, CLion, ...) kannst du Umgebungsvariablen in der Run-Configuration setzen.
</details>

### Schritt 4: Gegen Haus-Bots üben

Starte den Bot mit dem Argument `practice`:

```bash
python3 bot.py practice
```

Damit öffnest du einen **privaten Übungstisch** gegen drei eingebaute Bots:

- **Randy Random** spielt zufällig.
- **Carl Callstation** callt alles.
- **Tina Tight** spielt nur gute Hände.

Der Bot gibt einen Link aus wie `https://poker.example.com/#/table/p_ab12cd`. Öffne ihn und
schau deinem Bot beim Spielen zu. Übungsergebnisse zählen für nichts, also probier ruhig alles aus.

### Schritt 5: An einem Turnier teilnehmen

Turniere werden im Voraus angesetzt; du siehst sie in der **Lobby**. Die Starter-Bots melden sich beim
Start automatisch für jedes offene Turnier an und schauen alle 5 Minuten nach neuen. Um mitzuspielen,
lass deinen Bot einfach laufen, bis das Turnier beginnt.

Sobald das Turnier startet, kommen deine Züge über dieselbe `GET /turn`-Schleife. Extra-Code brauchst du nicht.

### Schritt 6: Mach ihn schlau

Öffne den Starter-Bot und such die Funktion `decide(state)`. Das ist die einzige Stelle, die du ändern
musst. Sie bekommt den kompletten Spielzustand und gibt eine Aktion zurück. Die Starter-Strategie ist
absichtlich dumm. In den [Strategie-Tipps](#/docs/strategy) findest du jede Menge Ideen.

## Hausregeln

- **Ein Bot pro Person und Turnier.** Du darfst mehrere Bots haben, aber in jedem Turnier spielt nur
  einer davon mit.
- **Keine Teamarbeit zwischen Bots.** Bots dürfen keine Informationen austauschen oder
  zusammenarbeiten (im Poker heißt das "Collusion").
- **Sei nett zum Server.** Er ist ein Raspberry Pi. Nutz das Long-Polling (`wait=25`) und schick nicht
  hunderte Requests pro Sekunde. Leere Requests sind auf 60 pro Sekunde begrenzt.
- **Halte deinen Token geheim.** Wenn er rauskommt, frag den Organisator nach einem neuen.
- **Bugs im Server** sind keine Strategie. Melde sie, dafür gibt's ewigen Ruhm.

## Wie geht's weiter

- [HTTP & REST für Einsteiger](#/docs/web-basics): Requests, JSON, Statuscodes, Bearer-Tokens und Long-Polling.
- [Pokerregeln](#/docs/poker-rules): wie Texas Hold'em und die Turniere funktionieren.
- [API-Referenz](#/docs/api-reference): alle Endpunkte und Felder.
- [Spielablauf & Timeouts](#/docs/game-loop): was passiert, wenn dein Bot langsam ist oder abstürzt.
- **Swagger UI** unter [/docs](https://poker.example.com/docs): Probier jeden Endpunkt im Browser
  aus. Auf *Authorize* klicken, Token einfügen, dann *Try it out*.
