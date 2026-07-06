import React, { useState, useEffect } from 'react';
import { VaultUnlock } from './VaultUnlock';
import { ConversationList } from './ConversationList';
import { ConversationWindow } from './ConversationWindow';
import { MessageInput } from './MessageInput';
import { ContactDiscovery } from './ContactDiscovery';
import { InstanceDiscovery } from './InstanceDiscovery';
import { InstanceList } from './InstanceList';
import { GroupList } from './GroupList';
import { GroupChat } from './GroupChat';
import { GroupForm } from './GroupForm';
import { GroupAdminPanel } from './GroupAdminPanel';
import { useChat } from '../../hooks/useChat';
import { useGroupChat } from '../../hooks/useGroupChat';
import { encryptMessage } from '../../crypto/chatCrypto';
import './styles.css';
import './GroupChat.css';

interface ChatProps {
    token: string | null;
    currentUser: { username: string };
}

export default function Chat({ token, currentUser }: ChatProps) {
    const [vaultUnlocked, setVaultUnlocked] = useState(false);
    const [selectedConversation, setSelectedConversation] = useState<number | null>(null);
    const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
    const [sessionKey, setSessionKey] = useState<string | null>(null);
    const [groupSessionKey, setGroupSessionKey] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'messages' | 'instances' | 'groups'>('messages');
    const [showGroupForm, setShowGroupForm] = useState(false);
    const [showGroupAdmin, setShowGroupAdmin] = useState(false);
    const { conversations, messages, fetchConversations, fetchMessages, sendMessage } = useChat(token);
    const { groups, fetchGroups } = useGroupChat(token);

    useEffect(() => {
        if (vaultUnlocked && token) {
            fetchConversations();
            fetchGroups();
        }
    }, [vaultUnlocked, token, fetchConversations, fetchGroups]);

    useEffect(() => {
        if (selectedConversation && token) {
            fetchMessages(selectedConversation);
            // In a real app, fetch or derive the session key for this conversation
            // For now, use a placeholder that would be set via context or state management
            setSessionKey(localStorage.getItem(`sessionKey_${selectedConversation}`) || null);
        }
    }, [selectedConversation, token, fetchMessages]);

    useEffect(() => {
        if (selectedGroup && token) {
            // In a real app, fetch or derive the session key for this group
            // For now, use a placeholder that would be set via context or state management
            setGroupSessionKey(localStorage.getItem(`groupSessionKey_${selectedGroup}`) || null);
        }
    }, [selectedGroup, token]);

    if (!vaultUnlocked) {
        return <VaultUnlock onUnlock={() => setVaultUnlocked(true)} />;
    }

    const handleSendMessage = async (plaintext: string) => {
        if (!selectedConversation || !sessionKey) return;
        try {
            const { ciphertext, nonce } = encryptMessage(plaintext, sessionKey);
            await sendMessage(selectedConversation, ciphertext, nonce);
            // Optionally refresh messages after sending
            await fetchMessages(selectedConversation);
        } catch (error) {
            console.error('Failed to send message:', error);
        }
    };

    const getGroupData = () => {
        return groups.find(g => g.id === selectedGroup);
    };

    return (
        <div className="chat-container">
            {activeTab === 'groups' && (
                <GroupList
                    token={token}
                    onSelectGroup={setSelectedGroup}
                    selectedGroupId={selectedGroup || undefined}
                />
            )}
            {activeTab !== 'groups' && (
                <ConversationList
                    conversations={conversations}
                    selectedId={selectedConversation}
                    onSelect={setSelectedConversation}
                />
            )}
            <div className="chat-main">
                <div className="chat-tabs">
                    <button
                        className={`tab-button ${activeTab === 'messages' ? 'active' : ''}`}
                        onClick={() => {
                            setActiveTab('messages');
                            setSelectedGroup(null);
                        }}
                    >
                        Messages
                    </button>
                    <button
                        className={`tab-button ${activeTab === 'instances' ? 'active' : ''}`}
                        onClick={() => {
                            setActiveTab('instances');
                            setSelectedGroup(null);
                        }}
                    >
                        Instances
                    </button>
                    <button
                        className={`tab-button ${activeTab === 'groups' ? 'active' : ''}`}
                        onClick={() => setActiveTab('groups')}
                    >
                        Groups
                    </button>
                </div>
                {activeTab === 'messages' ? (
                    <>
                        {selectedConversation ? (
                            <>
                                <ConversationWindow messages={messages} currentUser={currentUser.username} />
                                <MessageInput onSend={handleSendMessage} />
                            </>
                        ) : (
                            <div className="no-conversation">Select a conversation or <ContactDiscovery onAddContact={() => {}} /></div>
                        )}
                    </>
                ) : activeTab === 'instances' ? (
                    <div className="instances-panel">
                        <InstanceDiscovery onInstanceAdded={() => {}} />
                        <InstanceList />
                    </div>
                ) : (
                    <div className="groups-panel">
                        {selectedGroup && getGroupData() ? (
                            <div className="group-chat-view">
                                <GroupChat
                                    groupId={selectedGroup}
                                    currentUser={currentUser}
                                    token={token}
                                    currentGroup={getGroupData()}
                                />
                                <div className="group-sidebar">
                                    <button
                                        className="admin-toggle"
                                        onClick={() => setShowGroupAdmin(!showGroupAdmin)}
                                    >
                                        {showGroupAdmin ? 'Hide Admin' : 'Show Admin'}
                                    </button>
                                    {showGroupAdmin && getGroupData() && (
                                        <GroupAdminPanel
                                            groupId={selectedGroup}
                                            creatorId={getGroupData()!.creator_id}
                                            currentUser={currentUser}
                                            token={token}
                                        />
                                    )}
                                </div>
                            </div>
                        ) : (
                            <div className="groups-empty">
                                <p>Select a group or create a new one</p>
                                <button
                                    className="create-group-button"
                                    onClick={() => setShowGroupForm(!showGroupForm)}
                                >
                                    {showGroupForm ? 'Cancel' : '+ Create Group'}
                                </button>
                                {showGroupForm && (
                                    <GroupForm
                                        token={token}
                                        onGroupCreated={(id) => {
                                            setSelectedGroup(id);
                                            setShowGroupForm(false);
                                            fetchGroups();
                                        }}
                                        onCancel={() => setShowGroupForm(false)}
                                    />
                                )}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
