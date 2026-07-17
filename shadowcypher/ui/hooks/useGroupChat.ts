import { useState, useCallback } from 'react';

const API_BASE = 'https://api.shadowcypher.site';

// Groups map to Worker teams + team rooms (room_type: "team", name: "team-{id}")
export interface Group {
    id: string;
    name: string;
    role: 'owner' | 'member';
    is_owner: boolean;
    created_at: string;
}

export interface GroupMessage {
    id: string;
    user_id: string;
    nick: string;
    content: string;
    created_at: string;
}

// Worker has no team-members listing endpoint; this is a stub shape
export interface GroupMember {
    id: string;
    user_id: string;
    joined_at: string;
}

export function useGroupChat(apiKey: string | null) {
    const [groups, setGroups] = useState<Group[]>([]);
    const [currentGroupMessages, setCurrentGroupMessages] = useState<GroupMessage[]>([]);
    const [currentGroupMembers, setCurrentGroupMembers] = useState<GroupMember[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    function authHeader() {
        return apiKey ? { Authorization: `Bearer ${apiKey}` } : {} as Record<string, string>;
    }

    const fetchGroups = useCallback(async () => {
        if (!apiKey) return;
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${API_BASE}/v1/teams`, { headers: authHeader() });
            if (!res.ok) throw new Error(`${res.status}`);
            const data = await res.json() as { teams: Group[] };
            setGroups(data.teams ?? []);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch groups');
        } finally {
            setLoading(false);
        }
    }, [apiKey]);

    const createGroup = useCallback(async (name: string): Promise<Group | null> => {
        if (!apiKey) return null;
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${API_BASE}/v1/teams`, {
                method: 'POST',
                headers: { ...authHeader(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ name }),
            });
            if (!res.ok) {
                const body = await res.json().catch(() => ({})) as { error?: string };
                if (res.status === 403) throw new Error('Groups require the Operator plan. Upgrade at shadowcypher.site/billing');
                throw new Error(body.error ?? `${res.status}`);
            }
            const data = await res.json() as { team_id: string; name: string; created_at: string };
            const group: Group = { id: data.team_id, name: data.name, role: 'owner', is_owner: true, created_at: data.created_at };
            setGroups(prev => [group, ...prev]);
            return group;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to create group');
            return null;
        } finally {
            setLoading(false);
        }
    }, [apiKey]);

    const fetchGroupMessages = useCallback(async (teamId: string) => {
        if (!apiKey) return;
        setLoading(true);
        setError(null);
        try {
            const room = `team-${teamId}`;
            const res = await fetch(
                `${API_BASE}/v1/chat/messages?room=${encodeURIComponent(room)}&limit=50`,
                { headers: authHeader() }
            );
            if (!res.ok) throw new Error(`${res.status}`);
            const data = await res.json() as { messages: GroupMessage[] };
            setCurrentGroupMessages(data.messages ?? []);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch messages');
        } finally {
            setLoading(false);
        }
    }, [apiKey]);

    // Worker has no team-members listing endpoint — returns empty list
    const fetchGroupMembers = useCallback(async (_teamId: string) => {
        setCurrentGroupMembers([]);
    }, []);

    const sendMessage = useCallback(async (teamId: string, content: string): Promise<GroupMessage | null> => {
        if (!apiKey) return null;
        try {
            const res = await fetch(`${API_BASE}/v1/chat/send`, {
                method: 'POST',
                headers: { ...authHeader(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ room: `team-${teamId}`, content }),
            });
            if (!res.ok) throw new Error(`${res.status}`);
            const data = await res.json() as { message?: GroupMessage };
            return data.message ?? null;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to send message');
            return null;
        }
    }, [apiKey]);

    // Invite by email — Operator plan required on the team owner's side
    const addMember = useCallback(async (teamId: string, email: string): Promise<boolean> => {
        if (!apiKey) return false;
        try {
            const res = await fetch(`${API_BASE}/v1/teams/invite`, {
                method: 'POST',
                headers: { ...authHeader(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ team_id: teamId, email }),
            });
            if (!res.ok) {
                const body = await res.json().catch(() => ({})) as { error?: string };
                throw new Error(body.error ?? `${res.status}`);
            }
            return true;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to invite member');
            return false;
        }
    }, [apiKey]);

    // Worker only supports leaving — can't kick other members
    const removeMember = useCallback(async (teamId: string, _memberId: string): Promise<boolean> => {
        if (!apiKey) return false;
        try {
            const res = await fetch(`${API_BASE}/v1/teams/leave`, {
                method: 'DELETE',
                headers: { ...authHeader(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ team_id: teamId }),
            });
            return res.ok;
        } catch {
            return false;
        }
    }, [apiKey]);

    return {
        groups, currentGroupMessages, currentGroupMembers, loading, error,
        fetchGroups, createGroup, fetchGroupMessages, fetchGroupMembers,
        sendMessage, addMember, removeMember,
    };
}
