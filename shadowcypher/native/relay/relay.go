package main

import (
	"bufio"
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net"
	"net/http"
	"strings"
	"sync"

	"github.com/gorilla/websocket"
	_ "modernc.org/sqlite" // Pure Go SQLite (No CGO required)
)

// SovereignRelay V2.1 — Static Native Backbone (Pure Go).
// 100% Portable. zero-dependency runtime.

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool { return true },
}

type Message struct {
	Type    string `json:"type"`
	Nick    string `json:"nick,omitempty"`
	Channel string `json:"channel,omitempty"`
	Text    string `json:"text,omitempty"`
	Target  string `json:"target,omitempty"`
}

type RelayServer struct {
	clients    map[chan Message]string
	clientsMux sync.Mutex
	broadcast  chan Message
	db         *sql.DB
}

func NewRelayServer() *RelayServer {
	// Initialize Pure Go Persistent Tactical Registry
	db, err := sql.Open("sqlite", "./sovereign.db")
	if err != nil {
		log.Fatalf("DB_INIT_FAILED: %v", err)
	}

	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS users (
		nick TEXT PRIMARY KEY,
		xp INTEGER DEFAULT 0,
		level INTEGER DEFAULT 1,
		power TEXT DEFAULT 'user',
		last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
	)`)
	if err != nil {
		log.Fatalf("SCHEMA_INIT_FAILED: %v", err)
	}

	return &RelayServer{
		clients:   make(map[chan Message]string),
		broadcast: make(chan Message),
		db:        db,
	}
}

func (s *RelayServer) handleWS(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		return
	}
	defer conn.Close()

	ch := make(chan Message)
	s.clientsMux.Lock()
	s.clients[ch] = "anonymous"
	s.clientsMux.Unlock()

	defer func() {
		s.clientsMux.Lock()
		delete(s.clients, ch)
		s.clientsMux.Unlock()
	}()

	log.Printf("[UNMASK] WebSocket incoming from %s", r.RemoteAddr)

	for {
		_, msgBytes, err := conn.ReadMessage()
		if err != nil {
			break
		}
		var msg Message
		if err := json.Unmarshal(msgBytes, &msg); err == nil {
			if msg.Type == "auth" {
				s.clientsMux.Lock()
				s.clients[ch] = msg.Nick
				s.clientsMux.Unlock()
				s.registerUser(msg.Nick)
			}
			s.broadcast <- msg
		}
	}
}

func (s *RelayServer) registerUser(nick string) {
	_, _ = s.db.Exec("INSERT OR IGNORE INTO users (nick) VALUES (?)", nick)
	_, _ = s.db.Exec("UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE nick = ?", nick)
}

func (s *RelayServer) handleIRC(conn net.Conn) {
	defer conn.Close()
	scanner := bufio.NewScanner(conn)
	var nick string

	for scanner.Scan() {
		line := scanner.Text()
		parts := strings.Split(line, " ")
		if len(parts) < 2 {
			continue
		}

		cmd := strings.ToUpper(parts[0])
		switch cmd {
		case "NICK":
			nick = parts[1]
			s.registerUser(nick)
		case "USER":
			fmt.Fprintf(conn, ":sovereign 001 %s :Welcome to Sovereign Hub (Native Pure-Go)\r\n", nick)
			fmt.Fprintf(conn, ":sovereign 376 %s :End of MOTD\r\n", nick)
		case "PRIVMSG":
			target := parts[1]
			text := strings.Join(parts[2:], " ")
			if strings.HasPrefix(text, ":") {
				text = text[1:]
			}
			s.broadcast <- Message{Type: "chat", Nick: nick, Channel: target, Text: text}
		case "PING":
			fmt.Fprintf(conn, "PONG %s\r\n", parts[1])
		}
	}
}

func (s *RelayServer) startBroadcaster() {
	for msg := range s.broadcast {
		s.clientsMux.Lock()
		for ch := range s.clients {
			ch <- msg
		}
		s.clientsMux.Unlock()
	}
}

func main() {
	server := NewRelayServer()
	go server.startBroadcaster()

	// High-Concurrency Multi-plex Listening Engine
	http.HandleFunc("/ws", server.handleWS)
	go func() {
		log.Println("[GO_CORE] Sovereign WS Relay active on :8888")
		_ = http.ListenAndServe(":8888", nil)
	}()

	ln, _ := net.Listen("tcp", ":6667")
	log.Println("[GO_CORE] Sovereign IRC Relay active on :6667")
	for {
		conn, _ := ln.Accept()
		go server.handleIRC(conn)
		// Rate limiting and de-cloaking probes could go here
	}
}
