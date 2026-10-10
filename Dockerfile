# poker-pi: builds the spectator UI, then runs the Python server that also serves it.
# Works on amd64 and arm64 (Raspberry Pi).

FROM docker.io/library/node:22-alpine AS web
WORKDIR /src/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
COPY docs/ /src/docs/
RUN npm run build

FROM docker.io/library/python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POKER_DB=/data/poker.db \
    POKER_STATIC_DIR=/app/web \
    POKER_HOST=0.0.0.0 \
    POKER_PORT=8000
WORKDIR /app
COPY server/pyproject.toml server/
COPY server/poker_pi server/poker_pi
RUN pip install --no-cache-dir ./server && rm -rf server
COPY --from=web /src/web/dist /app/web
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=4)"
CMD ["python", "-m", "poker_pi"]
