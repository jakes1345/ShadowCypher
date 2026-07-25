/**
 * VideoRoom Durable Object — one instance per call room, relays WebRTC signaling.
 *
 * Uses Cloudflare WebSocket Hibernation API so the DO stays alive across messages
 * without holding a persistent connection cost.
 *
 * Protocol (client → server):
 *   { type: "offer",  to: peerId, sdp: string }
 *   { type: "answer", to: peerId, sdp: string }
 *   { type: "ice",    to: peerId, candidate: RTCIceCandidateInit }
 *   { type: "ping" }
 *
 * Protocol (server → client):
 *   { type: "joined",      peerId, peers: { id, name }[] }  — on connect
 *   { type: "peer_joined", peerId, name }                   — broadcast
 *   { type: "peer_left",   peerId }                         — broadcast
 *   { type: "offer",  from: peerId, sdp }                   — relayed
 *   { type: "answer", from: peerId, sdp }                   — relayed
 *   { type: "ice",    from: peerId, candidate }             — relayed
 *   { type: "pong" }
 *   { type: "error", message }
 */

import type { Env } from "./index";

const MAX_PEERS = 6;
const ROOM_TAG  = "video";

interface PeerMeta {
  peerId: string;
  name: string;
}

export class VideoRoom implements DurableObject {
  private state: DurableObjectState;

  constructor(state: DurableObjectState, _env: Env) {
    this.state = state;
  }

  async fetch(request: Request): Promise<Response> {
    if (request.headers.get("Upgrade") !== "websocket") {
      return new Response("Expected WebSocket", { status: 426 });
    }

    const existing = this.state.getWebSockets(ROOM_TAG);
    if (existing.length >= MAX_PEERS) {
      return new Response("room_full", { status: 429 });
    }

    const url  = new URL(request.url);
    const name = (url.searchParams.get("name") ?? "Anonymous").slice(0, 32);
    const peerId = crypto.randomUUID();

    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);

    this.state.acceptWebSocket(server, [ROOM_TAG, peerId]);
    server.serializeAttachment({ peerId, name } satisfies PeerMeta);

    // Tell the new peer who's already here
    const peers = existing.map((ws) => {
      const m = ws.deserializeAttachment() as PeerMeta | null;
      return m ? { id: m.peerId, name: m.name } : null;
    }).filter(Boolean);

    server.send(JSON.stringify({ type: "joined", peerId, peers }));

    // Tell everyone else a new peer has arrived
    this.broadcast(peerId, { type: "peer_joined", peerId, name });

    return new Response(null, { status: 101, webSocket: client });
  }

  async webSocketMessage(ws: WebSocket, raw: string | ArrayBuffer): Promise<void> {
    if (typeof raw !== "string") return;

    const meta = ws.deserializeAttachment() as PeerMeta | null;
    if (!meta) return;

    let msg: Record<string, unknown>;
    try { msg = JSON.parse(raw); }
    catch { ws.send(JSON.stringify({ type: "error", message: "invalid_json" })); return; }

    if (msg.type === "ping") {
      ws.send(JSON.stringify({ type: "pong" }));
      return;
    }

    const allowed = new Set(["offer", "answer", "ice"]);
    if (!allowed.has(msg.type as string)) return;

    const targetId = msg.to as string | undefined;
    if (!targetId) return;

    const targets = this.state.getWebSockets(targetId);
    const payload = JSON.stringify({ ...msg, from: meta.peerId });
    for (const t of targets) {
      try { t.send(payload); } catch { /* stale */ }
    }
  }

  async webSocketClose(ws: WebSocket): Promise<void> {
    const meta = ws.deserializeAttachment() as PeerMeta | null;
    if (meta) this.broadcast(meta.peerId, { type: "peer_left", peerId: meta.peerId });
  }

  async webSocketError(ws: WebSocket): Promise<void> {
    const meta = ws.deserializeAttachment() as PeerMeta | null;
    if (meta) this.broadcast(meta.peerId, { type: "peer_left", peerId: meta.peerId });
  }

  private broadcast(excludeId: string, data: unknown): void {
    const msg = JSON.stringify(data);
    for (const ws of this.state.getWebSockets(ROOM_TAG)) {
      const m = ws.deserializeAttachment() as PeerMeta | null;
      if (m?.peerId === excludeId) continue;
      try { ws.send(msg); } catch { /* stale */ }
    }
  }
}
