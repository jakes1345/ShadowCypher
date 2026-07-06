import React from 'react';

interface ConversationListProps {
    conversations: any[];
    selectedId: number | null;
    onSelect: (id: number) => void;
}

export function ConversationList({ conversations, selectedId, onSelect }: ConversationListProps) {
    return (
        <div className="conversation-list">
            <div className="conversation-list-header">Messages</div>
            {conversations.map((conv) => (
                <div
                    key={conv.conversation_id}
                    className={`conversation-item ${selectedId === conv.conversation_id ? 'active' : ''}`}
                    onClick={() => onSelect(conv.conversation_id)}
                >
                    <div className="conversation-name">{conv.contact_username}</div>
                    <div className="conversation-preview">{conv.last_message || 'No messages'}</div>
                </div>
            ))}
        </div>
    );
}
