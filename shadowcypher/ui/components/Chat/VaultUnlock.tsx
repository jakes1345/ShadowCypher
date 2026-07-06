import React, { useState } from 'react';
import './styles.css';

interface VaultUnlockProps {
    onUnlock: (password: string) => void;
}

export function VaultUnlock({ onUnlock }: VaultUnlockProps) {
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const handleUnlock = () => {
        if (!password) {
            setError('Password required');
            return;
        }
        onUnlock(password);
    };

    return (
        <div className="vault-unlock-overlay">
            <div className="vault-unlock-dialog">
                <div className="vault-lock-icon">🔒</div>
                <h2>Unlock Your Vault</h2>
                <p>Enter your master password to access encrypted messages</p>
                <input
                    type="password"
                    placeholder="Master password"
                    value={password}
                    onChange={(e) => {
                        setPassword(e.target.value);
                        setError('');
                    }}
                    onKeyPress={(e) => e.key === 'Enter' && handleUnlock()}
                    autoFocus
                    className="vault-password-input"
                />
                {error && <div className="error-message">{error}</div>}
                <button onClick={handleUnlock} className="unlock-button">Unlock Vault</button>
            </div>
        </div>
    );
}
