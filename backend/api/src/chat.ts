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
    // Single IN query — avoids N+1 (one query per team)
    teamRooms = await dbSelect<ChatRoom>(env, "chat_rooms", {
      select: "id,name,display_name,room_type,team_id,created_at",
      filters: { team_id: `in.(${teamIds.join(",")})` },
    });
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

// ── POST /v1/chat/dm/open ─────────────────────────────────────────────────────

export async function openDm(
  req: Request, env: Env, user: AuthedUser, cors: HeadersInit
): Promise<Response> {
  const body = (await req.json().catch(() => null)) as { handle?: string } | null;
  const handle = body?.handle?.trim().toLowerCase().replace(/[^a-z0-9_-]/g, "");
  if (!handle) return json({ error: "handle_required" }, { status: 400 }, cors);

  const myNick = nickFromEmail(user.email);
  if (handle === myNick) return json({ error: "cannot_dm_self" }, { status: 400 }, cors);

  // Verify target user exists
  const targetEmail = `${handle}@shadowcypher.site`;
  const usersResp = await fetch(
    `${env.SUPABASE_URL}/auth/v1/admin/users?email=${encodeURIComponent(targetEmail)}`,
    { headers: { apikey: env.SUPABASE_SERVICE_ROLE_KEY, Authorization: `Bearer ${env.SUPABASE_SERVICE_ROLE_KEY}` } }
  );
  if (!usersResp.ok) return json({ error: "user_lookup_failed" }, { status: 500 }, cors);
  const usersBody = (await usersResp.json()) as { users?: { id: string }[] };
  const targetUser = usersBody.users?.[0];
  if (!targetUser) return json({ error: "user_not_found" }, { status: 404 }, cors);

  // Sort by user ID for a consistent room identity regardless of who initiates
  const [first, second] = [
    { id: user.id, nick: myNick },
    { id: targetUser.id, nick: handle },
  ].sort((a, b) => a.id < b.id ? -1 : 1);

  // Short stable room name (first 12 hex chars of each UUID, no separator ambiguity)
  const h1 = first.id.replace(/-/g, "").slice(0, 12);
  const h2 = second.id.replace(/-/g, "").slice(0, 12);
  const roomName = `dm${h1}${h2}`;

  // display_name encodes both nicks and UIDs for access-check + display: nick1:nick2:uid1:uid2
  const displayName = `${first.nick}:${second.nick}:${first.id}:${second.id}`;

  const existing = await dbSelect<ChatRoom>(env, "chat_rooms", {
    filters: { name: `eq.${roomName}` }, limit: 1,
  });

  if (!existing.length) {
    await dbInsert(env, "chat_rooms", {
      name: roomName,
      display_name: displayName,
      room_type: "dm",
      team_id: null,
    });
  }

  return json({ ok: true, room: roomName, display: `@${handle}` }, {}, cors);
}

// ── GET /v1/chat/dm ───────────────────────────────────────────────────────────

export async function listDms(
  _req: Request, env: Env, user: AuthedUser, cors: HeadersInit
): Promise<Response> {
  // Find rooms where user.id appears in display_name (format: nick1:nick2:uid1:uid2)
  const rooms = await dbSelect<ChatRoom>(env, "chat_rooms", {
    select: "id,name,display_name,room_type,created_at",
    filters: {
      room_type: "eq.dm",
      display_name: `ilike.%${user.id}%`,
    },
    order: "created_at.desc",
    limit: 50,
  });

  const dms = rooms.map(r => {
    const parts = r.display_name.split(":");
    // parts: [nick1, nick2, uid1, uid2]  (uid may contain hyphens — split gives more parts)
    // Since UIDs look like "abc-def-ghi", splitting "n1:n2:uid1:uid2" by ":" yields [n1, n2, uidPart1, uidPart2, ...]
    // Reassemble: nicks are first two parts, UIDs are the remaining joined back with ":"
    const nick1 = parts[0];
    const nick2 = parts[1];
    // uid1 and uid2 are the 3rd and 4th original fields, but UUIDs don't have ":" so parts[2] = uid1, parts[3] = uid2
    const uid1 = parts[2];
    const otherNick = uid1 === user.id ? nick2 : nick1;
    return { ...r, display_name: `@${otherNick}`, other_nick: otherNick };
  });

  return json({ dms }, {}, cors);
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
