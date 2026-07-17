import { useState, useCallback } from 'react';

const API_BASE = 'https://api.shadowcypher.site';

// Repurposed: shows users online in the global room instead of P2P instances
export interface OnlineUser {
    instance_id: string;
    public_key: string;
    endpoint: string | null;
    is_online: boolean;
    last_heartbeat: number;
}

interface PresenceRow {
    user_id: string;
    nick: string;
    seen_at: string;
}

export function useInstanceDiscovery(apiKey?: string | null) {
    const [instances, setInstances] = useState<OnlineUser[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    function authHeader() {
        return apiKey ? { Authorization: `Bearer ${apiKey}` } : {} as Record<string, string>;
    }

    // Lists users online in the global room — mapped to the old Instance shape
    const listInstances = useCallback(async (room = 'global') => {
        if (!apiKey) return;
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(
                `${API_BASE}/v1/chat/online?room=${encodeURIComponent(room)}`,
                { headers: authHeader() }
            );
            if (!res.ok) throw new Error(`${res.status}`);
            const data = await res.json() as { online: PresenceRow[] };
            setInstances((data.online ?? []).map(u => ({
                instance_id: u.user_id,
                public_key: '',
                endpoint: null,
                is_online: true,
                last_heartbeat: Math.floor(new Date(u.seen_at).getTime() / 1000),
            })));
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to fetch online users');
        } finally {
            setLoading(false);
        }
    }, [apiKey]);

    // Not applicable to the Worker model — no-op
    const registerInstance = useCallback(async (_instanceId: string, _pubkey: string, _endpoint?: string) => {
        return null;
    }, []);

    const getInstanceStatus = useCallback(async (_instanceId: string) => {
        return null;
    }, []);

    return { instances, loading, error, listInstances, registerInstance, getInstanceStatus };
}
