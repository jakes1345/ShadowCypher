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
                        placeholder="Their username"
                        value={contactInfo.username}
                        onChange={(e) => setContactInfo({ ...contactInfo, username: e.target.value })}
                    />
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
            {mode === 'qr' && (
                <div className="feature-coming-soon">
                    <span style={{ fontSize: '2rem' }}>📱</span>
                    <p><strong>QR Code sharing coming soon</strong></p>
                    <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Your contact will scan your QR code to add you securely. Tap "Verify Fingerprint" for now.</p>
                </div>
            )}
            {mode === 'link' && (
                <div className="feature-coming-soon">
                    <span style={{ fontSize: '2rem' }}>🔗</span>
                    <p><strong>Link sharing coming soon</strong></p>
                    <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Generate a one-time share link. Tap "Verify Fingerprint" for now.</p>
                </div>
            )}
        </div>
    );
}
