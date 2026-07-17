import { useState, useCallback } from 'react';

const API_BASE = 'https://api.shadowcypher.site';

export interface ChatRoom {
    id: string;
    name: string;
    display_name: string;
    room_type: 'global' | 'public' | 'team' | 'dm';
    team_id: string | null;
    created_by: string | null;
    topic: string | null;
    created_at: string;
    other_nick?: string;
}

export interface ChatMessage {
    id: string;
    user_id: string;
    nick: string;
    content: string;
    created_at: string;
    reactions?: Record<string, number>;
}

export function useChat(apiKey: string | null) {
    const [rooms, setRooms] = useState<ChatRoom[]>([]);
    const [dms, setDms] = useState<ChatRoom[]>([]);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    function authHeader() {
        return apiKey ? { Authorization: `Bearer ${apiKey}` } : {} as Record<string, string>;
    }

    const fetchRooms = useCallback(async () => {
        if (!apiKey) return;
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${API_BASE}/v1/chat/rooms`, { headers: authHeader() });
            if (!res.ok) throw new Error(`${res.status}`);
            const data = await res.json() as { rooms: ChatRoom[] };
            setRooms((data.rooms ?? []).filter(r => r.room_type !== 'dm'));
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch rooms');
        } finally {
            setLoading(false);
        }
    }, [apiKey]);

    const fetchDms = useCallback(async () => {
        if (!apiKey) return;
        try {
            const res = await fetch(`${API_BASE}/v1/chat/dm`, { headers: authHeader() });
            if (!res.ok) return;
            const data = await res.json() as { dms: ChatRoom[] };
            setDms(data.dms ?? []);
        } catch { /* silent */ }
    }, [apiKey]);

    const fetchMessages = useCallback(async (roomName: string) => {
        if (!apiKey) return;
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(
                `${API_BASE}/v1/chat/messages?room=${encodeURIComponent(roomName)}&limit=50`,
                { headers: authHeader() }
            );
            if (!res.ok) throw new Error(`${res.status}`);
            const data = await res.json() as { messages: ChatMessage[] };
            setMessages(data.messages ?? []);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch messages');
        } finally {
            setLoading(false);
        }
    }, [apiKey]);

    const sendMessage = useCallback(async (roomName: string, content: string) => {
        if (!apiKey || !content.trim()) return;
        const res = await fetch(`${API_BASE}/v1/chat/send`, {
            method: 'POST',
            headers: { ...authHeader(), 'Content-Type': 'application/json' },
            body: JSON.stringify({ room: roomName, content }),
        });
        if (!res.ok) throw new Error(`send failed: ${res.status}`);
    }, [apiKey]);

    const openDm = useCallback(async (handle: string): Promise<string | null> => {
        if (!apiKey) return null;
        const res = await fetch(`${API_BASE}/v1/chat/dm/open`, {
            method: 'POST',
            headers: { ...authHeader(), 'Content-Type': 'application/json' },
            body: JSON.stringify({ handle }),
        });
        if (!res.ok) return null;
        const data = await res.json() as { room?: string };
        return data.room ?? null;
    }, [apiKey]);

    const createRoom = useCallback(async (name: string, displayName?: string, topic?: string): Promise<ChatRoom | null> => {
        if (!apiKey) return null;
        const res = await fetch(`${API_BASE}/v1/chat/rooms`, {
            method: 'POST',
            headers: { ...authHeader(), 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, display_name: displayName ?? `#${name}`, topic }),
        });
        if (!res.ok) return null;
        const data = await res.json() as { room?: ChatRoom };
        return data.room ?? null;
    }, [apiKey]);

    return {
        rooms, dms, messages, loading, error,
        fetchRooms, fetchDms, fetchMessages, sendMessage, openDm, createRoom,
    };
}
