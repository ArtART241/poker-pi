# HTTP basics

This page summarizes the web concepts a bot needs: HTTP requests and responses, JSON, status
codes, bearer tokens and long polling. Readers familiar with REST APIs can skip it.

## Requests and responses

HTTP is a request/response protocol. A client sends a **request** to a server and receives
exactly one **response**. There is no permanent connection to manage.

A request consists of:

| Part | Example | Meaning |
|---|---|---|
| **Method** | `GET`, `POST`, `DELETE` | The kind of operation: `GET` reads, `POST` sends data or triggers something, `DELETE` removes. |
| **URL** | `https://poker.example.com/api/v1/bot/turn?wait=25` | The target. The part after `?` is the *query string* with parameters as `key=value&key2=value2`. |
| **Headers** | `Authorization: Bearer pk_...` | Metadata as `Name: value` lines, e.g. credentials or the body format. |
| **Body** | `{"turn_id": "t_1", "action": "call"}` | Optional payload, usually only with `POST`. For poker-pi always JSON. |

A response consists of a **status code** (e.g. `200`), **headers** and an optional **body**.

On the wire, both are plain text:

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

HTTP libraries build and parse these messages; they never need to be written by hand.

<details>
<summary>HTTPS</summary>

HTTPS is HTTP inside an encrypted TLS connection. HTTP libraries handle it automatically for
`https://` URLs, provided the system has up-to-date root certificates. Certificate errors are
covered in the [FAQ](#/docs/faq).
</details>

## Status codes

| Code | Name | Meaning in poker-pi |
|---|---|---|
| `200` | OK | Success; the body contains the result. |
| `204` | No Content | Success without content. For `GET /turn`: no decision is due yet, ask again. The body is **empty** and must not be parsed as JSON. |
| `401` | Unauthorized | Token missing or invalid. |
| `403` | Forbidden | Attempt to answer another bot's turn. |
| `404` | Not Found | Unknown URL or id. |
| `409` | Conflict | The turn is over (answered already or timed out). |
| `422` | Unprocessable Entity | The request is understood but not allowed, e.g. a raise below the minimum. The body explains why. |
| `429` | Too Many Requests | Too many requests without effect; the client should slow down. |
| `5xx` | Server Error | A server-side problem; retrying after a short pause is appropriate. |

As a rule: **2xx** success, **4xx** a problem with the request, **5xx** a problem on the server.

Every error response from poker-pi has a JSON body of the form `{"detail": "explanation"}`.
Logging `detail` is the quickest way to find the cause of a problem.

## JSON

JSON is the data format used for all bodies:

```json
{
  "hole_cards": ["Ah", "Td"],
  "stack": 1480,
  "legal": { "check": false, "call": 20, "raise": { "min": 40, "max": 1500 } },
  "board": []
}
```

- `{ }` is an object (string keys mapped to values), `[ ]` an array.
- Values are strings in double quotes, numbers, `true` / `false`, or `null`.

Nearly every language offers a JSON parser, either built in or as a standard package, that turns
this text into native maps/lists or typed structures and back.

<details>
<summary>null is meaningful</summary>

In poker-pi, `null` carries information: `"call": null` means there is nothing to call, and
`"raise": null` means raising is not allowed. In statically typed languages these fields map to an
optional or nullable type. Mapping them to `0` would turn "cannot raise" into "raise to 0", which
the server rejects.
</details>

## REST

REST describes a style of HTTP API in which resources have URLs and the method expresses the
operation:

```
GET    /api/v1/bot/tournaments                 → list tournaments
POST   /api/v1/bot/tournaments/3/register      → register for tournament 3
DELETE /api/v1/bot/tournaments/3/register      → withdraw from tournament 3
```

## Bearer tokens

Each request to `/api/v1/bot/...` identifies the bot through a header:

```
Authorization: Bearer pk_3Jk9xQ7mR2...
```

`Authorization` is a standard HTTP header; `Bearer` is the token type ("whoever bears this token
is authorized"), followed by a single space and the token. There is no login and no session: every
request is checked on its own.

<details>
<summary>Common mistakes</summary>

- The word `Bearer` or the space after it is missing.
- The header is spelled `Authorisation` instead of `Authorization`.
- The copied token contains a trailing space or line break.
- The token is sent in the URL (`?token=...`); this is not supported, and URLs tend to end up in logs.
</details>

## Long polling

A bot needs to learn when it is its turn. Three approaches are common:

1. **Polling**: asking repeatedly, e.g. every 100 ms. Simple, but wasteful for the server.
2. **Push**: the server calls the bot. This requires the bot to be reachable from the internet.
3. **Long polling**: the bot asks, and the server holds the request open until there is something
   to report, or until a timeout. The answer arrives as soon as the turn opens.

poker-pi uses long polling. `GET /api/v1/bot/turn?wait=25` can take up to 25 seconds to return;
this is expected behaviour. Two consequences:

- The HTTP client's **timeout must be longer than the wait time**, for example 40 seconds. Some
  libraries default to 10 or 30 seconds.
- A plain blocking loop is sufficient. Threads, async code or callbacks are not required.
