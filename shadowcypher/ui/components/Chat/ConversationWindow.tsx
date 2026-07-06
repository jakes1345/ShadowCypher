import React from 'react';

interface ConversationWindowProps {
    messages: any[];
    currentUser: string;
}

export function ConversationWindow({ messages, currentUser }: ConversationWindowProps) {
    return (
        <div className="conversation-window">
            <div className="messages-container">
                {messages.map((msg) => (
                    <div key={msg.id} className={`message ${msg.sender === currentUser ? 'sent' : 'received'}`}>
                        <div className="message-sender">{msg.sender}</div>
                        <div className="message-text">[Encrypted message - decrypted client-side]</div>
                        <div className="message-time">{new Date(msg.timestamp * 1000).toLocaleTimeString()}</div>
                    </div>
                ))}
            </div>
        </div>
    );
}
