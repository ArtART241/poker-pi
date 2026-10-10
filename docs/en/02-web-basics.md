# HTTP & REST for beginners

You can program, but you've never written something that talks to a web server? This page covers
everything you need for poker-pi, and nothing more. Read it once and the rest of the docs will make sense.

## HTTP in 60 seconds

HTTP is a **request/response** protocol. Your program (the *client*) sends a **request** to a
*server*, and the server sends back exactly one **response**. That's it. There's no permanent
connection you have to manage.

A request consists of:

| Part | Example | Meaning |
|---|---|---|
| **Method** | `GET`, `POST`, `DELETE` | What you want to do. `GET` = read something, `POST` = send something / do something, `DELETE` = remove something. |
| **URL** | `https://poker.example.com/api/v1/bot/turn?wait=25` | Where. The part after `?` is the *query string*: extra parameters as `key=value&key2=value2`. |
| **Headers** | `Authorization: Bearer pk_...` | Metadata as `Name: value` lines, e.g. who you are or what format the body has. |
| **Body** | `{"turn_id": "t_1", "action": "call"}` | Optional data, usually only for `POST`. Here it's always JSON. |

A response consists of:

| Part | Example | Meaning |
|---|---|---|
| **Status code** | `200`, `204`, `401`, `422` | A number that says how it went (table below). |
| **Headers** | `Content-Type: application/json` | Metadata. |
| **Body** | `{"name": "MyBot", ...}` | The actual answer, here always JSON (or empty). |

This is what an actual request looks like on the wire. It's just text:

```http
POST /api/v1/bot/action HTTP/1.1
Host: poker.example.com
Authorization: Bearer pk_3Jk9xQ...
Content-Type: application/json
Content-Length: 46

{"turn_id": "t_3f9a0c1b", "action": "call"}
```

And the answer:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{"accepted": true, "action": "call", "amount": null}
```

You'll never write this by hand. Your language's HTTP library builds it for you. But it helps to
know that there's no magic behind it.

<details>
<summary>What about HTTPS?</summary>

HTTPS is HTTP inside an encrypted connection (TLS). Your HTTP library handles it automatically
when the URL starts with `https://`. You don't have to do anything, except make sure your system has
up-to-date root certificates. If you get certificate errors, see the [FAQ](#/docs/faq).
</details>

## Status codes you'll meet

| Code | Name | What it means for your bot |
|---|---|---|
| `200` | OK | Everything worked. The body contains the answer. |
| `204` | No Content | Worked, but there's nothing to report. For `GET /turn` it means *"not your turn yet, ask again"*. The body is **empty**, so don't try to parse it as JSON! |
| `401` | Unauthorized | Token missing or wrong. |
| `403` | Forbidden | You tried to answer someone else's turn. |
| `404` | Not Found | Wrong URL or unknown id. |
| `409` | Conflict | The turn is over (you were too slow, or you already answered). |
| `422` | Unprocessable Entity | Your request was understood but isn't allowed, e.g. raising too little. The body says why. |
| `429` | Too Many Requests | You're sending too many requests. Slow down. |
| `5xx` | Server Error | Not your fault. Wait a second and try again. |

The rule of thumb: **2xx = good, 4xx = your request has a problem, 5xx = the server has a problem.**

> Every error response from poker-pi has a JSON body like `{"detail": "explanation"}`.
> **Always print `detail` when something goes wrong.** It tells you exactly what to fix.

## JSON

JSON is the text format for data on the web. If you know Python dicts or JavaScript objects, you
already know it:

```json
{
  "hole_cards": ["Ah", "Td"],
  "stack": 1480,
  "legal": { "check": false, "call": 20, "raise": { "min": 40, "max": 1500 } },
  "board": []
}
```

- `{ }` is an *object* (a map/dictionary: string keys → values)
- `[ ]` is an *array* (a list)
- values: strings in `"double quotes"`, numbers, `true`/`false`, `null`

Every language has a way to turn JSON text into native data structures and back:

| Language | Read JSON | Write JSON |
|---|---|---|
| Python | `json.loads(text)` → dict | `json.dumps(obj)` |
| JavaScript | `JSON.parse(text)` | `JSON.stringify(obj)` |
| Go | `json.Unmarshal(bytes, &structVar)` | `json.Marshal(v)` |
| Java | no built-in parser; the starter bot includes a small one, or use Gson/Jackson | |
| C++ | no built-in parser; the starter bot includes a small one, or use nlohmann/json | |

<details>
<summary>Tip: null vs. missing vs. 0</summary>

In poker-pi, `null` has a meaning. `"call": null` means *"there is nothing to call"* and
`"raise": null` means *"you are not allowed to raise"*. In typed languages, map these to `Optional`,
pointers (`*int` in Go) or a nullable type, not to `0`. Otherwise "can't raise" turns into
"raise to 0" and the server rejects it.
</details>

## REST

"REST" is just a style of designing HTTP APIs. **Things** have URLs (`/tournaments/3`), and the
HTTP method says what you do with them:

```
GET    /api/v1/bot/tournaments                 → list tournaments
POST   /api/v1/bot/tournaments/3/register      → register for tournament 3
DELETE /api/v1/bot/tournaments/3/register      → withdraw from tournament 3
```

That's all there is to it. You don't need to know more about REST.

## Bearer tokens

The server needs to know **which bot** is sending a request. For that, every request to
`/api/v1/bot/...` carries your token in a header:

```
Authorization: Bearer pk_3Jk9xQ7mR2...
```

- `Authorization` is the header name (a standard HTTP header).
- `Bearer` means *"whoever bears (holds) this token is allowed in"*. It's the token type.
- Then a single space, then your token.

That's the whole mechanism. No login, no session, no cookies. Each request is checked on its own.

<details>
<summary>Common mistakes with the token</summary>

- Forgetting the word `Bearer` (and the space after it).
- Writing `Authorisation` (British spelling). The header is `Authorization` with a z.
- Copying the token with a line break or space at the end.
- Putting the token in the URL (`?token=...`). It doesn't work, and URLs end up in logs.
- Committing the token to GitHub. Use an environment variable instead.

If you think your token leaked, the organizer can issue a new one (`rotate-token`), and the old one
stops working immediately.
</details>

## Long polling: why `GET /turn` "hangs"

Your bot needs to find out when it's its turn. There are three ways to do that:

1. **Polling**: ask "my turn?" every 100 ms. Simple, but it wastes the server's resources, and the
   server is a Raspberry Pi. Please don't.
2. **Push**: the server calls *your* program. Then your laptop would have to be reachable from
   the internet, which is a hassle.
3. **Long polling**: you ask "my turn?" and the server **doesn't answer until it is** (or until
   25 seconds have passed). As soon as your turn comes, you get the answer instantly.

poker-pi uses **long polling**. For you, that means:

```
loop forever:
    response = GET /api/v1/bot/turn?wait=25      # may take up to 25 seconds, that's normal!
    if response.status == 204: continue          # nothing happened, ask again
    state = parse JSON of response
    action = decide(state)
    POST /api/v1/bot/action  {turn_id, action}
```

> **Important:** set your HTTP client's **timeout higher than 25 seconds**, e.g. 40 s. Some libraries
> default to 10 or 30 seconds and would abort the request before the server answers.

<details>
<summary>Doesn't a hanging request block my program?</summary>

Yes, the thread that sends the request waits. That's exactly what you want: your bot has nothing
else to do while it isn't its turn. You don't need threads, async/await or callbacks. A plain
blocking `while` loop is perfect.

If you *want* to compute things in the background (e.g. precompute tables), use a separate thread.
That's optional.
</details>

## Try it in the browser: Swagger UI

The server documents itself. Open **[/docs](https://poker.example.com/docs)**:

1. Click **Authorize** (top right), paste your token (without `Bearer `), confirm.
2. Open an endpoint, e.g. `GET /api/v1/bot/me`, click **Try it out**, then **Execute**.
3. You'll see the exact request (as a curl command), the status code and the response.

This is the fastest way to understand what each endpoint returns. The machine-readable spec is at
[/openapi.yaml](https://poker.example.com/openapi.yaml). Some tools can generate client code
from it, but for this API that's overkill.

## Use the standard library

You don't need frameworks. Every starter bot uses only what comes with the language:

| Language | HTTP | JSON |
|---|---|---|
| Python | `urllib.request` (or `requests` if you like, `pip install requests`) | `json` |
| Java 11+ | `java.net.http.HttpClient` | not built in (included in the starter) |
| Go | `net/http` | `encoding/json` |
| C++ | not built in, use **libcurl** | not built in (included in the starter) |
| JavaScript (Node 18+) | built-in `fetch` | built-in `JSON` |
| C# | `System.Net.Http.HttpClient` | `System.Text.Json` |
| Rust | crates `ureq` or `reqwest` | crate `serde_json` |
