import React, { useState } from 'react';

interface ContactDiscoveryProps {
    onAddContact: (username: string, pubkey: string, fingerprint: string) => void;
}

export function ContactDiscovery({ onAddContact }: ContactDiscoveryProps) {
    const [mode, setMode] = useState<'qr' | 'link' | 'fingerprint' | null>(null);
    const [contactInfo, setContactInfo] = useState({ username: '', pubkey: '', fingerprint: '' });

    return (
        <div className="contact-discovery">
            <div className="discovery-methods">
                <button onClick={() => setMode('qr')}>📱 QR Code</button>
                <button onClick={() => setMode('link')}>🔗 Share Link</button>
                <button onClick={() => setMode('fingerprint')}>👆 Verify Fingerprint</button>
            </div>

            {mode === 'fingerprint' && (
                <div className="fingerprint-dialog">
                    <p>Ask them to share their fingerprint:</p>
                    <input
                        type="text"
                        placeholder="8-char fingerprint"
                        value={contactInfo.fingerprint}
                        onChange={(e) => setContactInfo({ ...contactInfo, fingerprint: e.target.value })}
                    />
                    <button onClick={() => onAddContact(contactInfo.username, contactInfo.pubkey, contactInfo.fingerprint)}>
                        Verify & Add Contact
                    </button>
                </div>
            )}
        </div>
    );
}
