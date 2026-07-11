import React from 'react';
import { decryptMessage } from '../../crypto/chatCrypto';

interface Message {
    id: number;
    sender: string;
    timestamp: number;
    encrypted_message: string;
    nonce: string;
}

interface ConversationWindowProps {
    messages: Message[];
    currentUser: string;
    sessionKey: string | null;
}

export function ConversationWindow({ messages, currentUser, sessionKey }: ConversationWindowProps) {
    function decryptText(msg: Message): string {
        if (!sessionKey) return '[Vault locked — unlock to read messages]';
        try {
            return decryptMessage(msg.encrypted_message, msg.nonce, sessionKey);
        } catch {
            return '[Decryption failed]';
        }
    }

    return (
        <div className="conversation-window">
            <div className="messages-container">
                {messages.length === 0 && (
                    <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '40px', fontSize: '0.85rem' }}>
                        No messages yet. Send the first one!
                    </div>
                )}
                {messages.map((msg) => (
                    <div key={msg.id} className={`message ${msg.sender === currentUser ? 'sent' : 'received'}`}>
                        <div className="message-sender">{msg.sender}</div>
                        <div className="message-text">{decryptText(msg)}</div>
                        <div className="message-time">{new Date(msg.timestamp * 1000).toLocaleTimeString()}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}
