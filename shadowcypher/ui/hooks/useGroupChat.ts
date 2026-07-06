import { useState, useCallback } from 'react';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface Group {
    id: string;
    name: string;
    creator_id: string;
    created_at: string;
}

export interface GroupMessage {
    id: string;
    group_id: string;
    sender_id: string;
    encrypted_message: string;
    nonce: string;
    created_at: string;
}

export interface GroupMember {
    id: string;
    group_id: string;
    user_id: string;
    joined_at: string;
}

export function useGroupChat(token: string | null) {
    const [groups, setGroups] = useState<Group[]>([]);
    const [currentGroupMessages, setCurrentGroupMessages] = useState<GroupMessage[]>([]);
    const [currentGroupMembers, setCurrentGroupMembers] = useState<GroupMember[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const fetchGroups = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${API_BASE}/chat/groups`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (!res.ok) throw new Error('Failed to fetch groups');
            const data = await res.json();
            setGroups(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setLoading(false);
        }
    }, [token]);

    const createGroup = useCallback(async (name: string) => {
        if (!token) return null;
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${API_BASE}/chat/groups`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({ name })
            });
            if (!res.ok) throw new Error('Failed to create group');
            const group = await res.json();
            setGroups(prev => [...prev, group]);
            return group;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
            return null;
        } finally {
            setLoading(false);
        }
    }, [token]);

    const fetchGroupMessages = useCallback(async (groupId: string) => {
        if (!token) return;
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${API_BASE}/chat/groups/${groupId}/messages`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (!res.ok) throw new Error('Failed to fetch messages');
            const data = await res.json();
            setCurrentGroupMessages(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
        } finally {
            setLoading(false);
        }
    }, [token]);

    const fetchGroupMembers = useCallback(async (groupId: string) => {
        if (!token) return;
        try {
            const res = await fetch(`${API_BASE}/chat/groups/${groupId}/members`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (!res.ok) throw new Error('Failed to fetch members');
            const data = await res.json();
            setCurrentGroupMembers(data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
        }
    }, [token]);

    const sendMessage = useCallback(async (groupId: string, encryptedMessage: string, nonce: string) => {
        if (!token) return null;
        try {
            const res = await fetch(`${API_BASE}/chat/groups/${groupId}/messages`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({ encrypted_message: encryptedMessage, nonce })
            });
            if (!res.ok) throw new Error('Failed to send message');
            return await res.json();
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
            return null;
        }
    }, [token]);

    const addMember = useCallback(async (groupId: string, userId: string) => {
        if (!token) return false;
        try {
            const res = await fetch(`${API_BASE}/chat/groups/${groupId}/members`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify({ user_id: userId })
            });
            if (!res.ok) throw new Error('Failed to add member');
            const member = await res.json();
            setCurrentGroupMembers(prev => [...prev, member]);
            return true;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
            return false;
        }
    }, [token]);

    const removeMember = useCallback(async (groupId: string, userId: string) => {
        if (!token) return false;
        try {
            const res = await fetch(`${API_BASE}/chat/groups/${groupId}/members/${userId}`, {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${token}` }
            });
            if (!res.ok) throw new Error('Failed to remove member');
            setCurrentGroupMembers(prev => prev.filter(m => m.user_id !== userId));
            return true;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
            return false;
        }
    }, [token]);

    return {
        groups,
        currentGroupMessages,
        currentGroupMembers,
        loading,
        error,
        fetchGroups,
        createGroup,
        fetchGroupMessages,
        fetchGroupMembers,
        sendMessage,
        addMember,
        removeMember
    };
}
