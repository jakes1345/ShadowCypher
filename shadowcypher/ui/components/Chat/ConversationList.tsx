import React from 'react';
import type { ChatRoom } from '../../hooks/useChat';

interface ConversationListProps {
    rooms: ChatRoom[];
    dms: ChatRoom[];
    selectedName: string | null;
    onSelect: (roomName: string) => void;
}

export function ConversationList({ rooms, dms, selectedName, onSelect }: ConversationListProps) {
    return (
        <div className="conversation-list">
            <div className="conversation-list-header">Rooms</div>
            {rooms.map(room => (
                <div
                    key={room.name}
                    className={`conversation-item ${selectedName === room.name ? 'active' : ''}`}
                    onClick={() => onSelect(room.name)}
                >
                    <div className="conversation-name">{room.display_name || `#${room.name}`}</div>
                    {room.topic && <div className="conversation-preview">{room.topic}</div>}
                </div>
            ))}
            {dms.length > 0 && (
                <>
                    <div className="conversation-list-header" style={{ marginTop: 12 }}>Direct Messages</div>
                    {dms.map(dm => (
                        <div
                            key={dm.name}
                            className={`conversation-item ${selectedName === dm.name ? 'active' : ''}`}
                            onClick={() => onSelect(dm.name)}
                        >
                            <div className="conversation-name">{dm.display_name || dm.other_nick || dm.name}</div>
                        </div>
                    ))}
                </>
            )}
        </div>
    );
}
