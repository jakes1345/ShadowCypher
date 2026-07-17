import React, { useState } from 'react';

interface ContactDiscoveryProps {
    onOpenDm: (handle: string) => Promise<void>;
}

export function ContactDiscovery({ onOpenDm }: ContactDiscoveryProps) {
    const [handle, setHandle] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        const h = handle.trim().replace(/^@/, '');
        if (!h) return;
        setLoading(true);
        setError('');
        try {
            await onOpenDm(h);
            setHandle('');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'User not found');
        } finally {
            setLoading(false);
        }
    };

    return (
        <form className="contact-discovery" onSubmit={handleSubmit} style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>
            <input
                type="text"
                placeholder="@handle"
                value={handle}
                onChange={e => { setHandle(e.target.value); setError(''); }}
                disabled={loading}
                style={{ width: 120 }}
            />
            <button type="submit" disabled={!handle.trim() || loading}>
                {loading ? '...' : 'Open DM'}
            </button>
            {error && <span style={{ color: 'var(--accent-secondary)', fontSize: '0.8rem' }}>{error}</span>}
        </form>
    );
}
