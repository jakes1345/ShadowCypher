import { shortest } from "@antiwork/shortest";

// Network Tools
shortest("Log in with 'admin'/'shadow', click 'Tools' in the sidebar, and verify the Network Tools page shows Ping, Traceroute, DNS Lookup, Whois, Port Check, Nmap Scan, IP Lookup, HTTP Headers, Speed Test, Wake-on-LAN, DNS Benchmark, and Network Doctor tools");

shortest("On the Tools page, the Ping tool should have already auto-run against 8.8.8.8 — verify the output shows ping statistics with round-trip times, not 'Loading...'");

shortest("On the Tools page, click Run on the DNS Lookup tool for 'google.com' and verify the output shows DNS records");

shortest("On the Tools page, click the 'Test DNS Latency' button in the DNS Benchmark section and verify results appear showing Cloudflare, Google, Quad9, and OpenDNS with latency values");
