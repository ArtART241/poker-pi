// poker-pi starter bot (Go 1.21+, standard library only).
//
// Run:
//
//	export POKER_TOKEN="pk_..."                          # your bot token
//	export POKER_URL="https://poker.example.com"    # optional, default http://localhost:8000
//	go run .              # play tournaments
//	go run . practice     # start a practice table against house bots first
//
// Only decide() needs to change to make the bot smarter.
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"time"
)

const ranks = "23456789TJQKA"

var (
	baseURL = strings.TrimRight(getenv("POKER_URL", "http://localhost:8000"), "/")
	token   = os.Getenv("POKER_TOKEN")
	client  = &http.Client{Timeout: 40 * time.Second}
)

// ----------------------------------------------------------------------------- game state

type RaiseRange struct {
	Min int `json:"min"`
	Max int `json:"max"`
}

type Legal struct {
	Fold  bool        `json:"fold"`
	Check bool        `json:"check"`
	Call  *int        `json:"call"`  // nil if there is nothing to call
	Raise *RaiseRange `json:"raise"` // nil if raising is not allowed
}

type Blinds struct {
	Small int `json:"small"`
	Big   int `json:"big"`
	Ante  int `json:"ante"`
	Level int `json:"level"`
}

type Player struct {
	Seat   int    `json:"seat"`
	Name   string `json:"name"`
	Stack  int    `json:"stack"`
	Bet    int    `json:"bet"`
	Status string `json:"status"`
	IsYou  bool   `json:"is_you"`
}

type State struct {
	TurnID     string           `json:"turn_id"`
	DeadlineMs int              `json:"deadline_ms"`
	HandID     int              `json:"hand_id"`
	Seat       int              `json:"seat"`
	HoleCards  []string         `json:"hole_cards"`
	Stack      int              `json:"stack"`
	Bet        int              `json:"bet"`
	Street     string           `json:"street"`
	Board      []string         `json:"board"`
	Pot        int              `json:"pot"`
	CurrentBet int              `json:"current_bet"`
	ToCall     int              `json:"to_call"`
	Legal      Legal            `json:"legal"`
	Blinds     Blinds           `json:"blinds"`
	Button     int              `json:"button"`
	Players    []Player         `json:"players"`
	ActionLog  []map[string]any `json:"action_log"`
}

type Action struct {
	TurnID string `json:"turn_id"`
	Action string `json:"action"`
	Amount *int   `json:"amount,omitempty"`
}

// ----------------------------------------------------------------------------- your strategy

func decide(s State) Action {
	r1 := strings.IndexByte(ranks, s.HoleCards[0][0])
	r2 := strings.IndexByte(ranks, s.HoleCards[1][0])
	hi, lo := max(r1, r2), min(r1, r2)

	pair := r1 == r2
	high := hi >= strings.IndexByte(ranks, 'T') && lo >= strings.IndexByte(ranks, '9')
	strong := pair || high || hi == strings.IndexByte(ranks, 'A')

	bigBlind := s.Blinds.Big
	nobodyRaised := s.CurrentBet <= bigBlind

	switch {
	case strong && s.Legal.Raise != nil && nobodyRaised:
		// raise TO 3 big blinds (amount = your total bet on this street), within the legal range
		amount := min(max(s.Legal.Raise.Min, 3*bigBlind), s.Legal.Raise.Max)
		return Action{Action: "raise", Amount: &amount}
	case s.Legal.Check:
		return Action{Action: "check"}
	case strong || s.ToCall <= s.Stack/20:
		return Action{Action: "call"}
	default:
		return Action{Action: "fold"}
	}
}

// ----------------------------------------------------------------------------- HTTP plumbing

func getenv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

// api sends a request and decodes the JSON answer into out (if out != nil and there is a body).
func api(method, path string, body any, out any) (int, error) {
	var reader io.Reader
	if body != nil {
		data, err := json.Marshal(body)
		if err != nil {
			return 0, err
		}
		reader = bytes.NewReader(data)
	}
	req, err := http.NewRequest(method, baseURL+path, reader)
	if err != nil {
		return 0, err
	}
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("User-Agent", "poker-pi-starter-bot/1.0 (go)")
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := client.Do(req)
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return resp.StatusCode, err
	}
	if resp.StatusCode >= 400 {
		return resp.StatusCode, fmt.Errorf("server said: %s", raw)
	}
	if out != nil && len(raw) > 0 {
		return resp.StatusCode, json.Unmarshal(raw, out)
	}
	return resp.StatusCode, nil
}

func registerForOpenTournaments() {
	var tournaments []struct {
		ID         int    `json:"id"`
		Name       string `json:"name"`
		Status     string `json:"status"`
		StartAt    string `json:"start_at"`
		Registered bool   `json:"registered"`
	}
	if _, err := api("GET", "/api/v1/bot/tournaments", nil, &tournaments); err != nil {
		log.Println("could not list tournaments:", err)
		return
	}
	for _, t := range tournaments {
		if t.Status == "registering" && !t.Registered {
			status, err := api("POST", fmt.Sprintf("/api/v1/bot/tournaments/%d/register", t.ID), nil, nil)
			log.Printf("register for '%s' (starts %s): %d %v", t.Name, t.StartAt, status, err)
		}
	}
}

func main() {
	if token == "" {
		log.Fatal("Set the POKER_TOKEN environment variable to your bot token.")
	}
	var me struct {
		Name string `json:"name"`
	}
	if status, err := api("GET", "/api/v1/bot/me", nil, &me); err != nil {
		log.Fatalf("Token check failed (%d): %v", status, err)
	}
	log.Printf("Hello %s! Talking to %s", me.Name, baseURL)

	if len(os.Args) > 1 && os.Args[1] == "practice" {
		var table struct {
			WatchURL string `json:"watch_url"`
		}
		body := map[string]any{"opponents": []string{"random", "station", "tight"}}
		status, err := api("POST", "/api/v1/bot/practice", body, &table)
		log.Println("practice table:", status, table.WatchURL, err)
	}

	registerForOpenTournaments()
	lastCheck := time.Now()

	for {
		if time.Since(lastCheck) > 5*time.Minute {
			registerForOpenTournaments()
			lastCheck = time.Now()
		}
		var state State
		status, err := api("GET", "/api/v1/bot/turn?wait=25", nil, &state)
		if err != nil {
			log.Println("error while waiting for a turn:", status, err)
			time.Sleep(2 * time.Second)
			continue
		}
		if status == http.StatusNoContent { // not our turn yet, ask again
			continue
		}

		action := decide(state)
		action.TurnID = state.TurnID
		status, err = api("POST", "/api/v1/bot/action", action, nil)
		amount := ""
		if action.Amount != nil {
			amount = fmt.Sprint(*action.Amount)
		}
		log.Printf("hand %d %-7s %v | board %v -> %s %s [%d]",
			state.HandID, state.Street, state.HoleCards, state.Board, action.Action, amount, status)
		if status == http.StatusUnprocessableEntity {
			// our action was not legal: say why, then play it safe so we do not time out
			log.Println("  rejected:", err)
			safe := Action{TurnID: state.TurnID, Action: "fold"}
			if state.Legal.Check {
				safe.Action = "check"
			}
			api("POST", "/api/v1/bot/action", safe, nil)
		} else if err != nil {
			log.Println("  ", err)
		}
	}
}
