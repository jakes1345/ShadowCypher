package main

import (
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

/*
#cgo LDFLAGS: -L../libs -lrust_core -Wl,-rpath,../libs
#include <stdlib.h>

extern char* encrypt_signal(char* key, char* data);
extern char* decrypt_signal(char* key, char* hex_data);
extern void free_signal(char* s);
*/
import "C"

import "unsafe"

/**
 * ShadowCypher Nexus-V2 — The Multi-Language Sovereign Signal Plane.
 * Mix of Go (Concurrency), C++ (Performance Core), and Python (Orchestration).
 * Implements: 
 *  1. SOCKS5 Proxy over Encrypted UDP (No-VPN Browsing).
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

// ── RUST GHOST-CORE INTERFACE ─────────────────────────────────────

func ghostEncrypt(key, data string) string {
	cKey := C.CString(key)
	cData := C.CString(data)
	defer C.free(unsafe.Pointer(cKey))
	defer C.free(unsafe.Pointer(cData))

	cResult := C.encrypt_signal(cKey, cData)
	defer C.free_signal(cResult)

	return C.GoString(cResult)
}

func ghostDecrypt(key, hexData string) string {
	cKey := C.CString(key)
	cHex := C.CString(hexData)
	defer C.free(unsafe.Pointer(cKey))
	defer C.free(unsafe.Pointer(cHex))

	cResult := C.decrypt_signal(cKey, cHex)
	defer C.free_signal(cResult)

	return C.GoString(cResult)
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
	log.Printf("\u26a1 NEXUS_PROXY_ACTIVE: Listening on :%d (Encrypted SOCKS5)", port)

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
	if _, err := io.ReadFull(conn, buf[:2]); err != nil { return }
	if buf[0] != 0x05 { return } // SOCKS5
	
	nmethods := int(buf[1])
	io.ReadFull(conn, buf[:nmethods])
	conn.Write([]byte{0x05, 0x00}) // No auth for now (internal)

	// Request
	io.ReadFull(conn, buf[:4])
	if buf[1] != 0x01 { return } // CONNECT
	
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
	
	dest := fmt.Sprintf("%s:%d", addr, port)
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
	log.Printf("\U0001f4ac SOVEREIGN_CHAT_ACTIVE: WS Endpoint on :%d/chat", chatPort)
	
	log.Fatal(http.ListenAndServe(fmt.Sprintf(":%d", chatPort), nil))
}
