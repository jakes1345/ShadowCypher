import React, { useState, useEffect } from 'react';
import { useGroupChat, Group, GroupMessage } from '../../hooks/useGroupChat';
import './GroupChat.css';

interface GroupChatProps {
    groupId: string;
    currentUser: { username: string; id?: string };
    token: string | null;
    currentGroup: Group | undefined;
}

export const GroupChat: React.FC<GroupChatProps> = ({ groupId, currentUser, token }) => {
    const { currentGroupMessages, loading, error, fetchGroupMessages, sendMessage } = useGroupChat(token);
    const [input, setInput] = useState('');
    const [sending, setSending] = useState(false);

    useEffect(() => {
        if (groupId) fetchGroupMessages(groupId);
    }, [groupId, fetchGroupMessages]);

    const handleSend = async () => {
        if (!input.trim() || !groupId) return;
        setSending(true);
        try {
            await sendMessage(groupId, input.trim());
            setInput('');
            await fetchGroupMessages(groupId);
        } catch (err) {
            console.error('Failed to send message:', err);
        } finally {
            setSending(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
    };

    if (loading) return <div className="group-chat-loading">Loading...</div>;

    return (
        <div className="group-chat-container">
            <div className="group-chat-header">
                <h2>Group Chat</h2>
            </div>
            {error && <div className="error-message">{error}</div>}
            <div className="group-chat-main">
                <div className="messages-section">
                    <div className="messages-container">
                        {currentGroupMessages.length === 0 ? (
                            <div className="no-messages">No messages yet. Start the conversation!</div>
                        ) : (
                            currentGroupMessages.map((msg: GroupMessage) => (
                                <div
                                    key={msg.id}
                                    className={`message ${msg.nick === currentUser.username ? 'sent' : 'received'}`}
                                >
                                    <div className="message-sender">{msg.nick}</div>
                                    <div className="message-content">{msg.content}</div>
                                    <div className="message-time">
                                        {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                    <div className="message-input-section">
                        <textarea
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            onKeyPress={handleKeyPress}
                            placeholder="Type a message..."
                            disabled={sending}
                            rows={3}
                        />
                        <button onClick={handleSend} disabled={!input.trim() || sending} className="send-button">
                            {sending ? 'Sending...' : 'Send'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};
