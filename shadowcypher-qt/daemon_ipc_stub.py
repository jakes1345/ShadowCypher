"""
Shadow Daemon — JSON-RPC 2.0 IPC server stub
Listens on /tmp/shadowcypher-daemon.sock for Qt6 app connections.

The real daemon will live in shadowcypher/core/daemon.py.
This stub lets you test the Qt6 UI without the full Python stack.

Usage: python daemon_ipc_stub.py
"""
import asyncio
import json
import os
import random

SOCKET_PATH = "/tmp/shadowcypher-daemon.sock"


def handle_request(method: str, params: dict) -> dict:
    if method == "get_tactical_summary":
        return {
            "active_missions": random.randint(0, 3),
            "uptime": "0:42:17",
            "threat_hits": random.randint(0, 5),
            "integrity": True,
            "stealth_active": random.choice([True, False]),
            "relay_connected": False,
        }
    if method == "get_counter_intel_status":
        return {"running": False, "last_scan": None, "findings": []}
    return {"error": "method_not_found"}


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    print("[daemon] client connected")
    try:
        while True:
            line = await reader.readline()
            if not line:
                break
            try:
                req = json.loads(line)
                result = handle_request(req.get("method", ""), req.get("params", {}))
                resp = {"jsonrpc": "2.0", "result": result, "id": req.get("id")}
            except Exception as e:
                resp = {"jsonrpc": "2.0", "error": {"message": str(e)}, "id": None}
            writer.write(json.dumps(resp).encode() + b"\n")
            await writer.drain()
    except asyncio.CancelledError:
        pass
    finally:
        writer.close()
        print("[daemon] client disconnected")


async def main():
    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)
    server = await asyncio.start_unix_server(handle_client, SOCKET_PATH)
    print(f"[daemon] listening on {SOCKET_PATH}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
