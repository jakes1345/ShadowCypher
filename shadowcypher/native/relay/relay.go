package main

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"log"
	"net"
	"net/http"
	"os"
	"strconv"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		host, _, err := net.SplitHostPort(r.RemoteAddr)
		if err != nil {
			return false
		}
		return host == "127.0.0.1" || host == "::1"
	},
}

type Message struct {
	Type      string   `json:"type"`
	Nick      string   `json:"nick,omitempty"`
	Channel   string   `json:"channel,omitempty"`
	Text      string   `json:"text,omitempty"`
	Target    string   `json:"target,omitempty"`
	Peers     []string `json:"peers,omitempty"`
	PeerCount int      `json:"peer_count,omitempty"`
	MissionID string   `json:"mission_id,omitempty"`
	Auth      string   `json:"auth_token,omitempty"`
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
	authToken  string // The "Sovereign Key"
	startTime  time.Time
}

func (s *RelayServer) GenerateShadowID() {
	b := make([]byte, 8)
	rand.Read(b)
	s.shadowID = hex.EncodeToString(b)
	
	// Generate a unique session token
	t := make([]byte, 16)
	rand.Read(t)
	s.authToken = hex.EncodeToString(t)
	
	// Save token to temporary file for Python to read (Citadel Handshake)
	os.WriteFile(".relay_token", []byte(s.authToken), 0600)
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
	log.Printf("\u1f512 SOVEREIGN_KEY_GENERATED: citadel-to-relay handshake ready.")
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
		}
	}
}

// ── Admin API: Telemetry ────────────────────────────────────────

func (s *RelayServer) handleStatus(w http.ResponseWriter, r *http.Request) {
	host, _, _ := net.SplitHostPort(r.RemoteAddr)
	if host != "127.0.0.1" && host != "::1" {
		http.Error(w, "SOVEREIGN_REJECTION", 403)
		return
	}

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
	
	// APEX_HARDENING: Initial Handshake
	_, msgBytes, err := conn.ReadMessage()
	if err != nil { return }
	
	var authMsg Message
	if err := json.Unmarshal(msgBytes, &authMsg); err != nil || authMsg.Auth != s.authToken {
		log.Printf("[REJECT] UNAUTHORIZED_CONNECTION_ATTEMPT: IP %s", r.RemoteAddr)
		return
	}

	s.clientsMux.Lock()
	s.clients[ch] = "authenticated_citadel"
	s.clientsMux.Unlock()

	log.Printf("[AUTH] CITADEL_LINKED: Secure signal bridge established.")

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
	
	msg := Message{Type: "titan_event", MissionID: strconv.Itoa(int(missionID))}
	
	switch opCode {
	case 0xA1: // AI_DELEGATION
		msg.Text = "AI_DELEGATION"
		log.Printf("[TITAN] INGESTED: Autonomous Intelligence Link (MSN:%d)", missionID)
	case 0xB2: // SWARM_SYNC
		msg.Text = "SWARM_SYNC"
		log.Printf("[TITAN] INGESTED: High-Velocity Swarm Discovery (MSN:%d)", missionID)
	case 0xC3: // MEM_STRIKE
		msg.Text = "MEM_STRIKE"
		log.Printf("[TITAN] INGESTED: DIRECT_MEMORY_STRIKE (MSN:%d)", missionID)
	default:
		return
	}
	
	s.broadcast <- msg
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
			Type:      "status",
			Text:      s.shadowID,
			PeerCount: count,
			Peers:     []string{s.startTime.Format(time.RFC3339)},
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

	log.Printf("\u26a1 SWARM_BRIDGE_ACTIVE: Secure Signal Plane :%s", port)
	if err := http.ListenAndServe("127.0.0.1:"+port, nil); err != nil {
		log.Fatalf("NATIVE_FATAL: %v", err)
	}
}
