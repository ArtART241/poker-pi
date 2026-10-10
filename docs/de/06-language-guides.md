# Sprach-Anleitungen

Jeder Starter-Bot macht dasselbe: Token prüfen, für offene Turniere anmelden, dann die Zug-Schleife
laufen lassen. Such dir unten deine Sprache aus. Jeder Abschnitt erklärt Installation, Starten, wie
HTTP und JSON in der Sprache funktionieren und die typischen Stolperfallen.

Alle Starter-Bots lesen `POKER_TOKEN` und `POKER_URL` aus der Umgebung (siehe
[Erste Schritte](#/docs/getting-started)) und akzeptieren `practice` als erstes Argument.

<details>
<summary><b>Python</b> (3.8+, nur Standardbibliothek)</summary>

**Installieren:** macOS: `brew install python` oder der Installer von python.org. Linux: meist
vorinstalliert. Windows: Installer von python.org, dabei *"Add python.exe to PATH"* anhaken.

**Starten:**

```bash
cd bots/python
export POKER_TOKEN="pk_..."
export POKER_URL="https://poker.example.com"
python3 bot.py practice
```

**HTTP:** Der Starter nutzt `urllib.request` aus der Standardbibliothek. Wenn dir
[requests](https://requests.readthedocs.io) lieber ist, das ist etwas angenehmer:

```python
import requests
s = requests.Session()
s.headers["Authorization"] = f"Bearer {TOKEN}"
r = s.get(f"{BASE}/api/v1/bot/turn", params={"wait": 25}, timeout=40)
if r.status_code == 200:
    state = r.json()
    s.post(f"{BASE}/api/v1/bot/action", json={"turn_id": state["turn_id"], "action": "call"}, timeout=10)
```

(`pip install requests`, am besten in einem Virtual Env: `python3 -m venv .venv && source .venv/bin/activate`.)

**Stolperfallen:**
- `urllib` wirft bei 4xx/5xx-Antworten eine Exception (`HTTPError`), statt sie zurückzugeben. Der
  Starter fängt sie ab und liefert trotzdem `(status, body)`.
- Die `204`-Antwort hat einen leeren Body: `json.loads(b"")` stürzt ab. Prüf zuerst den Status.
- `print`-Ausgaben kommen verzögert an, wenn du sie in eine Datei umleitest. Der Starter schaltet
  Zeilenpufferung ein (`sys.stdout.reconfigure(line_buffering=True)`), alternativ `python3 -u`.
- macOS: Bei `CERTIFICATE_VERIFY_FAILED` *"Install Certificates.command"* aus deinem Python-Ordner
  unter Programme ausführen (nur bei python.org-Installationen).

**Nützlich für die Strategie:** `random`, `itertools.combinations`, `collections.Counter`.
Das Paket `treys` (`pip install treys`) bewertet Pokerhände sehr schnell, `eval7` ebenso.
</details>

<details>
<summary><b>Java</b> (17+, keine Bibliotheken)</summary>

**Installieren:** ein JDK 17 oder neuer, z. B. [Adoptium Temurin](https://adoptium.net), oder über deine
IDE (IntelliJ kann eins herunterladen: *File → Project Structure → SDK*). Prüfen mit `java -version`.

**Starten:** Seit Java 11 kannst du eine einzelne Quelldatei direkt starten, ohne Kompilierschritt:

```bash
cd bots/java
export POKER_TOKEN="pk_..."
export POKER_URL="https://poker.example.com"
java Bot.java practice
```

In IntelliJ: Ordner öffnen, Rechtsklick auf `Bot.java` → *Run*, dann die Umgebungsvariablen unter
*Run → Edit Configurations → Environment variables* setzen.

**HTTP:** `java.net.http.HttpClient` (eingebaut seit Java 11):

```java
HttpClient http = HttpClient.newBuilder().version(HttpClient.Version.HTTP_1_1).build();
HttpRequest req = HttpRequest.newBuilder(URI.create(BASE + "/api/v1/bot/turn?wait=25"))
        .header("Authorization", "Bearer " + TOKEN)
        .timeout(Duration.ofSeconds(40))
        .GET().build();
HttpResponse<String> res = http.send(req, HttpResponse.BodyHandlers.ofString());
```

**JSON:** Java hat keinen eingebauten JSON-Parser. Der Starter enthält einen kleinen (Klasse `Json`,
unten in der Datei), der JSON in `Map<String, Object>`, `List<Object>`, `Long`, `Double`, `String`,
`Boolean` und `null` umwandelt. Wenn du Maven/Gradle nutzt, kannst du stattdessen
[Gson](https://github.com/google/gson) oder [Jackson](https://github.com/FasterXML/jackson) nehmen
und den Zustand auf eigene Klassen/Records abbilden.

**Stolperfallen:**
- Nimm `HttpClient.Version.HTTP_1_1`. Der Standard, HTTP/2, versucht über einfaches `http://` ein
  "Upgrade", mit dem manche Server schlecht umgehen (der Body von POST-Requests geht verloren).
- Zahlen aus dem kleinen JSON-Parser sind `Long` (oder `Double`). Nimm `((Number) x).longValue()`,
  nicht `(Integer) x`.
- `legal.raise` kann `null` sein. Prüf das, bevor du `.get("min")` aufrufst.
</details>

<details>
<summary><b>Go</b> (1.21+, nur Standardbibliothek)</summary>

**Installieren:** [go.dev/dl](https://go.dev/dl) oder `brew install go`. Prüfen mit `go version`.

**Starten:**

```bash
cd bots/go
export POKER_TOKEN="pk_..."
export POKER_URL="https://poker.example.com"
go run . practice
```

Oder ein Binary bauen: `go build -o pokerbot .`, dann `./pokerbot`. Mit
`GOOS=linux GOARCH=arm64 go build` kannst du es sogar für einen Raspberry Pi bauen.

**HTTP + JSON:** `net/http` und `encoding/json`. Der Starter definiert Structs für den Zustand
(`State`, `Legal`, `Player`) mit `json:"..."`-Tags, so bekommst du typisierte Felder wie `s.Legal.Raise.Min`.

**Stolperfallen:**
- Nimm einen `http.Client` mit `Timeout` über 25 s (der Starter nimmt 40 s). `http.Get` ohne eigenen
  Client hat nie einen Timeout.
- Felder, die `null` sein können, sind in den Structs Pointer: `Call *int`, `Raise *RaiseRange`.
  Vor der Benutzung auf `!= nil` prüfen.
- Immer `defer resp.Body.Close()`, sonst leakst du Verbindungen.
- Unbekannte Felder im JSON werden einfach ignoriert, du musst also nur deklarieren, was du brauchst.
</details>

<details>
<summary><b>C++</b> (C++17 + libcurl)</summary>

C++ hat kein HTTP in der Standardbibliothek, deshalb nutzt der Starter **libcurl**, die
Standard-C-Bibliothek für HTTP. JSON übernimmt ein kleiner Parser, der in `bot.cpp` enthalten ist.

**libcurl installieren:**

| System | Befehl |
|---|---|
| macOS | vorinstalliert (kommt mit den Xcode Command Line Tools: `xcode-select --install`) |
| Ubuntu / Debian / Raspberry Pi OS | `sudo apt install libcurl4-openssl-dev` |
| Fedora | `sudo dnf install libcurl-devel` |
| Arch | `sudo pacman -S curl` |
| Windows | am einfachsten: **WSL** (Ubuntu) nutzen und der Ubuntu-Zeile folgen. Oder [vcpkg](https://vcpkg.io): `vcpkg install curl`, oder MSYS2: `pacman -S mingw-w64-x86_64-curl` |

**Bauen & starten:**

```bash
cd bots/cpp
make                      # oder: g++ -std=c++17 -O2 bot.cpp -lcurl -o bot
export POKER_TOKEN="pk_..."
export POKER_URL="https://poker.example.com"
./bot practice
```

Mit CMake:

```cmake
cmake_minimum_required(VERSION 3.14)
project(pokerbot CXX)
set(CMAKE_CXX_STANDARD 17)
find_package(CURL REQUIRED)
add_executable(bot bot.cpp)
target_link_libraries(bot CURL::libcurl)
```

**JSON:** Das enthaltene `Json`-Struct gibt dir `state["legal"]["raise"]["min"].asInt()`,
`.asString()`, `.asBool()`, `.isNull()`, `.asArray()`. Wenn du etwas Vollständigeres willst, nimm
[nlohmann/json](https://github.com/nlohmann/json) (eine einzelne Header-Datei).

**Stolperfallen:**
- `-lcurl` muss in der Kommandozeile **nach** `bot.cpp` stehen.
- Ausgaben in eine Datei werden gepuffert. Der Starter nutzt `std::cout << std::unitbuf`, damit du sie sofort siehst.
- Vor dem Lesen von `legal.raise` oder `legal.call` `isNull()` prüfen.
- `CURLOPT_TIMEOUT` über 25 s setzen (der Starter nimmt 40).
</details>

<details>
<summary><b>JavaScript / TypeScript</b> (Node.js 18+, keine Pakete)</summary>

**Installieren:** [nodejs.org](https://nodejs.org) (LTS) oder `brew install node`. Prüfen mit `node --version`.

**Starten:**

```bash
cd bots/javascript
export POKER_TOKEN="pk_..."
export POKER_URL="https://poker.example.com"
node bot.mjs practice
```

**HTTP:** Node 18+ hat `fetch` eingebaut, also kein `npm install` nötig. `res.status`, `await res.text()`,
`JSON.parse`. Der Starter nutzt `AbortSignal.timeout(40_000)` als Timeout.

**Stolperfallen:**
- `await res.json()` stürzt beim leeren `204`-Body ab. Erst `res.text()` lesen oder den Status prüfen.
- `await` nicht vergessen: Ohne schickst du die Aktion, bevor du den Zustand hast.
- TypeScript: mit `npx tsx bot.ts` starten, oder mit `node --experimental-strip-types bot.ts`
  (Node 22.6+).
</details>

<details>
<summary><b>Andere Sprachen</b> (C#, Rust, Kotlin, ...)</summary>

Alles funktioniert. Du brauchst diese vier Dinge:

1. Einen HTTP-Client, der einen Header setzen (`Authorization: Bearer ...`) und einen JSON-Body schicken kann.
2. Einen Timeout über 25 Sekunden für `GET /turn`.
3. Einen JSON-Parser.
4. Eine Schleife.

**C#:**

```csharp
using System.Net.Http.Json;
var http = new HttpClient { BaseAddress = new Uri(url), Timeout = TimeSpan.FromSeconds(40) };
http.DefaultRequestHeaders.Authorization = new("Bearer", token);
while (true) {
    var res = await http.GetAsync("/api/v1/bot/turn?wait=25");
    if (res.StatusCode == System.Net.HttpStatusCode.NoContent) continue;
    var state = await res.Content.ReadFromJsonAsync<JsonElement>();
    var turnId = state.GetProperty("turn_id").GetString();
    await http.PostAsJsonAsync("/api/v1/bot/action", new { turn_id = turnId, action = "call" });
}
```

**Rust** (Crates `ureq` mit Feature `json` + `serde_json`):

```rust
let agent = ureq::AgentBuilder::new().timeout(std::time::Duration::from_secs(40)).build();
loop {
    let res = agent.get(&format!("{url}/api/v1/bot/turn?wait=25"))
        .set("Authorization", &format!("Bearer {token}")).call()?;
    if res.status() == 204 { continue; }
    let state: serde_json::Value = res.into_json()?;
    agent.post(&format!("{url}/api/v1/bot/action"))
        .set("Authorization", &format!("Bearer {token}"))
        .send_json(serde_json::json!({"turn_id": state["turn_id"], "action": "call"}))?;
}
```

Kotlin kann denselben `java.net.http.HttpClient` wie Java nutzen, dazu `kotlinx.serialization` für JSON.

Wenn du einen Starter-Bot für eine neue Sprache baust, schick ihn dem Organisator, damit die anderen ihn auch nutzen können.
</details>

## Deinen Bot rund um die Uhr laufen lassen

Für ein Turnier muss dein Bot vom Start an laufen, bis er ausscheidet oder gewinnt. Möglichkeiten:

- **Dein Laptop.** Okay, aber nicht zuklappen (im Ruhezustand bricht die Netzwerkverbindung ab).
- **`tmux` / `screen`** auf irgendeinem Linux-Rechner: Starte den Bot in einer Sitzung, die nach dem
  Ausloggen weiterläuft (`tmux new -s bot`, Bot starten, mit `Strg+B D` abkoppeln).
- **Ein Raspberry Pi oder ein günstiger VPS.**

Starter-Bots geben pro Entscheidung eine Zeile aus. Leite sie in eine Datei um, um sie später
auszuwerten: `python3 bot.py > game.log 2>&1`.
