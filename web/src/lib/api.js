const BASE = "/api/v1/public";

export async function get(path) {
  const res = await fetch(BASE + path);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {}
    throw new Error(detail);
  }
  return res.json();
}

// Subscribe to a table's live events. Returns a function that closes the stream.
export function streamTable(tableId, onEvent, onStatus = () => {}) {
  const es = new EventSource(`${BASE}/tables/${encodeURIComponent(tableId)}/stream`);
  es.onopen = () => onStatus("live");
  es.onerror = () => onStatus(es.readyState === EventSource.CLOSED ? "closed" : "reconnecting");
  es.onmessage = (m) => onEvent(JSON.parse(m.data));
  return () => es.close();
}
