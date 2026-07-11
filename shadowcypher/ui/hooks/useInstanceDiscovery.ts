import { useState, useCallback } from 'react';

interface Instance {
  instance_id: string;
  public_key: string;
  endpoint: string | null;
  is_online: boolean;
  last_heartbeat: number;
}

export function useInstanceDiscovery() {
  const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';
  const [instances, setInstances] = useState<Instance[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const registerInstance = useCallback(
    async (instance_id: string, pubkey: string, endpoint?: string) => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`${API_BASE}/chat/instances/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ public_key: pubkey, endpoint }),
        });
        if (!response.ok) throw new Error(await response.text());
        const instance = await response.json();
        setInstances(prev => [...prev, instance]);
        return instance;
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const listInstances = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/chat/instances`);
      if (!response.ok) throw new Error(await response.text());
      setInstances(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  const getInstanceStatus = useCallback(async (instance_id: string) => {
    const response = await fetch(`${API_BASE}/chat/instances/${instance_id}`);
    if (!response.ok) throw new Error(await response.text());
    return await response.json();
  }, []);

  return { instances, loading, error, registerInstance, listInstances, getInstanceStatus };
}
