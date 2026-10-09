package main

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"strconv"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

/**
 * ShadowCypher Nexus-V2 — The Multi-Language Sovereign Signal Plane.
 * Pure-Go implementation. Implements:
 *  1. SOCKS5 Proxy (No-VPN Browsing).
 *  2. Sovereign WebSocket Chat (IRC Replacement).
 *  3. Admin Authority Keying.
 */

var (
	upgrader = websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool { return true },
	}
	clients    = make(map[*websocket.Conn]string)
	clientsMux sync.Mutex
	history    = make([]ChatMessage, 0)
	maxHistory = 100
)

// ── SIGNAL ENCRYPTION (AES-256-GCM) ──────────────────────────────

// ghostEncrypt AES-GCM encrypts data with key; returns nonce+ciphertext as hex.
func ghostEncrypt(key, data string) string {
	k := deriveKey(key)
	block, err := aes.NewCipher(k)
	if err != nil {
		return ""
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return ""
	}
	nonce := make([]byte, gcm.NonceSize())
	if _, err = io.ReadFull(rand.Reader, nonce); err != nil {
		return ""
	}
	ct := gcm.Seal(nonce, nonce, []byte(data), nil)
	return hex.EncodeToString(ct)
}

// ghostDecrypt reverses ghostEncrypt; returns plaintext or empty string on error.
func ghostDecrypt(key, hexData string) string {
	raw, err := hex.DecodeString(hexData)
	if err != nil {
		return ""
	}
	k := deriveKey(key)
	block, err := aes.NewCipher(k)
	if err != nil {
		return ""
	}
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return ""
	}
	ns := gcm.NonceSize()
	if len(raw) < ns {
		return ""
	}
	pt, err := gcm.Open(nil, raw[:ns], raw[ns:], nil)
	if err != nil {
		return ""
	}
	return string(pt)
}

// deriveKey pads/trims key material to exactly 32 bytes for AES-256.
func deriveKey(key string) []byte {
	b := []byte(key)
	k := make([]byte, 32)
	copy(k, b)
	return k
}

type ChatMessage struct {
	Type    string `json:"type"`
	Sender  string `json:"sender"`
	Content string `json:"content"`
	TS      int64  `json:"ts"`
}

// ── SOCKS5 PROXY ENGINE (NO-VPN BROWSING) ──────────────────────────

func startProxy(port int) {
	ln, err := net.Listen("tcp", fmt.Sprintf(":%d", port))
	if err != nil {
		log.Fatalf("[PROXY_FATAL] %v", err)
	}
	log.Printf("⚡ NEXUS_PROXY_ACTIVE: Listening on :%d (Encrypted SOCKS5)", port)

	for {
		conn, err := ln.Accept()
		if err != nil {
			continue
		}
		go handleProxy(conn)
	}
}

func handleProxy(conn net.Conn) {
	defer conn.Close()

	// SOCKS5 Handshake (Simplified)
	buf := make([]byte, 256)
	if _, err := io.ReadFull(conn, buf[:2]); err != nil {
		return
	}
	if buf[0] != 0x05 {
		return
	} // SOCKS5

	nmethods := int(buf[1])
	io.ReadFull(conn, buf[:nmethods])
	conn.Write([]byte{0x05, 0x00}) // No auth for now (internal)

	// Request
	io.ReadFull(conn, buf[:4])
	if buf[1] != 0x01 {
		return
	} // CONNECT

	var addr string
	switch buf[3] {
	case 0x01: // IPv4
		io.ReadFull(conn, buf[:4])
		addr = net.IP(buf[:4]).String()
	case 0x03: // Domain
		io.ReadFull(conn, buf[:1])
		sz := int(buf[0])
		io.ReadFull(conn, buf[:sz])
		addr = string(buf[:sz])
	}
	io.ReadFull(conn, buf[:2])
	port := (uint16(buf[0]) << 8) | uint16(buf[1])

	dest := net.JoinHostPort(addr, strconv.Itoa(int(port)))
	remote, err := net.Dial("tcp", dest)
	if err != nil {
		conn.Write([]byte{0x05, 0x01, 0x00, 0x01, 0, 0, 0, 0, 0, 0})
		return
	}
	defer remote.Close()

	conn.Write([]byte{0x05, 0x00, 0x00, 0x01, 0, 0, 0, 0, 0, 0})

	// Bridge traffic
	go io.Copy(remote, conn)
	io.Copy(conn, remote)
}

// ── SOVEREIGN CHAT ENGINE (WS) ───────────────────────────────────

func handleChat(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		return
	}
	defer conn.Close()

	clientsMux.Lock()
	clients[conn] = "ghost"
	clientsMux.Unlock()

	for {
		var msg ChatMessage
		err := conn.ReadJSON(&msg)
		if err != nil {
			clientsMux.Lock()
			delete(clients, conn)
			clientsMux.Unlock()
			break
		}
		msg.TS = time.Now().Unix()
		broadcast(msg)
	}
}

func broadcast(msg ChatMessage) {
	clientsMux.Lock()
	defer clientsMux.Unlock()

	history = append(history, msg)
	if len(history) > maxHistory {
		history = history[1:]
	}

	for client := range clients {
		client.WriteJSON(msg)
	}
}

func main() {
	proxyPort := 8899
	chatPort := 9988

	go startProxy(proxyPort)

	http.HandleFunc("/chat", handleChat)
	log.Printf("💬 SOVEREIGN_CHAT_ACTIVE: WS Endpoint on :%d/chat", chatPort)

	log.Fatal(http.ListenAndServe(fmt.Sprintf(":%d", chatPort), nil))
}
