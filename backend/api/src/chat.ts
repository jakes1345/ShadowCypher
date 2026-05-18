/**
 * Chat endpoints — global room + team rooms.
 *
 * GET  /v1/chat/rooms                    list rooms user has access to
 * GET  /v1/chat/messages?room=<name>&limit=50&before=<iso>  paginated history
 * POST /v1/chat/send   { room, content } send a message
 * POST /v1/chat/presence { room }        heartbeat — mark user online in room
 * GET  /v1/chat/online?room=<name>       users seen in last 90s
 */

import type { Env } from "./index";
import { dbSelect, dbInsert, dbUpsert } from "./supabase";

interface AuthedUser { id: string; email: string }

interface ChatRoom {
  id: string;
  name: string;
  display_name: string;
  room_type: string;
  team_id: string | null;
  created_at: string;
}

interface ChatMessage {
  id: string;
  room_id: string;
  user_id: string;
  nick: string;
  content: string;
  created_at: string;
}

interface Presence {
  user_id: string;
  room_id: string;
  nick: string;
  seen_at: string;
}

const json = (body: unknown, init: ResponseInit = {}, cors: HeadersInit = {}): Response =>
  new Response(JSON.stringify(body), {
    ...init,
    headers: { "Content-Type": "application/json", ...cors, ...(init.headers ?? {}) },
  });

function nickFromEmail(email: string): string {
  return email.split("@")[0].replace(/[^a-zA-Z0-9_-]/g, "").slice(0, 20) || "user";
}

async function resolveRoom(env: Env, roomName: string, userId: string): Promise<ChatRoom | null> {
  const rows = await dbSelect<ChatRoom>(env, "chat_rooms", {
    select: "id,name,display_name,room_type,team_id",
    filters: { name: `eq.${roomName}` },
    limit: 1,
  });
  const room = rows[0] ?? null;
  if (!room) return null;

  // Team rooms: verify membership
  if (room.room_type === "team" && room.team_id) {
    const members = await dbSelect(env, "team_members", {
      filters: { team_id: `eq.${room.team_id}`, user_id: `eq.${userId}` },
      limit: 1,
    });
    if (!members.length) return null;
  }
  return room;
}

// ── GET /v1/chat/rooms ────────────────────────────────────────────────────────

export async function listRooms(
  _req: Request, env: Env, user: AuthedUser, cors: HeadersInit
): Promise<Response> {
  // Always include global room
  const globalRoom = await dbSelect<ChatRoom>(env, "chat_rooms", {
    select: "id,name,display_name,room_type,team_id,created_at",
    filters: { room_type: "eq.global" },
  });

  // Include team rooms where user is a member
  const memberships = await dbSelect<{ team_id: string }>(env, "team_members", {
    select: "team_id",
    filters: { user_id: `eq.${user.id}` },
  });

  let teamRooms: ChatRoom[] = [];
  if (memberships.length) {
    const teamIds = memberships.map(m => m.team_id);
    // Fetch rooms for each team (simple approach)
    for (const tid of teamIds) {
      const rows = await dbSelect<ChatRoom>(env, "chat_rooms", {
        select: "id,name,display_name,room_type,team_id,created_at",
        filters: { team_id: `eq.${tid}` },
      });
      teamRooms = teamRooms.concat(rows);
    }
  }

  return json({ rooms: [...globalRoom, ...teamRooms] }, {}, cors);
}

// ── GET /v1/chat/messages ─────────────────────────────────────────────────────

export async function getMessages(
  req: Request, env: Env, user: AuthedUser, cors: HeadersInit
): Promise<Response> {
  const url = new URL(req.url);
  const roomName = (url.searchParams.get("room") ?? "global").slice(0, 64);
  const limit = Math.min(parseInt(url.searchParams.get("limit") ?? "50", 10), 100);
  const before = url.searchParams.get("before"); // ISO timestamp cursor

  const room = await resolveRoom(env, roomName, user.id);
  if (!room) return json({ error: "room_not_found" }, { status: 404 }, cors);

  const filters: Record<string, string> = { room_id: `eq.${room.id}` };
  if (before) filters.created_at = `lt.${before}`;

  const messages = await dbSelect<ChatMessage>(env, "chat_messages", {
    select: "id,user_id,nick,content,created_at",
    filters,
    order: "created_at.desc",
    limit,
  });

  return json({ room: room.name, messages: messages.reverse() }, {}, cors);
}

// ── POST /v1/chat/send ────────────────────────────────────────────────────────

export async function sendMessage(
  req: Request, env: Env, user: AuthedUser, cors: HeadersInit
): Promise<Response> {
  let body: { room?: string; content?: string };
  try { body = await req.json() as typeof body; }
  catch { return json({ error: "invalid_json" }, { status: 400 }, cors); }

  const roomName = (body.room ?? "global").slice(0, 64);
  const content = (body.content ?? "").trim().slice(0, 2000);

  if (!content) return json({ error: "content_required" }, { status: 400 }, cors);

  const room = await resolveRoom(env, roomName, user.id);
  if (!room) return json({ error: "room_not_found" }, { status: 404 }, cors);

  const nick = nickFromEmail(user.email);
  const msg = await dbInsert<ChatMessage>(env, "chat_messages", {
    room_id: room.id,
    user_id: user.id,
    nick,
    content,
  });

  // Update presence
  await dbUpsert(env, "chat_presence", {
    user_id: user.id,
    room_id: room.id,
    nick,
    seen_at: new Date().toISOString(),
  }, "user_id,room_id");

  return json({ ok: true, message: msg }, {}, cors);
}

// ── POST /v1/chat/presence ────────────────────────────────────────────────────

export async function updatePresence(
  req: Request, env: Env, user: AuthedUser, cors: HeadersInit
): Promise<Response> {
  let body: { room?: string };
  try { body = await req.json() as typeof body; }
  catch { return json({ error: "invalid_json" }, { status: 400 }, cors); }

  const roomName = (body.room ?? "global").slice(0, 64);
  const room = await resolveRoom(env, roomName, user.id);
  if (!room) return json({ error: "room_not_found" }, { status: 404 }, cors);

  await dbUpsert(env, "chat_presence", {
    user_id: user.id,
    room_id: room.id,
    nick: nickFromEmail(user.email),
    seen_at: new Date().toISOString(),
  }, "user_id,room_id");

  return json({ ok: true }, {}, cors);
}

// ── GET /v1/chat/online ───────────────────────────────────────────────────────

export async function getOnlineUsers(
  req: Request, env: Env, user: AuthedUser, cors: HeadersInit
): Promise<Response> {
  const url = new URL(req.url);
  const roomName = (url.searchParams.get("room") ?? "global").slice(0, 64);

  const room = await resolveRoom(env, roomName, user.id);
  if (!room) return json({ error: "room_not_found" }, { status: 404 }, cors);

  // Online = seen in last 90 seconds
  const cutoff = new Date(Date.now() - 90_000).toISOString();
  const present = await dbSelect<Presence>(env, "chat_presence", {
    select: "user_id,nick,seen_at",
    filters: { room_id: `eq.${room.id}`, seen_at: `gt.${cutoff}` },
    order: "seen_at.desc",
    limit: 100,
  });

  return json({ room: room.name, online: present }, {}, cors);
}

// ── Ensure team chat room exists (called on team creation) ────────────────────

export async function ensureTeamRoom(env: Env, teamId: string, teamName: string): Promise<void> {
  const name = `team-${teamId}`;
  const rows = await dbSelect(env, "chat_rooms", {
    filters: { name: `eq.${name}` },
    limit: 1,
  });
  if (!rows.length) {
    await dbInsert(env, "chat_rooms", {
      name,
      display_name: `#${teamName.toLowerCase().replace(/[^a-z0-9]/g, "-").slice(0, 30)}`,
      room_type: "team",
      team_id: teamId,
    });
  }
}
