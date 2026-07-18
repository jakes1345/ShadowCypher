import React from 'react';
import type { ChatMessage } from '../../hooks/useChat';

interface ConversationWindowProps {
    messages: ChatMessage[];
    currentNick: string;
}

export function ConversationWindow({ messages, currentNick }: ConversationWindowProps) {
    return (
        <div className="conversation-window">
            <div className="messages-container">
                {messages.length === 0 && (
                    <div style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '40px', fontSize: '0.85rem' }}>
                        No messages yet. Send the first one!
                    </div>
                )}
                {messages.map(msg => (
                    <div key={msg.id} className={`message ${msg.nick === currentNick ? 'sent' : 'received'}`}>
                        <div className="message-sender">{msg.nick}</div>
                        <div className="message-text">{msg.content}</div>
                        <div className="message-time">
                            {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
