"""
Shadow Daemon — JSON-RPC 2.0 IPC server stub
Cross-platform: Unix socket (Linux/macOS) or TCP loopback (Windows).

Usage: python daemon_ipc_stub.py
"""
import asyncio
import json
import os
import random
import sys

# IPC transport — must match IpcClient.cpp
if sys.platform == "win32":
    _TRANSPORT = "tcp"
    _TCP_HOST  = "127.0.0.1"
    _TCP_PORT  = 54321
else:
    _TRANSPORT   = "unix"
    _SOCKET_PATH = "/tmp/shadowcypher-daemon.sock"


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
    if method == "get_ai_model":
        return {"model": "shadowai-stub"}
    if method == "ai_chat":
        msg = params.get("message", "")
        return {"response": f"[STUB] Echo: {msg}"}
    if method == "cve_feed_recent":
        return {"cves": [], "count": 0}
    if method == "cve_feed_scan":
        return {"cves": [], "target": params.get("target", "")}
    if method == "cve_feed_search":
        return {"cves": [], "keyword": params.get("keyword", "")}
    return {"error": "method_not_found"}


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info("peername") or "unix"
    print(f"[daemon] client connected: {addr}")
    try:
        while True:
            line = await reader.readline()
            if not line:
                break
            try:
                req    = json.loads(line)
                result = handle_request(req.get("method", ""), req.get("params") or {})
                resp   = {"jsonrpc": "2.0", "result": result, "id": req.get("id")}
            except Exception as e:
                resp = {"jsonrpc": "2.0", "error": {"message": str(e)}, "id": None}
            writer.write(json.dumps(resp).encode() + b"\n")
            await writer.drain()
    except (asyncio.CancelledError, ConnectionResetError):
        pass
    finally:
        writer.close()
        print("[daemon] client disconnected")


async def main():
    if _TRANSPORT == "tcp":
        server = await asyncio.start_server(handle_client, _TCP_HOST, _TCP_PORT)
        print(f"[daemon] listening on {_TCP_HOST}:{_TCP_PORT}")
    else:
        if os.path.exists(_SOCKET_PATH):
            os.unlink(_SOCKET_PATH)
        server = await asyncio.start_unix_server(handle_client, _SOCKET_PATH)
        print(f"[daemon] listening on {_SOCKET_PATH}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
