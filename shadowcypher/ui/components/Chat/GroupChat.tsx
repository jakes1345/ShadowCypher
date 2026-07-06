import React, { useState, useEffect } from 'react';
import { useGroupChat, Group, GroupMessage } from '../../hooks/useGroupChat';
import { encryptGroupMessage } from '../../crypto/chatCrypto';
import './GroupChat.css';

interface GroupChatProps {
    groupId: string;
    currentUser: { username: string };  // User object with username
    token: string | null;
    currentGroup: Group | undefined;  // Current group data for keys
}

interface DecryptedMessage extends GroupMessage {
    plaintext?: string;
}

export const GroupChat: React.FC<GroupChatProps> = ({ groupId, currentUser, token, currentGroup }) => {
    const { currentGroupMessages, currentGroupMembers, loading, error, fetchGroupMessages, fetchGroupMembers, sendMessage, decryptMessages } = useGroupChat(token);
    const [input, setInput] = useState('');
    const [sending, setSending] = useState(false);
    const [showMembers, setShowMembers] = useState(false);
    const [decryptedMessages, setDecryptedMessages] = useState<DecryptedMessage[]>([]);

    useEffect(() => {
        if (groupId) {
            fetchGroupMessages(groupId);
            fetchGroupMembers(groupId);
        }
    }, [groupId, fetchGroupMessages, fetchGroupMembers]);

    // Decrypt messages when group key is available
    useEffect(() => {
        if (currentGroup && currentGroupMessages.length > 0) {
            const groupKey = currentGroup.new_group_key_hex || currentGroup.group_key;
            const keyVersion = currentGroup.key_version;

            decryptMessages(currentGroupMessages, groupKey, keyVersion).then(
                decrypted => {
                    setDecryptedMessages(decrypted);
                    // Store current group key in localStorage for UI state
                    localStorage.setItem(`group_key_${groupId}`, groupKey);
                }
            ).catch(err => {
                console.error('Failed to decrypt messages:', err);
            });
        }
    }, [groupId, currentGroup, currentGroupMessages, decryptMessages]);

    const handleSend = async () => {
        if (!input.trim() || !currentGroup || !groupId) return;

        setSending(true);
        try {
            const groupKey = currentGroup.new_group_key_hex || currentGroup.group_key;
            const { ciphertext, nonce } = await encryptGroupMessage(input, groupKey);
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
                        {decryptedMessages.length === 0 ? (
                            <div className="no-messages">No messages yet. Start the conversation!</div>
                        ) : (
                            decryptedMessages.map(msg => (
                                <div
                                    key={msg.id}
                                    className={`message ${msg.sender_id === currentUser.username ? 'sent' : 'received'}`}
                                >
                                    <div className="message-sender">{msg.sender_id}</div>
                                    <div className="message-content">{msg.plaintext || msg.encrypted_message}</div>
                                    <div className="message-time">{new Date(msg.created_at * 1000).toLocaleTimeString()}</div>
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
                                    <span className="member-joined">Joined: {new Date(member.joined_at * 1000).toLocaleDateString()}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};
