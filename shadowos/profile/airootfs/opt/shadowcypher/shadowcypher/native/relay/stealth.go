package main

import (
	"fmt"
	"net/http"
	"net/url"
	"time"
	"golang.org/x/net/proxy"
)

// ShadowStealth — Multi-hop Onion Routing & IP Obfuscation.
// Forces all outgoing tactical traffic through the Tor network.

type StealthClient struct {
	HttpClient *http.Client
}

func NewStealthClient(torPort string) (*StealthClient, error) {
	// 1. Setup SOCKS5 Proxy for Tor
	proxyURL, err := url.Parse("socks5://127.0.0.1:" + torPort)
	if err != nil {
		return nil, err
	}

	dialer, err := proxy.FromURL(proxyURL, proxy.Direct)
	if err != nil {
		return nil, err
	}

	// 2. Wrap in HTTP Transport
	transport := &http.Client{
		Transport: &http.Transport{
			Dial: dialer.Dial,
		},
		Timeout: 30 * time.Second,
	}

	fmt.Printf("\u26d1 STEALTH_ACTIVE: Onion Circuit locked on port %s\n", torPort)
	return &StealthClient{HttpClient: transport}, nil
}

func (c *StealthClient) Send(req *http.Request) (*http.Response, error) {
	// Add obfuscation headers before sending
	req.Header.Set("X-Forwarded-For", "127.0.0.1") // Simple decoy
	return c.HttpClient.Do(req)
}
