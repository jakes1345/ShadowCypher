/**
 * ChatRoom Durable Object — one instance per room, holds all WebSocket connections.
 *
 * Protocol (client → server):
 *   { type: "message", content: "..." }
 *   { type: "ping" }
 *
 * Protocol (server → client):
 *   { type: "message", id, user_id, nick, content, created_at }
 *   { type: "presence", user_id, nick, online: true|false }
 *   { type: "history", messages: [...] }   — sent on connect
 *   { type: "pong" }
 *   { type: "error", message: "..." }
 */

import type { Env } from "./index";
import { dbInsert, dbSelect } from "./supabase";

interface SessionMeta {
  userId: string;
  nick: string;
  roomId: string;
  roomName: string;
}

interface ChatMessage {
  id: string;
  user_id: string;
  nick: string;
  content: string;
  created_at: string;
}

export class ChatRoom implements DurableObject {
  private state: DurableObjectState;
  private env: Env;

  constructor(state: DurableObjectState, env: Env) {
    this.state = state;
    this.env = env;
  }

  async fetch(request: Request): Promise<Response> {
    if (request.headers.get("Upgrade") !== "websocket") {
      return new Response("Expected WebSocket", { status: 426 });
    }

    const url = new URL(request.url);
    const userId = url.searchParams.get("user_id") ?? "";
    const nick = url.searchParams.get("nick") ?? "user";
    const roomId = url.searchParams.get("room_id") ?? "";
    const roomName = url.searchParams.get("room") ?? "global";

    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);

    const meta: SessionMeta = { userId, nick, roomId, roomName };
    this.state.acceptWebSocket(server, ["chat"]);
    server.serializeAttachment(meta);

    // Send recent history on connect
    try {
      const history = await dbSelect<ChatMessage>(this.env, "chat_messages", {
        select: "id,user_id,nick,content,created_at",
        filters: { room_id: `eq.${roomId}` },
        order: "created_at.desc",
        limit: 50,
      });
      server.send(JSON.stringify({ type: "history", messages: history.reverse() }));
    } catch {
      // Non-fatal — client will load history via REST fallback
    }

    // Notify room that user joined
    this.broadcast({ type: "presence", user_id: userId, nick, online: true }, server);

    return new Response(null, { status: 101, webSocket: client });
  }

  async webSocketMessage(ws: WebSocket, raw: string | ArrayBuffer): Promise<void> {
    if (typeof raw !== "string") return;
    const meta = ws.deserializeAttachment() as SessionMeta | null;
    if (!meta) return;

    let data: { type?: string; content?: string };
    try { data = JSON.parse(raw); }
    catch { ws.send(JSON.stringify({ type: "error", message: "invalid_json" })); return; }

    if (data.type === "ping") {
      ws.send(JSON.stringify({ type: "pong" }));
      return;
    }

    if (data.type === "message") {
      const content = (data.content ?? "").trim().slice(0, 2000);
      if (!content) return;

      let msg: ChatMessage;
      try {
        msg = await dbInsert<ChatMessage>(this.env, "chat_messages", {
          room_id: meta.roomId,
          user_id: meta.userId,
          nick: meta.nick,
          content,
        });
      } catch {
        ws.send(JSON.stringify({ type: "error", message: "send_failed" }));
        return;
      }

      this.broadcast({ type: "message", ...msg }, null);
    }
  }

  async webSocketClose(ws: WebSocket): Promise<void> {
    const meta = ws.deserializeAttachment() as SessionMeta | null;
    if (meta) {
      this.broadcast({ type: "presence", user_id: meta.userId, nick: meta.nick, online: false }, null);
    }
  }

  async webSocketError(ws: WebSocket): Promise<void> {
    const meta = ws.deserializeAttachment() as SessionMeta | null;
    if (meta) {
      this.broadcast({ type: "presence", user_id: meta.userId, nick: meta.nick, online: false }, null);
    }
  }

  private broadcast(data: unknown, exclude: WebSocket | null): void {
    const msg = JSON.stringify(data);
    for (const ws of this.state.getWebSockets("chat")) {
      if (ws === exclude) continue;
      try { ws.send(msg); } catch { /* stale socket */ }
    }
  }
}
