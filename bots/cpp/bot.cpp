// poker-pi starter bot (C++17 + libcurl).
//
// C++ has no HTTP client in its standard library, so this uses libcurl (preinstalled on
// macOS and most Linux systems; see the docs for Windows). JSON is parsed by the small
// parser included below, so nothing else is needed.
//
// Build & run:
//   g++ -std=c++17 -O2 bot.cpp -lcurl -o bot        (or: clang++ ..., or: make)
//   export POKER_TOKEN="pk_..."                        # your bot token
//   export POKER_URL="https://poker.example.com"  # optional, default http://localhost:8000
//   ./bot              # play tournaments
//   ./bot practice     # start a practice table against house bots first
//
// Only decide() needs to change to make the bot smarter.

#include <curl/curl.h>

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <map>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <variant>
#include <vector>

// ============================================================================ tiny JSON

struct Json;
using JsonArray = std::vector<Json>;
using JsonObject = std::map<std::string, Json>;

struct Json {
    std::variant<std::nullptr_t, bool, double, std::string, JsonArray, JsonObject> v;

    bool isNull() const { return std::holds_alternative<std::nullptr_t>(v); }
    bool asBool() const { return std::get<bool>(v); }
    long asInt() const { return static_cast<long>(std::get<double>(v)); }
    const std::string& asString() const { return std::get<std::string>(v); }
    const JsonArray& asArray() const { return std::get<JsonArray>(v); }
    const JsonObject& asObject() const { return std::get<JsonObject>(v); }
    const Json& operator[](const std::string& key) const {
        static const Json null{nullptr};
        const auto& o = asObject();
        auto it = o.find(key);
        return it == o.end() ? null : it->second;
    }
    const Json& operator[](size_t i) const { return asArray().at(i); }

    static Json parse(const std::string& s) {
        size_t i = 0;
        Json j = parseValue(s, i);
        return j;
    }

    std::string dump() const {
        std::ostringstream out;
        if (isNull()) out << "null";
        else if (auto b = std::get_if<bool>(&v)) out << (*b ? "true" : "false");
        else if (auto d = std::get_if<double>(&v)) out << static_cast<long long>(*d);
        else if (auto str = std::get_if<std::string>(&v)) out << quote(*str);
        else if (auto a = std::get_if<JsonArray>(&v)) {
            out << '[';
            for (size_t k = 0; k < a->size(); ++k) out << (k ? "," : "") << (*a)[k].dump();
            out << ']';
        } else {
            out << '{';
            bool first = true;
            for (const auto& [key, val] : std::get<JsonObject>(v)) {
                out << (first ? "" : ",") << quote(key) << ':' << val.dump();
                first = false;
            }
            out << '}';
        }
        return out.str();
    }

  private:
    static std::string quote(const std::string& s) {
        std::string out = "\"";
        for (char c : s) {
            if (c == '"' || c == '\\') out += '\\';
            out += c;
        }
        return out + "\"";
    }
    static void ws(const std::string& s, size_t& i) {
        while (i < s.size() && isspace(static_cast<unsigned char>(s[i]))) ++i;
    }
    static Json parseValue(const std::string& s, size_t& i) {
        ws(s, i);
        if (i >= s.size()) throw std::runtime_error("unexpected end of JSON");
        char c = s[i];
        if (c == '{') {
            JsonObject o;
            ++i; ws(s, i);
            if (s[i] == '}') { ++i; return Json{o}; }
            while (true) {
                ws(s, i);
                std::string key = parseValue(s, i).asString();
                ws(s, i); ++i;  // ':'
                o[key] = parseValue(s, i);
                ws(s, i);
                if (s[i++] == '}') return Json{o};  // otherwise ','
            }
        }
        if (c == '[') {
            JsonArray a;
            ++i; ws(s, i);
            if (s[i] == ']') { ++i; return Json{a}; }
            while (true) {
                a.push_back(parseValue(s, i));
                ws(s, i);
                if (s[i++] == ']') return Json{a};  // otherwise ','
            }
        }
        if (c == '"') {
            std::string out;
            ++i;
            while (s[i] != '"') {
                if (s[i] == '\\') {
                    char e = s[++i];
                    if (e == 'n') out += '\n';
                    else if (e == 't') out += '\t';
                    else if (e == 'u') { out += '?'; i += 4; }  // good enough for this API
                    else out += e;
                    ++i;
                } else {
                    out += s[i++];
                }
            }
            ++i;
            return Json{out};
        }
        if (s.compare(i, 4, "true") == 0) { i += 4; return Json{true}; }
        if (s.compare(i, 5, "false") == 0) { i += 5; return Json{false}; }
        if (s.compare(i, 4, "null") == 0) { i += 4; return Json{nullptr}; }
        size_t start = i;
        while (i < s.size() && std::string("+-0123456789.eE").find(s[i]) != std::string::npos) ++i;
        return Json{std::stod(s.substr(start, i - start))};
    }
};

// ============================================================================ your strategy

const std::string RANKS = "23456789TJQKA";

// Returns the action as JSON fields, e.g. {"action": "call"}.
JsonObject decide(const Json& state) {
    const Json& legal = state["legal"];
    int r1 = static_cast<int>(RANKS.find(state["hole_cards"][0].asString()[0]));
    int r2 = static_cast<int>(RANKS.find(state["hole_cards"][1].asString()[0]));
    long toCall = state["to_call"].asInt();
    long stack = state["stack"].asInt();
    int hi = std::max(r1, r2), lo = std::min(r1, r2);

    bool pair = r1 == r2;
    bool high = hi >= static_cast<int>(RANKS.find('T')) && lo >= static_cast<int>(RANKS.find('9'));
    bool strong = pair || high || hi == static_cast<int>(RANKS.find('A'));

    long bigBlind = state["blinds"]["big"].asInt();
    bool nobodyRaised = state["current_bet"].asInt() <= bigBlind;
    if (strong && !legal["raise"].isNull() && nobodyRaised) {
        // raise TO 3 big blinds (amount = your total bet on this street), within the legal range
        long amount = std::min(std::max(legal["raise"]["min"].asInt(), 3 * bigBlind), legal["raise"]["max"].asInt());
        return {{"action", Json{std::string("raise")}}, {"amount", Json{static_cast<double>(amount)}}};
    }
    if (legal["check"].asBool()) return {{"action", Json{std::string("check")}}};
    if (strong || toCall <= stack / 20) return {{"action", Json{std::string("call")}}};
    return {{"action", Json{std::string("fold")}}};
}

// ============================================================================ HTTP plumbing

std::string env(const char* name, const std::string& fallback) {
    const char* v = std::getenv(name);
    return v && *v ? v : fallback;
}

std::string BASE_URL = env("POKER_URL", "http://localhost:8000");
std::string TOKEN = env("POKER_TOKEN", "");

struct Reply {
    long status = 0;
    Json json{nullptr};
};

size_t collect(char* data, size_t size, size_t n, void* out) {
    static_cast<std::string*>(out)->append(data, size * n);
    return size * n;
}

Reply api(const std::string& method, const std::string& path, const JsonObject* body = nullptr) {
    std::unique_ptr<CURL, decltype(&curl_easy_cleanup)> curl(curl_easy_init(), curl_easy_cleanup);
    if (!curl) throw std::runtime_error("curl_easy_init failed");

    std::string response, payload;
    struct curl_slist* headers = nullptr;
    headers = curl_slist_append(headers, ("Authorization: Bearer " + TOKEN).c_str());
    if (body) {
        payload = Json{*body}.dump();
        headers = curl_slist_append(headers, "Content-Type: application/json");
        curl_easy_setopt(curl.get(), CURLOPT_POSTFIELDS, payload.c_str());
    }
    std::string url = BASE_URL + path;
    curl_easy_setopt(curl.get(), CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl.get(), CURLOPT_CUSTOMREQUEST, method.c_str());
    curl_easy_setopt(curl.get(), CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl.get(), CURLOPT_USERAGENT, "poker-pi-starter-bot/1.0 (c++)");
    curl_easy_setopt(curl.get(), CURLOPT_TIMEOUT, 40L);
    curl_easy_setopt(curl.get(), CURLOPT_WRITEFUNCTION, collect);
    curl_easy_setopt(curl.get(), CURLOPT_WRITEDATA, &response);

    CURLcode rc = curl_easy_perform(curl.get());
    curl_slist_free_all(headers);
    if (rc != CURLE_OK) throw std::runtime_error(curl_easy_strerror(rc));

    Reply r;
    curl_easy_getinfo(curl.get(), CURLINFO_RESPONSE_CODE, &r.status);
    if (!response.empty()) r.json = Json::parse(response);
    return r;
}

void registerForOpenTournaments() {
    Reply r = api("GET", "/api/v1/bot/tournaments");
    if (r.status != 200) {
        std::cout << "could not list tournaments: " << r.status << " " << r.json.dump() << "\n";
        return;
    }
    for (const Json& t : r.json.asArray()) {
        if (t["status"].asString() == "registering" && !t["registered"].asBool()) {
            Reply reg = api("POST", "/api/v1/bot/tournaments/" + std::to_string(t["id"].asInt()) + "/register");
            std::cout << "register for '" << t["name"].asString() << "': " << reg.status << "\n";
        }
    }
}

std::string join(const Json& cards) {
    std::string out;
    for (const Json& c : cards.asArray()) out += (out.empty() ? "" : " ") + c.asString();
    return out.empty() ? "-" : out;
}

int main(int argc, char** argv) {
    std::cout << std::unitbuf;  // show output immediately, even when redirected to a file
    if (TOKEN.empty()) {
        std::cerr << "Set the POKER_TOKEN environment variable to your bot token.\n";
        return 1;
    }
    while (!BASE_URL.empty() && BASE_URL.back() == '/') BASE_URL.pop_back();
    curl_global_init(CURL_GLOBAL_DEFAULT);

    Reply me = api("GET", "/api/v1/bot/me");
    if (me.status != 200) {
        std::cerr << "Token check failed (" << me.status << "): " << me.json.dump() << "\n";
        return 1;
    }
    std::cout << "Hello " << me.json["name"].asString() << "! Talking to " << BASE_URL << "\n";

    if (argc > 1 && std::string(argv[1]) == "practice") {
        JsonObject body{{"opponents", Json{JsonArray{Json{std::string("random")}, Json{std::string("station")},
                                                     Json{std::string("tight")}}}}};
        Reply p = api("POST", "/api/v1/bot/practice", &body);
        std::cout << "practice table: " << p.status << " " << p.json["watch_url"].asString() << "\n";
    }

    registerForOpenTournaments();
    auto lastCheck = std::chrono::steady_clock::now();

    while (true) {
        if (std::chrono::steady_clock::now() - lastCheck > std::chrono::minutes(5)) {
            registerForOpenTournaments();
            lastCheck = std::chrono::steady_clock::now();
        }
        Reply turn;
        try {
            turn = api("GET", "/api/v1/bot/turn?wait=25");
        } catch (const std::exception& e) {
            std::cout << "network error: " << e.what() << "\n";
            std::this_thread::sleep_for(std::chrono::seconds(2));
            continue;
        }
        if (turn.status == 204) continue;  // not our turn yet, ask again
        if (turn.status != 200) {
            std::cout << "unexpected answer: " << turn.status << " " << turn.json.dump() << "\n";
            std::this_thread::sleep_for(std::chrono::seconds(2));
            continue;
        }

        const Json& state = turn.json;
        JsonObject action = decide(state);
        JsonObject body = action;
        body["turn_id"] = state["turn_id"];
        Reply res = api("POST", "/api/v1/bot/action", &body);
        std::cout << "hand " << state["hand_id"].asInt() << " " << state["street"].asString() << " "
                  << join(state["hole_cards"]) << " | board " << join(state["board"]) << " -> "
                  << Json{action}.dump() << " [" << res.status << "]\n";
        if (res.status == 422) {
            // our action was not legal: say why, then play it safe so we do not time out
            std::cout << "  rejected: " << res.json.dump() << "\n";
            JsonObject safe{{"turn_id", state["turn_id"]},
                            {"action", Json{std::string(state["legal"]["check"].asBool() ? "check" : "fold")}}};
            api("POST", "/api/v1/bot/action", &safe);
        } else if (res.status != 200) {
            std::cout << "  server said: " << res.json.dump() << "\n";
        }
    }
}
