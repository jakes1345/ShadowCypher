#!/usr/bin/env python3
"""
DNS Tunnel Detector using tcpdump output
"""

import sys
from collections import defaultdict

def analyze_dns_capture(filename):
    try:
        # Read DNS query data from the capture file
        dns_queries = []
        
        with open(filename, 'r') as f:
            for line in f:
                if "QUERY" in line and "IN A" not in line:  # Filter out normal A records
                    parts = line.split()
                    subdomain_parts = [p.strip('"') for p in parts[1:-2] if "'" not in p]
                    dns_queries.extend(subdomain_parts)
        
        # Analyze patterns
        domain_stats = defaultdict(int)
        max_length = 0
        
        for q in dns_queries:
            length = len(q.split('.')[0])  # First label only
            
            if length > max_length:
                max_length = length
                
            if len(dns_queries) >= 5:  # Only analyze meaningful samples
                domain_stats[q] += 1
                
        
        # Report findings
        print(f"DNS Tunnel Analysis Results ({filename}):")
        print(f"Total DNS Queries Sampled: {len(dns_queries)}")
        print(f"Longest Subdomain Label Length: {max_length}")
        
        if max_length > 40:
            print("⚠️ Warning: Long subdomain lengths detected (>40 chars)")
            
        common = sorted(domain_stats.items(), key=lambda x: x[1], reverse=True)
        top_domains = [d for d, c in common[:3]]  # Top offenders
        
        if len(top_domains) > 2:
            print("Common repeated domains:", ", ".join(top_domains))
        
    except FileNotFoundError as e:
        print(f"Error: Capture file not found ({filename})")
        sys.exit(1)

if __name__ == "__main__":
    analyze_dns_capture('dns_capture.pcap')