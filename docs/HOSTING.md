# Hosting & administration

This is for whoever runs the server. The pages for bot authors are in `docs/en` and `docs/de`; the
website shows them under **Docs**.

## Local development

```bash
# server
cd server
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest              # engine + API tests
.venv/bin/python -m poker_pi            # http://localhost:8000 (API, /docs Swagger UI, website if built)

# website (in a second terminal)
cd web
npm install
npm run dev                             # http://localhost:5173, proxies /api to :8000
npm run build                           # builds web/dist, which the server then serves on :8000
```

The database defaults to `data/poker.db` in the repository root.

## Running in a container (Docker or Podman)

```bash
docker compose up -d --build        # or: podman compose up -d --build
docker compose exec poker-server python -m poker_pi.admin create-bot "MyBot" --owner Me
docker compose logs -f poker-server
docker compose down                 # data stays in the "poker-data" volume (down -v deletes it)
```

The website is on http://localhost:8000 (`POKER_PORT=8080 docker compose up -d` for another port).
Bots running on the same machine use `POKER_URL=http://localhost:8000`.

Podman notes:
- `podman compose` hands off to docker-compose if it's installed, so the commands are the same.
- Building directly with `podman build` creates an OCI image, which drops the Dockerfile's
  `HEALTHCHECK`. That's why the compose files declare the healthcheck themselves. If you build by
  hand, use `podman build --format docker -t poker-pi .`.
- The image is multi-arch-friendly: build it on the machine that runs it (arm64 on the Pi and
  Apple Silicon, amd64 elsewhere).

## Admin CLI

All admin work goes through `python -m poker_pi.admin`. It writes to the database directly, and the
running server picks the changes up within a second. Inside Docker, prefix the commands with
`docker compose exec poker-server`.

```bash
python -m poker_pi.admin create-bot "Bluff Master" --owner Lena     # prints the token ONCE
python -m poker_pi.admin list-bots
python -m poker_pi.admin rotate-token "Bluff Master"                # new token, old one stops working
python -m poker_pi.admin revoke-bot "Bluff Master"                  # disable (restore-bot to undo)

python -m poker_pi.admin create-tournament --name "Friday Night Poker" --start "2026-10-16 20:00"
#   --start also accepts "+15m", "+2h", "now". Times without timezone are local time.
#   options: --stack 1500 --hands-per-level 10 --pace 2 --street-pause 1.5 --hand-pause 4 --max-players 9
python -m poker_pi.admin list-tournaments
python -m poker_pi.admin show-tournament 1
python -m poker_pi.admin register 1 "Bluff Master" "Other Bot"      # bots can also register themselves
python -m poker_pi.admin start 1                                    # start now instead of at start time
python -m poker_pi.admin reschedule 1 "+1h"
python -m poker_pi.admin cancel 1                                   # also stops a running tournament
```

A tournament with fewer than 2 registered bots at its start time is cancelled automatically.

## Configuration

Environment variables (all optional):

| Variable | Default | Meaning |
|---|---|---|
| `POKER_DB` | `data/poker.db` | SQLite database file |
| `POKER_STATIC_DIR` | `web/dist` | built website |
| `POKER_HOST` / `POKER_PORT` | `0.0.0.0` / `8000` | listen address |
| `POKER_DECISION_TIMEOUT` | `15` | seconds per decision |
| `POKER_MAX_TIMEOUTS` | `3` | timeouts in a row until a bot sits out |
| `POKER_SITOUT_GRACE` | `3` | seconds a sitting-out bot gets per decision |
| `POKER_DISCONNECT_AFTER` | `60` | seconds without any request until a bot counts as disconnected |
| `POKER_RATE_LIMIT` | `60` | unproductive requests (empty polls, errors) per second per bot |
| `POKER_CARD_DECK` | `drawn` | default card style on the website: `drawn` or `artwork` (viewers can switch in the ⚙ menu) |

Per-tournament settings (stack, blind speed, pacing) are options of `create-tournament`.

## Website look: cards and sounds

- **Card styles**: `drawn` (SVG drawn in code: `web/src/lib/cards/DrawnCard.svelte`) and `artwork`
  (public-domain deck in `web/public/cards/artwork/`). `POKER_CARD_DECK` sets the default; every viewer
  can switch in the ⚙ menu, and `#/cards` shows all 52 cards side by side. To drop a style, delete its
  files and its entry in `DECKS` in `web/src/lib/settings.svelte.js` (see the artwork `LICENSE.md`).
- **Sounds**: put recordings into `web/public/sounds/` (the README there lists the names), then
  `cd web && npm run build`. Viewers turn sound on in the ⚙ menu.

## Deploying on a Raspberry Pi

The server is published through a dedicated Cloudflare Tunnel: no port
forwarding, and the home IP stays hidden.

1. **Copy the repository** to the Pi, e.g. `~/poker-pi` (git clone or rsync).
2. **Create the tunnel**: Cloudflare Zero Trust → Networks → Tunnels → *Create a tunnel* →
   Cloudflared → name `poker-pi`. Copy the token.
   Add a public hostname: `poker.example.com` → service `http://poker-server:8000`.
3. **Store the token**:
   ```bash
   cd ~/poker-pi/deploy
   echo "TUNNEL_TOKEN=<token>" > .env && chmod 600 .env
   ```
4. **Data directory** on the USB disk, not on the SD card:
   ```bash
   echo "POKER_DATA_DIR=/srv/poker-pi" >> .env && mkdir -p /srv/poker-pi
   ```
5. **Start**:
   ```bash
   docker compose -f docker-compose.pi.yml up -d --build
   docker compose -f docker-compose.pi.yml logs -f poker-server
   ```
   The first build on the Pi takes a few minutes (npm + pip).
6. **Create bots** and hand out the tokens:
   ```bash
   docker compose -f docker-compose.pi.yml exec poker-server python -m poker_pi.admin create-bot "Name" --owner Friend
   ```

### Cloudflare settings to check

- **Bot Fight Mode / Super Bot Fight Mode** (Security → Bots) may challenge requests from bots,
  since they look automated, which they are. Either switch it off for the
  zone, or add a WAF *skip* rule for `http.host eq "poker.example.com" and starts_with(http.request.uri.path, "/api/")`.
- **Caching**: Cloudflare doesn't cache JSON by default, so nothing to do. Make sure no cache rule
  matches `/api/*`.
- **Timeouts**: Cloudflare allows 100 s per request. The long-poll waits at most 30 s and the SSE stream
  sends a keep-alive every 15 s, so both are well inside the limit.
- Optional rate limiting rule on `/api/v1/bot/*` as an additional safety net.

### Rootless Docker note

The container runs as root *inside* the container. With rootless Docker that maps
to the unprivileged user running Docker, so the files in the data folder belong to that user.

## Backups

Everything lives in one SQLite file. A consistent copy while the server runs:

```bash
sqlite3 /srv/poker-pi/poker.db ".backup '/srv/poker-pi/backup-$(date +%F).db'"
```

## Updating

```bash
cd ~/poker-pi && git pull
cd deploy && docker compose -f docker-compose.pi.yml up -d --build
```

Running tournaments survive restarts: they resume from the last completed hand.

## Regenerating openapi.yaml

The server serves the spec live at `/openapi.yaml`. To refresh the copy in `docs/`:

```bash
cd server && .venv/bin/python -c "import yaml; from poker_pi.config import Settings; from poker_pi.main import create_app; \
print(yaml.safe_dump(create_app(Settings(db_path=':memory:')).openapi(), sort_keys=False))" > ../docs/openapi.yaml
```
