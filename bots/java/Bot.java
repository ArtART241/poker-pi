// poker-pi starter bot (Java 17+, no libraries needed).
//
// Run (no compile step needed since Java 11):
//   export POKER_TOKEN="pk_..."                          # your bot token
//   export POKER_URL="https://poker.example.com"    # optional, default http://localhost:8000
//   java Bot.java              # play tournaments
//   java Bot.java practice     # start a practice table against house bots first
//
// Only decide() needs to change to make the bot smarter.
// Java has no JSON parser built in, so a tiny one is included at the bottom (class Json).

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class Bot {
    static final String BASE_URL = System.getenv().getOrDefault("POKER_URL", "http://localhost:8000").replaceAll("/$", "");
    static final String TOKEN = System.getenv().getOrDefault("POKER_TOKEN", "");
    static final String RANKS = "23456789TJQKA";
    static final HttpClient HTTP = HttpClient.newBuilder()
            .version(HttpClient.Version.HTTP_1_1) // plain HTTP/1.1 works everywhere
            .connectTimeout(Duration.ofSeconds(10))
            .build();

    // ------------------------------------------------------------------------ your strategy

    /** Returns the JSON fields of the action, e.g. {"action": "call"}. */
    @SuppressWarnings("unchecked")
    static Map<String, Object> decide(Map<String, Object> state) {
        Map<String, Object> legal = (Map<String, Object>) state.get("legal");
        List<Object> hole = (List<Object>) state.get("hole_cards");
        int r1 = RANKS.indexOf(((String) hole.get(0)).charAt(0));
        int r2 = RANKS.indexOf(((String) hole.get(1)).charAt(0));
        long toCall = num(state.get("to_call"));
        long stack = num(state.get("stack"));

        boolean pair = r1 == r2;
        boolean high = Math.max(r1, r2) >= RANKS.indexOf('T') && Math.min(r1, r2) >= RANKS.indexOf('9');
        boolean strong = pair || high || Math.max(r1, r2) == RANKS.indexOf('A');

        Map<String, Object> action = new LinkedHashMap<>();
        Map<String, Object> raise = (Map<String, Object>) legal.get("raise"); // null if not allowed
        long bigBlind = num(((Map<String, Object>) state.get("blinds")).get("big"));
        boolean nobodyRaised = num(state.get("current_bet")) <= bigBlind;
        if (strong && raise != null && nobodyRaised) {
            // raise TO 3 big blinds (amount = your total bet on this street), within the legal range
            long amount = Math.max(num(raise.get("min")), 3 * bigBlind);
            action.put("action", "raise");
            action.put("amount", Math.min(amount, num(raise.get("max"))));
        } else if (Boolean.TRUE.equals(legal.get("check"))) {
            action.put("action", "check");
        } else if (strong || toCall <= stack / 20) {
            action.put("action", "call");
        } else {
            action.put("action", "fold");
        }
        return action;
    }

    // ------------------------------------------------------------------------ HTTP plumbing

    record Reply(int status, Object json) {}

    static Reply api(String method, String path, Map<String, Object> body) throws Exception {
        HttpRequest.Builder req = HttpRequest.newBuilder(URI.create(BASE_URL + path))
                .timeout(Duration.ofSeconds(40))
                .header("Authorization", "Bearer " + TOKEN)
                .header("User-Agent", "poker-pi-starter-bot/1.0 (java)");
        if (body != null) {
            req.header("Content-Type", "application/json")
               .method(method, HttpRequest.BodyPublishers.ofString(Json.write(body)));
        } else {
            req.method(method, HttpRequest.BodyPublishers.noBody());
        }
        HttpResponse<String> res = HTTP.send(req.build(), HttpResponse.BodyHandlers.ofString());
        String text = res.body();
        return new Reply(res.statusCode(), text == null || text.isEmpty() ? null : Json.parse(text));
    }

    static long num(Object o) {
        return o == null ? 0 : ((Number) o).longValue();
    }

    @SuppressWarnings("unchecked")
    static void registerForOpenTournaments() throws Exception {
        Reply r = api("GET", "/api/v1/bot/tournaments", null);
        if (r.status() != 200) {
            System.out.println("could not list tournaments: " + r.status() + " " + r.json());
            return;
        }
        for (Object o : (List<Object>) r.json()) {
            Map<String, Object> t = (Map<String, Object>) o;
            if ("registering".equals(t.get("status")) && !Boolean.TRUE.equals(t.get("registered"))) {
                Reply reg = api("POST", "/api/v1/bot/tournaments/" + num(t.get("id")) + "/register", null);
                System.out.println("register for '" + t.get("name") + "': " + reg.status() + " " + reg.json());
            }
        }
    }

    @SuppressWarnings("unchecked")
    public static void main(String[] args) throws Exception {
        if (TOKEN.isEmpty()) {
            System.err.println("Set the POKER_TOKEN environment variable to your bot token.");
            System.exit(1);
        }
        Reply me = api("GET", "/api/v1/bot/me", null);
        if (me.status() != 200) {
            System.err.println("Token check failed (" + me.status() + "): " + me.json());
            System.exit(1);
        }
        System.out.println("Hello " + ((Map<String, Object>) me.json()).get("name") + "! Talking to " + BASE_URL);

        if (args.length > 0 && args[0].equals("practice")) {
            Map<String, Object> body = new LinkedHashMap<>();
            body.put("opponents", List.of("random", "station", "tight"));
            Reply p = api("POST", "/api/v1/bot/practice", body);
            System.out.println("practice table: " + p.status() + " " + ((Map<String, Object>) p.json()).get("watch_url"));
        }

        registerForOpenTournaments();
        long lastCheck = System.currentTimeMillis();

        while (true) {
            if (System.currentTimeMillis() - lastCheck > 300_000) {
                registerForOpenTournaments();
                lastCheck = System.currentTimeMillis();
            }
            Reply turn;
            try {
                turn = api("GET", "/api/v1/bot/turn?wait=25", null);
            } catch (Exception e) {
                System.out.println("network error: " + e);
                Thread.sleep(2000);
                continue;
            }
            if (turn.status() == 204) continue; // not our turn yet, ask again
            if (turn.status() != 200) {
                System.out.println("unexpected answer: " + turn.status() + " " + turn.json());
                Thread.sleep(2000);
                continue;
            }

            Map<String, Object> state = (Map<String, Object>) turn.json();
            Map<String, Object> action = decide(state);
            Map<String, Object> body = new LinkedHashMap<>();
            body.put("turn_id", state.get("turn_id"));
            body.putAll(action);
            Reply res = api("POST", "/api/v1/bot/action", body);
            System.out.printf("hand %d %-7s %s | board %s -> %s [%d]%n", num(state.get("hand_id")), state.get("street"),
                    state.get("hole_cards"), state.get("board"), Json.write(action), res.status());
            if (res.status() == 422) {
                // our action was not legal: say why, then play it safe so we do not time out
                System.out.println("  rejected: " + res.json());
                Map<String, Object> legal = (Map<String, Object>) state.get("legal");
                body.clear();
                body.put("turn_id", state.get("turn_id"));
                body.put("action", Boolean.TRUE.equals(legal.get("check")) ? "check" : "fold");
                api("POST", "/api/v1/bot/action", body);
            } else if (res.status() != 200) {
                System.out.println("  server said: " + res.json());
            }
        }
    }
}

/** Minimal JSON reader/writer: objects -> Map, arrays -> List, numbers -> Long/Double. */
class Json {
    private final String s;
    private int i;

    private Json(String s) { this.s = s; }

    static Object parse(String text) {
        Json p = new Json(text);
        Object v = p.value();
        p.ws();
        if (p.i != p.s.length()) throw new IllegalArgumentException("trailing characters at " + p.i);
        return v;
    }

    private void ws() { while (i < s.length() && Character.isWhitespace(s.charAt(i))) i++; }

    private Object value() {
        ws();
        char c = s.charAt(i);
        if (c == '{') return object();
        if (c == '[') return array();
        if (c == '"') return string();
        if (s.startsWith("true", i)) { i += 4; return Boolean.TRUE; }
        if (s.startsWith("false", i)) { i += 5; return Boolean.FALSE; }
        if (s.startsWith("null", i)) { i += 4; return null; }
        return number();
    }

    private Map<String, Object> object() {
        Map<String, Object> m = new LinkedHashMap<>();
        i++; ws();
        if (s.charAt(i) == '}') { i++; return m; }
        while (true) {
            ws(); String k = string(); ws(); i++; // ':'
            m.put(k, value()); ws();
            if (s.charAt(i++) == '}') return m; // otherwise ','
        }
    }

    private List<Object> array() {
        List<Object> a = new ArrayList<>();
        i++; ws();
        if (s.charAt(i) == ']') { i++; return a; }
        while (true) {
            a.add(value()); ws();
            if (s.charAt(i++) == ']') return a; // otherwise ','
        }
    }

    private String string() {
        StringBuilder b = new StringBuilder();
        i++; // opening quote
        while (true) {
            char c = s.charAt(i++);
            if (c == '"') return b.toString();
            if (c != '\\') { b.append(c); continue; }
            char e = s.charAt(i++);
            switch (e) {
                case 'n' -> b.append('\n');
                case 't' -> b.append('\t');
                case 'r' -> b.append('\r');
                case 'b' -> b.append('\b');
                case 'f' -> b.append('\f');
                case 'u' -> { b.append((char) Integer.parseInt(s.substring(i, i + 4), 16)); i += 4; }
                default -> b.append(e); // \" \\ \/
            }
        }
    }

    private Object number() {
        int start = i;
        while (i < s.length() && "+-0123456789.eE".indexOf(s.charAt(i)) >= 0) i++;
        String n = s.substring(start, i);
        if (n.contains(".") || n.contains("e") || n.contains("E")) return Double.parseDouble(n);
        return Long.parseLong(n);
    }

    static String write(Object v) {
        if (v == null) return "null";
        if (v instanceof String str) {
            StringBuilder b = new StringBuilder("\"");
            for (char c : str.toCharArray()) {
                if (c == '"' || c == '\\') b.append('\\').append(c);
                else if (c < 0x20) b.append(String.format("\\u%04x", (int) c));
                else b.append(c);
            }
            return b.append('"').toString();
        }
        if (v instanceof Map<?, ?> m) {
            StringBuilder b = new StringBuilder("{");
            for (Map.Entry<?, ?> e : m.entrySet()) {
                if (b.length() > 1) b.append(',');
                b.append(write(String.valueOf(e.getKey()))).append(':').append(write(e.getValue()));
            }
            return b.append('}').toString();
        }
        if (v instanceof List<?> l) {
            StringBuilder b = new StringBuilder("[");
            for (Object o : l) {
                if (b.length() > 1) b.append(',');
                b.append(write(o));
            }
            return b.append(']').toString();
        }
        return String.valueOf(v); // numbers, booleans
    }
}
