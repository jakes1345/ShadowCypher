package main

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool { return true },
}

type Message struct {
	Type    string   `json:"type"`
	Nick    string   `json:"nick,omitempty"`
	Channel string   `json:"channel,omitempty"`
	Text    string   `json:"text,omitempty"`
	Target  string   `json:"target,omitempty"`
	Peers   []string `json:"peers,omitempty"`
	MissionID string `json:"mission_id,omitempty"`
}

type RelayStatus struct {
	ShadowID   string   `json:"shadow_id"`
	Uptime     string   `json:"uptime"`
	PeersCount int      `json:"peers_count"`
	Peers      []string `json:"peers"`
	ClientsCount int    `json:"clients_count"`
}

type RelayServer struct {
	clients    map[chan Message]string
	peers      map[string]time.Time 
	clientsMux sync.Mutex
	peersMux   sync.Mutex
	broadcast  chan Message
	beaconURL  string
	shadowID   string
	startTime  time.Time
}

func (s *RelayServer) GenerateShadowID() {
	b := make([]byte, 8)
	rand.Read(b)
	s.shadowID = hex.EncodeToString(b)
}

func NewRelayServer(beacon string) *RelayServer {
	s := &RelayServer{
		clients:   make(map[chan Message]string),
		peers:     make(map[string]time.Time),
		broadcast: make(chan Message),
		beaconURL: beacon,
		startTime: time.Now(),
	}
	s.GenerateShadowID()
	log.Printf("\u26a1 ABSOLUT_GHOST: Transient Identity Initialized [%s]", s.shadowID)
	return s
}

// ── SWARM: Gossip Protocol ──────────────────────────────────────

func (s *RelayServer) gossip() {
	ticker := time.NewTicker(30 * time.Second)
	for range ticker.C {
		s.peersMux.Lock()
		activePeers := make([]string, 0, len(s.peers))
		for p, lastSeen := range s.peers {
			if time.Since(lastSeen) < 10*time.Minute {
				activePeers = append(activePeers, p)
			}
		}
		s.peersMux.Unlock()

		if len(activePeers) > 0 {
			msg := Message{Type: "gossip", Peers: activePeers}
			s.broadcast <- msg
			log.Printf("[SWARM] Gossiping %d peers to local clients", len(activePeers))
		}
	}
}

// ── Admin API: Telemetry ────────────────────────────────────────

func (s *RelayServer) handleStatus(w http.ResponseWriter, r *http.Request) {
	s.peersMux.Lock()
	activePeers := make([]string, 0, len(s.peers))
	for p := range s.peers {
		activePeers = append(activePeers, p)
	}
	s.peersMux.Unlock()

	s.clientsMux.Lock()
	clientsLen := len(s.clients)
	s.clientsMux.Unlock()

	status := RelayStatus{
		ShadowID:     s.shadowID,
		Uptime:       time.Since(s.startTime).String(),
		PeersCount:   len(activePeers),
		Peers:        activePeers,
		ClientsCount: clientsLen,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(status)
}

// ── WebSocket: Swarm Delivery ───────────────────────────────────

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

	// Broadcaster loop for this client
	go func() {
		for msg := range ch {
			if err := conn.WriteJSON(msg); err != nil {
				break
			}
		}
	}()

	for {
		mt, msgBytes, err := conn.ReadMessage()
		if err != nil {
			break
		}

		if mt == websocket.BinaryMessage {
			s.handleBinaryFrame(msgBytes)
			continue
		}

		var msg Message
		if err := json.Unmarshal(msgBytes, &msg); err == nil {
			if msg.Type == "gossip" {
				s.syncPeers(msg.Peers)
			}
			s.broadcast <- msg
		}
	}
}

func (s *RelayServer) handleTitanFrame(data []byte) {
	if len(data) < 3 { return }
	
	opCode := data[0]
	missionID := (uint16(data[1]) << 8) | uint16(data[2])
	
	switch opCode {
	case 0xA1: // AI_DELEGATION
		log.Printf("[TITAN] INGESTED: Autonomous Intelligence Link (MSN:%d)", missionID)
		// Route to OpenControl Gateway if target specified in next bytes
	case 0xB2: // SWARM_SYNC
		log.Printf("[TITAN] INGESTED: High-Velocity Swarm Discovery (MSN:%d)", missionID)
	case 0xC3: // MEM_STRIKE
		log.Printf("[TITAN] INGESTED: DIRECT_MEMORY_STRIKE (MSN:%d)", missionID)
	}
}

func (s *RelayServer) handleBinaryFrame(data []byte) {
	if len(data) < 1 { return }
	if data[0] == 0x99 {
		s.handleTitanFrame(data[1:])
		return
	}
}

func (s *RelayServer) syncPeers(peers []string) {
	s.peersMux.Lock()
	defer s.peersMux.Unlock()
	for _, p := range peers {
		s.peers[p] = time.Now()
	}
}

func (s *RelayServer) startBroadcaster() {
	for msg := range s.broadcast {
		s.clientsMux.Lock()
		for ch := range s.clients {
			select {
			case ch <- msg:
			default:
			}
		}
		s.clientsMux.Unlock()
	}
}

func (s *RelayServer) pulse() {
	ticker := time.NewTicker(5 * time.Second)
	for range ticker.C {
		s.peersMux.Lock()
		count := len(s.peers)
		s.peersMux.Unlock()

		msg := Message{
			Type: "status",
			Text: s.shadowID,
			Peers: []string{s.startTime.Format(time.RFC3339)}, // Hack to send uptime via existing struct
			Target: string(rune(count)), // Sending count as char to save bytes
		}
		s.broadcast <- msg
	}
}

func main() {
	port := "8888"
	if p := os.Getenv("SHADOW_PORT"); p != "" {
		port = p
	}

	server := NewRelayServer("")
	go server.startBroadcaster()
	go server.gossip()
	go server.pulse()

	http.HandleFunc("/ws", server.handleWS)
	http.HandleFunc("/api/status", server.handleStatus)

	log.Printf("\u26a1 SWARM_BRIDGE_ACTIVE: Frequency :%s", port)
	if err := http.ListenAndServe(":"+port, nil); err != nil {
		log.Fatalf("NATIVE_FATAL: %v", err)
	}
}
