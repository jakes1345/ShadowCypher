"""
SSH Tunnel Module — Pivot, Proxy, and Persist over SSH.
Handles local/remote forwarding, dynamic SOCKS proxies, reverse shells,
multi-hop proxy chaining, and session cleanup.
"""

import subprocess
import threading
from typing import List, Optional

from shadowcypher.core.module import BaseModule
from shadowcypher.core.runner import runner
from shadowcypher.core.sanitize import validate_port, validate_target


class SSHTunnel(BaseModule):
    """Persistent SSH tunnel engine for pivoting and proxying."""

    def __init__(self):
        super().__init__(module_name="ssh_tunnel")
        self._tunnel_pids: List[int] = []
        self._lock = threading.Lock()

    # ── Helpers ──

    def _build_base_args(self, ssh_host: str, ssh_user: str, key_file: Optional[str] = None) -> List[str]:
        """Construct shared SSH arguments: identity, user@host, no-TTY, keep-alive."""
        args = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=3",
            "-o", "ExitOnForwardFailure=yes",
            "-N",
        ]
        if key_file:
            args += ["-i", key_file]
        args.append(f"{ssh_user}@{ssh_host}")
        return args

    def _track_pid_output(self, on_output, pid_holder: dict):
        """Wrap output callback; extract PID when process starts."""
        def wrapper(line: str):
            if on_output:
                on_output(line)
        return wrapper

    # ── Core tunnel launcher that tracks PIDs ──

    def _launch_tunnel(self, task_name: str, args: List[str], on_output=None) -> str:
        """Launch a tunnel via runner and record the spawned PID."""
        task_id = runner.execute_task(task_name, args, callback=on_output)
        self.active_tasks.append(task_id)
        with self._lock:
            # Record task_id so kill_tunnels can stop it via runner
            self._tunnel_pids.append(task_id)
        return task_id

    # ── Forwarding methods ──

    def local_forward(
        self,
        local_port: int,
        remote_host: str,
        remote_port: int,
        ssh_host: str,
        ssh_user: str,
        key_file: Optional[str] = None,
        on_output=None,
    ) -> Optional[str]:
        """
        Local port forwarding: ssh -L local_port:remote_host:remote_port ssh_user@ssh_host
        Binds local_port on localhost and forwards it through the SSH server to remote_host:remote_port.
        """
        if not validate_port(local_port) or not validate_port(remote_port):
            if on_output:
                on_output(f"[SSH_TUNNEL] ERROR: invalid port(s) {local_port}/{remote_port}\n")
            return None
        if not validate_target(ssh_host) or not validate_target(remote_host):
            if on_output:
                on_output("[SSH_TUNNEL] ERROR: invalid host(s)\n")
            return None

        args = self._build_base_args(ssh_host, ssh_user, key_file)
        # Insert -L before the user@host at end of args
        args.insert(-1, "-L")
        args.insert(-1, f"{local_port}:{remote_host}:{remote_port}")

        self.log(f"LOCAL_FORWARD {local_port} -> {remote_host}:{remote_port} via {ssh_host}")
        if on_output:
            on_output(f"[SSH_TUNNEL] LOCAL_FORWARD 127.0.0.1:{local_port} -> {remote_host}:{remote_port} via {ssh_user}@{ssh_host}\n")
        return self._launch_tunnel("SSH_LOCAL_FWD", args, on_output)

    def remote_forward(
        self,
        remote_port: int,
        local_host: str,
        local_port: int,
        ssh_host: str,
        ssh_user: str,
        key_file: Optional[str] = None,
        on_output=None,
    ) -> Optional[str]:
        """
        Remote port forwarding: ssh -R remote_port:local_host:local_port ssh_user@ssh_host
        Exposes local_host:local_port on remote_port of the SSH server.
        """
        if not validate_port(remote_port) or not validate_port(local_port):
            if on_output:
                on_output("[SSH_TUNNEL] ERROR: invalid port(s)\n")
            return None
        if not validate_target(ssh_host):
            if on_output:
                on_output("[SSH_TUNNEL] ERROR: invalid ssh_host\n")
            return None

        args = self._build_base_args(ssh_host, ssh_user, key_file)
        args.insert(-1, "-R")
        args.insert(-1, f"{remote_port}:{local_host}:{local_port}")

        self.log(f"REMOTE_FORWARD {ssh_host}:{remote_port} -> {local_host}:{local_port}")
        if on_output:
            on_output(f"[SSH_TUNNEL] REMOTE_FORWARD {ssh_host}:{remote_port} -> {local_host}:{local_port}\n")
        return self._launch_tunnel("SSH_REMOTE_FWD", args, on_output)

    def dynamic_socks(
        self,
        local_port: int,
        ssh_host: str,
        ssh_user: str,
        key_file: Optional[str] = None,
        on_output=None,
    ) -> Optional[str]:
        """
        Dynamic SOCKS5 proxy: ssh -D local_port ssh_user@ssh_host
        Creates a SOCKS5 proxy on local_port for proxychains / browser routing.
        """
        if not validate_port(local_port):
            if on_output:
                on_output(f"[SSH_TUNNEL] ERROR: invalid local_port {local_port}\n")
            return None
        if not validate_target(ssh_host):
            if on_output:
                on_output("[SSH_TUNNEL] ERROR: invalid ssh_host\n")
            return None

        args = self._build_base_args(ssh_host, ssh_user, key_file)
        args.insert(-1, "-D")
        args.insert(-1, str(local_port))

        self.log(f"DYNAMIC_SOCKS SOCKS5://127.0.0.1:{local_port} via {ssh_host}")
        if on_output:
            on_output(f"[SSH_TUNNEL] DYNAMIC_SOCKS SOCKS5://127.0.0.1:{local_port} via {ssh_user}@{ssh_host}\n")
        return self._launch_tunnel("SSH_SOCKS", args, on_output)

    def reverse_tunnel(
        self,
        ssh_host: str,
        ssh_user: str,
        remote_port: int,
        local_port: int,
        key_file: Optional[str] = None,
        on_output=None,
    ) -> Optional[str]:
        """
        Persistent reverse SSH tunnel using autossh.
        autossh -M 0 -R remote_port:localhost:local_port ssh_user@ssh_host
        Falls back to plain ssh if autossh is not installed.
        Keeps the tunnel alive through disconnections.
        """
        if not validate_port(remote_port) or not validate_port(local_port):
            if on_output:
                on_output("[SSH_TUNNEL] ERROR: invalid port(s)\n")
            return None
        if not validate_target(ssh_host):
            if on_output:
                on_output("[SSH_TUNNEL] ERROR: invalid ssh_host\n")
            return None

        import shutil
        binary = "autossh" if shutil.which("autossh") else "ssh"

        base_ssh_args = [
            "-o", "StrictHostKeyChecking=no",
            "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=3",
            "-o", "ExitOnForwardFailure=yes",
            "-N",
            "-R", f"{remote_port}:localhost:{local_port}",
        ]
        if key_file:
            base_ssh_args += ["-i", key_file]
        base_ssh_args.append(f"{ssh_user}@{ssh_host}")

        if binary == "autossh":
            args = ["autossh", "-M", "0"] + base_ssh_args
        else:
            args = ["ssh"] + base_ssh_args

        self.log(f"REVERSE_TUNNEL {ssh_host}:{remote_port} -> localhost:{local_port} (via {binary})")
        if on_output:
            on_output(f"[SSH_TUNNEL] REVERSE_TUNNEL {ssh_host}:{remote_port} <- localhost:{local_port} [{binary}]\n")
        return self._launch_tunnel("SSH_REVERSE", args, on_output)

    def proxy_chain(
        self,
        targets: List[dict],
        on_output=None,
    ) -> Optional[str]:
        """
        Multi-hop SSH pivoting: builds a ProxyJump chain.
        Each entry in targets: {"host": str, "user": str, "port": int, "key": str (optional)}
        The last entry is the final destination; all prior entries are jump hosts.

        Builds:  ssh -J user1@hop1,user2@hop2 userN@final
        """
        if not targets or len(targets) < 2:
            if on_output:
                on_output("[SSH_TUNNEL] ERROR: proxy_chain requires at least 2 targets (hops + destination)\n")
            return None

        for t in targets:
            if not validate_target(t.get("host", "")):
                if on_output:
                    on_output(f"[SSH_TUNNEL] ERROR: invalid host in chain: {t.get('host')}\n")
                return None

        jump_hosts = targets[:-1]
        destination = targets[-1]

        jump_str = ",".join(
            f"{t['user']}@{t['host']}" + (f":{t['port']}" if t.get("port") else "")
            for t in jump_hosts
        )

        args = [
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "ServerAliveInterval=30",
            "-N",
            "-J", jump_str,
        ]

        if destination.get("key"):
            args += ["-i", destination["key"]]

        args.append(f"{destination['user']}@{destination['host']}")

        chain_repr = " -> ".join(f"{t['user']}@{t['host']}" for t in targets)
        self.log(f"PROXY_CHAIN: {chain_repr}")
        if on_output:
            on_output(f"[SSH_TUNNEL] PROXY_CHAIN: {chain_repr}\n")
        return self._launch_tunnel("SSH_CHAIN", args, on_output)

    def kill_tunnels(self, on_output=None) -> None:
        """
        Terminate all active SSH tunnel processes launched by this instance.
        Uses runner.stop_task() for graceful SIGTERM -> SIGKILL.
        """
        with self._lock:
            ids = list(self._tunnel_pids)

        if not ids:
            if on_output:
                on_output("[SSH_TUNNEL] No active tunnels to kill.\n")
            return

        for task_id in ids:
            runner.stop_task(task_id)
            if on_output:
                on_output(f"[SSH_TUNNEL] KILLED task {task_id}\n")

        with self._lock:
            self._tunnel_pids.clear()

        # Also pkill any orphaned ssh -N processes for safety
        try:
            subprocess.run(
                ["pkill", "-f", "ssh -N"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except FileNotFoundError:
            pass

        self.log("KILL_TUNNELS: all tunnels terminated")
        if on_output:
            on_output("[SSH_TUNNEL] All tunnels terminated.\n")
