import { useState, useCallback } from 'react';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

/**
 * Group — team chat container
 * group_key: hex-encoded 32-byte AES-256 key (current)
 * new_group_key_hex: rotated key (if null, use group_key)
 * key_version: incremented on key rotation
 * created_at: unix timestamp in seconds
 */
export interface Group {
    id: string;
    name: string;
    creator_id: string;  // User ID (string) who created group
    group_key: string;   // Hex-encoded 32-byte key
    new_group_key_hex: string | null;  // Rotated key (null = no rotation pending)
    key_version: number;  // Incremented on key rotation
    created_at: number;  // Unix timestamp (seconds)
}

/**
 * GroupMessage — encrypted message in group
 * encrypted_message: hex-encoded ciphertext (includes 16-byte auth tag)
 * nonce: hex-encoded 12-byte nonce
 * created_at: unix timestamp in seconds
 */
export interface GroupMessage {
    id: string;
    group_id: string;
    sender_id: string;  // User ID (string) who sent message
    encrypted_message: string;  // Hex-encoded ciphertext + auth tag
    nonce: string;  // Hex-encoded 12-byte nonce
    key_version: number;  // Which group key version was used to encrypt
    created_at: number;  // Unix timestamp (seconds)
}

/**
 * GroupMember — user membership record
 * joined_at: unix timestamp in seconds
 */
export interface GroupMember {
    id: string;  // Member record UUID
    user_id: string;  // User ID (string)
    joined_at: number;  // Unix timestamp (seconds)
}

interface DecryptedMessage extends GroupMessage {
    plaintext?: string;
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

    const removeMember = useCallback(async (groupId: string, memberId: string) => {
        if (!token) return false;
        try {
            const res = await fetch(`${API_BASE}/chat/groups/${groupId}/members/${memberId}`, {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${token}` }
            });
            if (!res.ok) throw new Error('Failed to remove member');
            setCurrentGroupMembers(prev => prev.filter(m => m.id !== memberId));
            return true;
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error');
            return false;
        }
    }, [token]);

    /**
     * Decrypt messages using the current group key
     * Handles key version mismatches gracefully
     */
    const decryptMessages = useCallback(
        async (messages: GroupMessage[], groupKey: string, keyVersion: number): Promise<DecryptedMessage[]> => {
            const { decryptGroupMessage } = await import('../crypto/chatCrypto');

            return Promise.all(
                messages.map(async (msg) => {
                    // Only decrypt if key version matches (supports key rotation)
                    if (msg.key_version === keyVersion) {
                        try {
                            const plaintext = await decryptGroupMessage(
                                msg.encrypted_message,
                                msg.nonce,
                                groupKey
                            );
                            return { ...msg, plaintext };
                        } catch (err) {
                            console.warn(`Failed to decrypt message ${msg.id}:`, err);
                            return { ...msg, plaintext: '[Decryption failed]' };
                        }
                    }
                    // Different key version — skip decryption
                    return msg;
                })
            );
        },
        []
    );

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
        removeMember,
        decryptMessages
    };
}
