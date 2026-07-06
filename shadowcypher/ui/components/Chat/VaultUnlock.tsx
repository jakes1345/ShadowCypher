import React, { useState } from 'react';
import './styles.css';

interface VaultUnlockProps {
    onUnlock: (vaultKey: string) => void;
    token: string | null;
}

export function VaultUnlock({ onUnlock, token }: VaultUnlockProps) {
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleUnlock = async () => {
        if (!password) {
            setError('Password required');
            return;
        }

        setLoading(true);
        setError('');

        try {
            // Validate vault password with backend
            const response = await fetch('http://localhost:8000/chat/vault/unlock', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({ vault_password: password }),
            });

            if (!response.ok) {
                const data = await response.json();
                setError(data.detail || 'Invalid vault password');
                setLoading(false);
                return;
            }

            const data = await response.json();
            // Vault password is correct, derive keys and unlock
            onUnlock(data.vault_key);
        } catch (err) {
            setError('Failed to unlock vault: ' + (err instanceof Error ? err.message : 'Unknown error'));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="vault-unlock-overlay">
            <div className="vault-unlock-dialog">
                <div className="vault-lock-icon">🔒</div>
                <h1>Vault Locked</h1>
                <p>This device requires a vault password to access encrypted messages.</p>
                <p style={{ fontSize: '0.9em', color: '#94a3b8' }}>If seized, law enforcement cannot access messages without this password.</p>

                <input
                    type="password"
                    placeholder="Vault password"
                    value={password}
                    onChange={(e) => {
                        setPassword(e.target.value);
                        setError('');
                    }}
                    onKeyPress={(e) => e.key === 'Enter' && !loading && handleUnlock()}
                    autoFocus
                    disabled={loading}
                    className="vault-password-input"
                />
                {error && <div className="error-message">{error}</div>}
                <button
                    onClick={handleUnlock}
                    disabled={loading}
                    className="unlock-button"
                >
                    {loading ? 'Validating...' : 'Unlock Vault'}
                </button>

                <div style={{ marginTop: '20px', fontSize: '0.85em', color: '#64748b', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '15px' }}>
                    <strong>⚠️ Important:</strong> This password is NOT stored. Lost passwords cannot be recovered.
                </div>
            </div>
        </div>
    );
}
