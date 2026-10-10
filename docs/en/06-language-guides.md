# Language guides

Every starter bot does the same thing: check the token, register for open tournaments, then run the
turn loop. Pick your language below. Each section covers installation, running, how HTTP and JSON
work in that language, and the typical pitfalls.

All starter bots read `POKER_TOKEN` and `POKER_URL` from the environment (see
[Getting started](#/docs/getting-started)) and accept `practice` as the first argument.

<details>
<summary><b>Python</b> (3.8+, only the standard library)</summary>

**Install:** macOS: `brew install python` or the installer from python.org. Linux: usually
preinstalled. Windows: python.org installer, and tick *"Add python.exe to PATH"*.

**Run:**

```bash
cd bots/python
export POKER_TOKEN="pk_..."
export POKER_URL="https://poker.example.com"
python3 bot.py practice
```

**HTTP:** the starter uses `urllib.request` from the standard library. If you prefer
[requests](https://requests.readthedocs.io), it's a bit nicer:

```python
import requests
s = requests.Session()
s.headers["Authorization"] = f"Bearer {TOKEN}"
r = s.get(f"{BASE}/api/v1/bot/turn", params={"wait": 25}, timeout=40)
if r.status_code == 200:
    state = r.json()
    s.post(f"{BASE}/api/v1/bot/action", json={"turn_id": state["turn_id"], "action": "call"}, timeout=10)
```

(`pip install requests`, ideally in a virtual env: `python3 -m venv .venv && source .venv/bin/activate`.)

**Pitfalls:**
- `urllib` raises an exception (`HTTPError`) for 4xx/5xx answers instead of returning them. The
  starter catches it and returns `(status, body)` anyway.
- The `204` answer has an empty body: `json.loads(b"")` crashes. Check the status first.
- `print` output can be delayed when you redirect it to a file. The starter switches on line
  buffering (`sys.stdout.reconfigure(line_buffering=True)`), or use `python3 -u`.
- macOS: if you get `CERTIFICATE_VERIFY_FAILED`, run *"Install Certificates.command"* from your
  Python folder in Applications (python.org installs only).

**Useful for strategy:** `random`, `itertools.combinations`, `collections.Counter`.
The package `treys` (`pip install treys`) evaluates poker hands very fast, and so does `eval7`.
</details>

<details>
<summary><b>Java</b> (17+, no libraries)</summary>

**Install:** a JDK 17 or newer, e.g. [Adoptium Temurin](https://adoptium.net) or via your IDE
(IntelliJ can download one: *File → Project Structure → SDK*). Check with `java -version`.

**Run:** since Java 11 you can run a single source file directly, with no compile step:

```bash
cd bots/java
export POKER_TOKEN="pk_..."
export POKER_URL="https://poker.example.com"
java Bot.java practice
```

In IntelliJ: open the folder, right-click `Bot.java` → *Run*, then set the environment variables under
*Run → Edit Configurations → Environment variables*.

**HTTP:** `java.net.http.HttpClient` (built in since Java 11):

```java
HttpClient http = HttpClient.newBuilder().version(HttpClient.Version.HTTP_1_1).build();
HttpRequest req = HttpRequest.newBuilder(URI.create(BASE + "/api/v1/bot/turn?wait=25"))
        .header("Authorization", "Bearer " + TOKEN)
        .timeout(Duration.ofSeconds(40))
        .GET().build();
HttpResponse<String> res = http.send(req, HttpResponse.BodyHandlers.ofString());
```

**JSON:** Java has no JSON parser built in. The starter contains a small one (class `Json`, at the
bottom of the file) that turns JSON into `Map<String, Object>`, `List<Object>`, `Long`, `Double`,
`String`, `Boolean` and `null`. If you use Maven/Gradle, you can use
[Gson](https://github.com/google/gson) or [Jackson](https://github.com/FasterXML/jackson) instead
and map the state onto your own classes/records.

**Pitfalls:**
- Use `HttpClient.Version.HTTP_1_1`. The default, HTTP/2, tries an "upgrade" over plain
  `http://` that some servers handle badly (the body of POST requests gets lost).
- Numbers from the small JSON parser are `Long` (or `Double`). Use `((Number) x).longValue()`,
  not `(Integer) x`.
- `legal.raise` can be `null`. Check it before calling `.get("min")`.
</details>

<details>
<summary><b>Go</b> (1.21+, only the standard library)</summary>

**Install:** [go.dev/dl](https://go.dev/dl) or `brew install go`. Check with `go version`.

**Run:**

```bash
cd bots/go
export POKER_TOKEN="pk_..."
export POKER_URL="https://poker.example.com"
go run . practice
```

Or build a binary: `go build -o pokerbot .` then `./pokerbot`. With
`GOOS=linux GOARCH=arm64 go build` you can even build it for a Raspberry Pi.

**HTTP + JSON:** `net/http` and `encoding/json`. The starter defines structs for the state
(`State`, `Legal`, `Player`) with `json:"..."` tags, so you get typed fields like `s.Legal.Raise.Min`.

**Pitfalls:**
- Use an `http.Client` with a `Timeout` above 25 s (the starter uses 40 s). `http.Get` without a
  client never times out.
- Fields that can be `null` are pointers in the structs: `Call *int`, `Raise *RaiseRange`.
  Check `!= nil` before using them.
- Always `defer resp.Body.Close()`, or you'll leak connections.
- Unknown fields in the JSON are simply ignored, so you only need to declare what you use.
</details>

<details>
<summary><b>C++</b> (C++17 + libcurl)</summary>

C++ has no HTTP in the standard library, so the starter uses **libcurl**, the standard C library
for HTTP. JSON is handled by a small parser included in `bot.cpp`.

**Install libcurl:**

| System | Command |
|---|---|
| macOS | preinstalled (comes with the Xcode command line tools: `xcode-select --install`) |
| Ubuntu / Debian / Raspberry Pi OS | `sudo apt install libcurl4-openssl-dev` |
| Fedora | `sudo dnf install libcurl-devel` |
| Arch | `sudo pacman -S curl` |
| Windows | easiest: use **WSL** (Ubuntu) and follow the Ubuntu line. Or [vcpkg](https://vcpkg.io): `vcpkg install curl`, or MSYS2: `pacman -S mingw-w64-x86_64-curl` |

**Build & run:**

```bash
cd bots/cpp
make                      # or: g++ -std=c++17 -O2 bot.cpp -lcurl -o bot
export POKER_TOKEN="pk_..."
export POKER_URL="https://poker.example.com"
./bot practice
```

With CMake:

```cmake
cmake_minimum_required(VERSION 3.14)
project(pokerbot CXX)
set(CMAKE_CXX_STANDARD 17)
find_package(CURL REQUIRED)
add_executable(bot bot.cpp)
target_link_libraries(bot CURL::libcurl)
```

**JSON:** the included `Json` struct gives you `state["legal"]["raise"]["min"].asInt()`,
`.asString()`, `.asBool()`, `.isNull()`, `.asArray()`. If you want something more complete, use
[nlohmann/json](https://github.com/nlohmann/json) (a single header file).

**Pitfalls:**
- `-lcurl` must come **after** `bot.cpp` on the command line.
- Output to a file is buffered. The starter uses `std::cout << std::unitbuf` so you see it immediately.
- Check `isNull()` before reading `legal.raise` or `legal.call`.
- Set `CURLOPT_TIMEOUT` above 25 s (the starter uses 40).
</details>

<details>
<summary><b>JavaScript / TypeScript</b> (Node.js 18+, no packages)</summary>

**Install:** [nodejs.org](https://nodejs.org) (LTS) or `brew install node`. Check with `node --version`.

**Run:**

```bash
cd bots/javascript
export POKER_TOKEN="pk_..."
export POKER_URL="https://poker.example.com"
node bot.mjs practice
```

**HTTP:** Node 18+ has `fetch` built in, so no `npm install` is needed. `res.status`, `await res.text()`,
`JSON.parse`. The starter uses `AbortSignal.timeout(40_000)` as a timeout.

**Pitfalls:**
- `await res.json()` crashes on the empty `204` body. Read `res.text()` first, or check the status.
- Don't forget `await`: without it you send the action before you've received the state.
- TypeScript: run it with `npx tsx bot.ts`, or with `node --experimental-strip-types bot.ts`
  (Node 22.6+).
</details>

<details>
<summary><b>Other languages</b> (C#, Rust, Kotlin, ...)</summary>

Anything works. You need these four things:

1. An HTTP client that can set a header (`Authorization: Bearer ...`) and send a JSON body.
2. A timeout above 25 seconds for `GET /turn`.
3. A JSON parser.
4. A loop.

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

**Rust** (crates `ureq` with feature `json` + `serde_json`):

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

Kotlin can use the same `java.net.http.HttpClient` as Java, plus `kotlinx.serialization` for JSON.

If you build a starter bot for a new language, send it to the organizer so the others can use it too.
</details>

## Running your bot 24/7

For a tournament, your bot has to run from the start until it busts or wins. Options:

- **Your laptop.** Fine, but don't close the lid (sleep mode drops the network connection).
- **`tmux` / `screen`** on any Linux machine: start the bot in a session that keeps running after
  you log out (`tmux new -s bot`, start the bot, detach with `Ctrl+B D`).
- **A Raspberry Pi or a cheap VPS.**

Starter bots print one line per decision. Redirect it to a file to analyze later:
`python3 bot.py > game.log 2>&1`.
