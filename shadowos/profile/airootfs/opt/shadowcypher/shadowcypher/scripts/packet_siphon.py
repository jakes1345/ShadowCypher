#!/usr/bin/env python3
"""
SHADOWCYPHER // PACKET SIPHON — Raw Socket Network Sniffer
Captures and parses live network traffic with protocol-level dissection.
Supports Ethernet, IP, TCP, UDP, ICMP, DNS, and HTTP protocol parsing.
Requires root privileges for raw socket access.

Usage:
    sudo python3 packet_siphon.py [-i INTERFACE] [-c COUNT] [-f FILTER] [--hex]
"""

import argparse
import os
import socket
import struct
import sys
import time

C = {"R":"\033[1;31m","G":"\033[1;32m","Y":"\033[1;33m","C":"\033[1;36m",
     "M":"\033[1;35m","D":"\033[0;37m","N":"\033[0m","B":"\033[1m"}

PROTO_MAP = {1:"ICMP", 6:"TCP", 17:"UDP"}

def mac_fmt(raw):
    return ":".join(f"{b:02x}" for b in raw)

def parse_ethernet(data):
    dst, src, proto = struct.unpack("!6s6sH", data[:14])
    return mac_fmt(dst), mac_fmt(src), proto, data[14:]

def parse_ip(data):
    ver_ihl = data[0]
    ihl = (ver_ihl & 0xF) * 4
    ttl = data[8]
    proto = data[9]
    src = socket.inet_ntoa(data[12:16])
    dst = socket.inet_ntoa(data[16:20])
    length = struct.unpack("!H", data[2:4])[0]
    return {"ihl":ihl,"ttl":ttl,"proto":proto,"src":src,"dst":dst,"len":length}, data[ihl:]

def parse_tcp(data):
    src_port, dst_port = struct.unpack("!HH", data[:4])
    seq, ack = struct.unpack("!II", data[4:12])
    offset = (data[12] >> 4) * 4
    flags = data[13]
    flag_str = ""
    if flags & 0x02:
        flag_str += "SYN "
    if flags & 0x10:
        flag_str += "ACK "
    if flags & 0x01:
        flag_str += "FIN "
    if flags & 0x04:
        flag_str += "RST "
    if flags & 0x08:
        flag_str += "PSH "
    if flags & 0x20:
        flag_str += "URG "
    return {"src":src_port,"dst":dst_port,"seq":seq,"ack":ack,"flags":flag_str.strip(),
            "offset":offset}, data[offset:]

def parse_udp(data):
    src_port, dst_port, length = struct.unpack("!HHH", data[:6])
    return {"src":src_port,"dst":dst_port,"len":length}, data[8:]

def parse_icmp(data):
    icmp_type, code, checksum = struct.unpack("!BBH", data[:4])
    type_names = {0:"Echo Reply",3:"Dest Unreachable",8:"Echo Request",11:"TTL Exceeded"}
    return {"type":icmp_type,"code":code,"name":type_names.get(icmp_type,"Other")}, data[4:]

def parse_dns(data):
    if len(data) < 12:
        return None
    qcount = struct.unpack("!H", data[4:6])[0]
    # Parse first question
    pos = 12
    labels = []
    while pos < len(data) and data[pos] != 0:
        length = data[pos]
        pos += 1
        labels.append(data[pos:pos+length].decode("ascii",errors="replace"))
        pos += length
    return {"query":".".join(labels),"questions":qcount}

def hexdump(data, max_bytes=64):
    lines = []
    for i in range(0, min(len(data), max_bytes), 16):
        chunk = data[i:i+16]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"    {i:04x}  {hex_part:<48}  {ascii_part}")
    return "\n".join(lines)

def main():
    if os.geteuid() != 0:
        print(f"{C['R']}[ERROR]{C['N']} Packet Siphon requires root. Run with sudo.")
        sys.exit(1)

    p = argparse.ArgumentParser(description="ShadowCypher Packet Siphon")
    p.add_argument("-i","--interface", default="", help="Bind to interface")
    p.add_argument("-c","--count", type=int, default=0, help="Packets to capture (0=inf)")
    p.add_argument("-f","--filter", default="", help="Filter: tcp, udp, icmp, dns, http")
    p.add_argument("--hex", action="store_true", help="Show hex dump of payload")
    p.add_argument("-o","--output", help="Save PCAP-like log to file")
    a = p.parse_args()

    print(f"\n{C['B']}{'='*70}{C['N']}")
    print(f" {C['C']}SHADOWCYPHER // PACKET SIPHON{C['N']}")
    print(f"{C['B']}{'='*70}{C['N']}")
    print(f"  Filter: {C['Y']}{a.filter or 'ALL'}{C['N']}  |  Count: {a.count or '∞'}")
    print(f"{C['B']}{'='*70}{C['N']}\n")

    try:
        sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(3))
        if a.interface:
            sock.bind((a.interface, 0))
    except PermissionError:
        print(f"{C['R']}[ERROR]{C['N']} Raw socket denied. Run as root.")
        sys.exit(1)
    except OSError as e:
        print(f"{C['R']}[ERROR]{C['N']} {e}")
        sys.exit(1)

    outfile = open(a.output, "w") if a.output else None
    captured = 0

    try:
        while True:
            raw, _ = sock.recvfrom(65535)
            eth_dst, eth_src, eth_proto, eth_payload = parse_ethernet(raw)

            if eth_proto != 0x0800:
                continue  # IPv4 only

            ip, ip_payload = parse_ip(eth_payload)
            # Apply filters
            if a.filter:
                filt = a.filter.lower()
                if filt == "tcp" and ip["proto"] != 6:
                    continue
                if filt == "udp" and ip["proto"] != 17:
                    continue
                if filt == "icmp" and ip["proto"] != 1:
                    continue

            ts = time.strftime("%H:%M:%S")
            line_parts = [f"  {C['D']}{ts}{C['N']}"]

            if ip["proto"] == 6:  # TCP
                tcp, payload = parse_tcp(ip_payload)
                if a.filter == "dns":
                    continue
                if a.filter == "http" and tcp["dst"] not in (80,443,8080,8443) and tcp["src"] not in (80,443,8080,8443):
                    continue
                line_parts.append(f"{C['G']}TCP{C['N']} {C['Y']}{ip['src']}:{tcp['src']}{C['N']} → {C['C']}{ip['dst']}:{tcp['dst']}{C['N']}  [{C['M']}{tcp['flags']}{C['N']}]  len={ip['len']}")

                # HTTP detection
                if payload and (payload[:4] in (b"GET ", b"POST", b"PUT ", b"HEAD", b"HTTP")):
                    first_line = payload.split(b"\r\n")[0].decode("utf-8", errors="replace")
                    line_parts.append(f"\n    {C['C']}HTTP: {first_line}{C['N']}")

            elif ip["proto"] == 17:  # UDP
                udp, payload = parse_udp(ip_payload)
                if a.filter == "http":
                    continue
                line_parts.append(f"{C['Y']}UDP{C['N']} {ip['src']}:{udp['src']} → {ip['dst']}:{udp['dst']}  len={udp['len']}")

                # DNS detection
                if udp["dst"] == 53 or udp["src"] == 53:
                    dns = parse_dns(payload)
                    if dns:
                        line_parts.append(f"\n    {C['M']}DNS: {dns['query']}{C['N']}")
                elif a.filter == "dns":
                    continue

            elif ip["proto"] == 1:  # ICMP
                icmp, payload = parse_icmp(ip_payload)
                if a.filter in ("dns","http"):
                    continue
                line_parts.append(f"{C['R']}ICMP{C['N']} {ip['src']} → {ip['dst']}  type={icmp['type']} ({icmp['name']})")
            else:
                continue

            output = " ".join(line_parts)
            print(output)

            if a.hex and ip_payload:
                print(hexdump(ip_payload))

            if outfile:
                outfile.write(output.replace("\033[", "ESC[") + "\n")

            captured += 1
            if a.count and captured >= a.count:
                break

    except KeyboardInterrupt:
        print(f"\n\n  {C['G']}Captured {captured} packets{C['N']}")
    finally:
        sock.close()
        if outfile:
            outfile.close()

if __name__ == "__main__":
    main()
