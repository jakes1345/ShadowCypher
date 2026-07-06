import React, { useState, useEffect } from 'react';
import { useGroupChat } from '../../hooks/useGroupChat';
import { encryptMessage } from '../../crypto/chatCrypto';
import './GroupChat.css';

interface GroupChatProps {
    groupId: string;
    currentUser: string;
    token: string | null;
    sessionKey: string | null;
}

export const GroupChat: React.FC<GroupChatProps> = ({ groupId, currentUser, token, sessionKey }) => {
    const { currentGroupMessages, currentGroupMembers, loading, error, fetchGroupMessages, fetchGroupMembers, sendMessage } = useGroupChat(token);
    const [input, setInput] = useState('');
    const [sending, setSending] = useState(false);
    const [showMembers, setShowMembers] = useState(false);

    useEffect(() => {
        if (groupId) {
            fetchGroupMessages(groupId);
            fetchGroupMembers(groupId);
        }
    }, [groupId, fetchGroupMessages, fetchGroupMembers]);

    const handleSend = async () => {
        if (!input.trim() || !sessionKey || !groupId) return;

        setSending(true);
        try {
            const { ciphertext, nonce } = encryptMessage(input, sessionKey);
            await sendMessage(groupId, ciphertext, nonce);
            setInput('');
            // Refresh messages
            await fetchGroupMessages(groupId);
        } catch (err) {
            console.error('Failed to send message:', err);
        } finally {
            setSending(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    if (loading) {
        return <div className="group-chat-loading">Loading group chat...</div>;
    }

    return (
        <div className="group-chat-container">
            <div className="group-chat-header">
                <div className="header-content">
                    <h2>Group Chat</h2>
                    <button
                        className="members-toggle"
                        onClick={() => setShowMembers(!showMembers)}
                    >
                        👥 Members ({currentGroupMembers.length})
                    </button>
                </div>
            </div>

            {error && <div className="error-message">{error}</div>}

            <div className="group-chat-main">
                <div className="messages-section">
                    <div className="messages-container">
                        {currentGroupMessages.length === 0 ? (
                            <div className="no-messages">No messages yet. Start the conversation!</div>
                        ) : (
                            currentGroupMessages.map(msg => (
                                <div
                                    key={msg.id}
                                    className={`message ${msg.sender_id === currentUser ? 'sent' : 'received'}`}
                                >
                                    <div className="message-sender">{msg.sender_id}</div>
                                    <div className="message-content">{msg.encrypted_message}</div>
                                    <div className="message-time">{new Date(msg.created_at).toLocaleTimeString()}</div>
                                </div>
                            ))
                        )}
                    </div>
                    <div className="message-input-section">
                        <textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyPress={handleKeyPress}
                            placeholder="Type your encrypted message..."
                            disabled={sending}
                            rows={3}
                        />
                        <button
                            onClick={handleSend}
                            disabled={!input.trim() || sending}
                            className="send-button"
                        >
                            {sending ? 'Sending...' : 'Send'}
                        </button>
                    </div>
                </div>

                {showMembers && (
                    <div className="members-section">
                        <div className="members-header">
                            <h3>Members</h3>
                        </div>
                        <div className="members-list">
                            {currentGroupMembers.map(member => (
                                <div key={member.id} className="member-item">
                                    <span className="member-name">{member.user_id}</span>
                                    <span className="member-joined">Joined: {new Date(member.joined_at).toLocaleDateString()}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};
