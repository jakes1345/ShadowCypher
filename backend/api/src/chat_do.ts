/**
 * ChatRoom Durable Object — one instance per room, holds all WebSocket connections.
 *
 * Protocol (client → server):
 *   { type: "message", content: "..." }
 *   { type: "ping" }
 *   { type: "react", message_id: "...", emoji: "..." }
 *   { type: "read" }   — DM rooms only: mark messages as read
 *
 * Protocol (server → client):
 *   { type: "message", id, user_id, nick, content, created_at }
 *   { type: "presence", user_id, nick, online: true|false }
 *   { type: "history", messages: [...] }   — sent on connect
 *   { type: "read_receipts", receipts: [{user_id, nick, last_read_at}] }  — DM connect
 *   { type: "read_receipt", user_id, nick, last_read_at }                 — DM live update
 *   { type: "reactions", message_id, reactions: {emoji: count} }
 *   { type: "pong" }
 *   { type: "error", message: "..." }
 */

import type { Env } from "./index";
import { dbInsert, dbSelect, dbUpsert } from "./supabase";
import { dispatchMentionPushNotification } from "./notifications";

interface SessionMeta {
  userId: string;
  nick: string;
  roomId: string;
  roomName: string;
  roomType: string;
}

interface ChatMessage {
  id: string;
  user_id: string;
  nick: string;
  content: string;
  created_at: string;
  reactions?: Record<string, number>;
}

interface ChatReaction {
  message_id: string;
  user_id: string;
  emoji: string;
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
    const roomType = url.searchParams.get("room_type") ?? "public";

    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);

    const meta: SessionMeta = { userId, nick, roomId, roomName, roomType };
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
      history.reverse();

      // Attach reactions to history messages
      if (history.length > 0) {
        const ids = history.map((m) => m.id);
        const reactionRows = await dbSelect<ChatReaction>(this.env, "chat_reactions", {
          select: "message_id,emoji",
          filters: { message_id: `in.(${ids.join(",")})` },
        }).catch(() => [] as ChatReaction[]);

        const byMsg: Record<string, Record<string, number>> = {};
        for (const r of reactionRows) {
          if (!byMsg[r.message_id]) byMsg[r.message_id] = {};
          byMsg[r.message_id][r.emoji] = (byMsg[r.message_id][r.emoji] ?? 0) + 1;
        }
        for (const m of history) {
          if (byMsg[m.id]) m.reactions = byMsg[m.id];
        }
      }

      server.send(JSON.stringify({ type: "history", messages: history }));

      // For DM rooms: upsert this user's read receipt and send all receipts to client
      if (roomType === "dm" && userId) {
        await this.upsertReadReceipt(roomName, userId, nick);
        const receipts = await dbSelect<{ user_id: string; nick: string; last_read_at: string }>(
          this.env, "dm_read_receipts", {
            select: "user_id,nick,last_read_at",
            filters: { room_id: `eq.${roomName}` },
          }
        ).catch(() => []);
        server.send(JSON.stringify({ type: "read_receipts", receipts }));
      }
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

    let data: { type?: string; content?: string; message_id?: string; emoji?: string };
    try { data = JSON.parse(raw); }
    catch { ws.send(JSON.stringify({ type: "error", message: "invalid_json" })); return; }

    if (data.type === "ping") {
      ws.send(JSON.stringify({ type: "pong" }));
      return;
    }

    if (data.type === "read") {
      if (meta.roomType === "dm" && meta.userId) {
        await this.upsertReadReceipt(meta.roomName, meta.userId, meta.nick);
      }
      return;
    }

    if (data.type === "react") {
      const messageId = (data.message_id ?? "").trim();
      const emoji = (data.emoji ?? "").trim().slice(0, 8);
      if (!messageId || !emoji) return;

      // Check existing reaction
      const existing = await dbSelect<ChatReaction>(this.env, "chat_reactions", {
        filters: {
          message_id: `eq.${messageId}`,
          user_id: `eq.${meta.userId}`,
          emoji: `eq.${emoji}`,
        },
        limit: 1,
      }).catch(() => [] as ChatReaction[]);

      if (existing.length > 0) {
        // Toggle off
        const url = `${this.env.SUPABASE_URL}/rest/v1/chat_reactions?message_id=eq.${messageId}&user_id=eq.${meta.userId}&emoji=eq.${encodeURIComponent(emoji)}`;
        await fetch(url, {
          method: "DELETE",
          headers: {
            apikey: this.env.SUPABASE_SERVICE_ROLE_KEY,
            Authorization: `Bearer ${this.env.SUPABASE_SERVICE_ROLE_KEY}`,
          },
        }).catch(() => null);
      } else {
        // Toggle on
        await dbInsert<ChatReaction>(this.env, "chat_reactions", {
          message_id: messageId,
          user_id: meta.userId,
          emoji,
        }).catch(() => null);
      }

      // Aggregate and broadcast updated counts
      const allReactions = await dbSelect<ChatReaction>(this.env, "chat_reactions", {
        select: "emoji",
        filters: { message_id: `eq.${messageId}` },
      }).catch(() => [] as ChatReaction[]);

      const counts: Record<string, number> = {};
      for (const r of allReactions) {
        counts[r.emoji] = (counts[r.emoji] ?? 0) + 1;
      }
      this.broadcast({ type: "reactions", message_id: messageId, reactions: counts }, null);
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

      // @mention push notifications — fire-and-forget
      const mentioned = [...new Set((content.match(/\B@([a-zA-Z0-9_-]{1,32})\b/g) ?? [])
        .map((m) => m.slice(1).toLowerCase())
        .filter((nick) => nick !== meta.nick.toLowerCase())
      )];
      for (const nick of mentioned) {
        this.sendMentionPush(nick, meta.nick, content, meta.roomName).catch(() => null);
      }
    }
  }

  private async sendMentionPush(
    mentionedNick: string,
    senderNick: string,
    content: string,
    roomName: string
  ): Promise<void> {
    const targetEmail = `${mentionedNick}@shadowcypher.site`;
    const resp = await fetch(
      `${this.env.SUPABASE_URL}/auth/v1/admin/users?email=${encodeURIComponent(targetEmail)}`,
      {
        headers: {
          apikey: this.env.SUPABASE_SERVICE_ROLE_KEY,
          Authorization: `Bearer ${this.env.SUPABASE_SERVICE_ROLE_KEY}`,
        },
      }
    );
    if (!resp.ok) return;
    const body = (await resp.json()) as { users?: { id: string }[] };
    const userId = body.users?.[0]?.id;
    if (!userId) return;
    await dispatchMentionPushNotification(this.env, userId, {
      senderNick,
      preview: content,
      roomName,
    });
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

  private async upsertReadReceipt(roomName: string, userId: string, nick: string): Promise<void> {
    const last_read_at = new Date().toISOString();
    await dbUpsert(this.env, "dm_read_receipts", { room_id: roomName, user_id: userId, nick, last_read_at }, "room_id,user_id").catch(() => null);
    this.broadcast({ type: "read_receipt", user_id: userId, nick, last_read_at }, null);
  }

  private broadcast(data: unknown, exclude: WebSocket | null): void {
    const msg = JSON.stringify(data);
    for (const ws of this.state.getWebSockets("chat")) {
      if (ws === exclude) continue;
      try { ws.send(msg); } catch { /* stale socket */ }
    }
  }
}
