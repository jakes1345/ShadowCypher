import { useState, useCallback } from 'react';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export function useChat(token: string | null) {
    const [conversations, setConversations] = useState<any[]>([]);
    const [messages, setMessages] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);

    const fetchConversations = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const res = await fetch(`${API_BASE}/chat/conversations`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            const data = await res.json();
            setConversations(data);
        } finally {
            setLoading(false);
        }
    }, [token]);

    const fetchMessages = useCallback(async (conversationId: number) => {
        if (!token) return;
        setLoading(true);
        try {
            const res = await fetch(
                `${API_BASE}/chat/conversations/${conversationId}/messages`,
                { headers: { Authorization: `Bearer ${token}` } }
            );
            const data = await res.json();
            setMessages(data);
        } finally {
            setLoading(false);
        }
    }, [token]);

    const sendMessage = useCallback(async (conversationId: number, encryptedMessage: string, nonce: string) => {
        if (!token) return;
        const res = await fetch(`${API_BASE}/chat/send-message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`
            },
            body: JSON.stringify({ conversation_id: conversationId, encrypted_message: encryptedMessage, nonce })
        });
        return await res.json();
    }, [token]);

    const addContact = useCallback(async (contactUsername: string, contactPubkey: string, fingerprint: string) => {
        if (!token) return;
        const res = await fetch(`${API_BASE}/chat/add-contact`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`
            },
            body: JSON.stringify({ contact_username: contactUsername, contact_pubkey: contactPubkey, fingerprint })
        });
        return await res.json();
    }, [token]);

    return { conversations, messages, loading, fetchConversations, fetchMessages, sendMessage, addContact };
}
