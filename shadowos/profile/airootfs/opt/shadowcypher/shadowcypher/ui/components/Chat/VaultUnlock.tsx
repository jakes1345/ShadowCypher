import React, { useEffect } from 'react';

// Vault unlock is no longer needed — messages are stored on the server and
// auth is via API key, not a local vault password. Auto-proceed on mount.
interface VaultUnlockProps {
    onUnlock: () => void;
    token: string | null;
}

export function VaultUnlock({ onUnlock, token }: VaultUnlockProps) {
    useEffect(() => {
        if (token) onUnlock();
    }, [token, onUnlock]);

    return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-secondary)' }}>
            {token ? 'Loading chat...' : 'Sign in to use chat.'}
        </div>
    );
}
