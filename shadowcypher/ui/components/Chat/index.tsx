import React, { useState, useEffect, useCallback } from 'react';
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
import './styles.css';
import './GroupChat.css';

// token = sc_live_* API key (from user.user_metadata.api_key in Supabase)
interface ChatProps {
    token: string | null;
    currentUser: { username: string; id?: string };
}

export default function Chat({ token, currentUser }: ChatProps) {
    const [selectedRoom, setSelectedRoom] = useState<string | null>(null);
    const [selectedGroup, setSelectedGroup] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'messages' | 'instances' | 'groups'>('messages');
    const [showGroupForm, setShowGroupForm] = useState(false);
    const [showGroupAdmin, setShowGroupAdmin] = useState(false);

    const {
        rooms, dms, messages, loading,
        fetchRooms, fetchDms, fetchMessages, sendMessage, openDm,
    } = useChat(token);

    const { groups, fetchGroups } = useGroupChat(token);

    useEffect(() => {
        if (!token) return;
        fetchRooms();
        fetchDms();
        fetchGroups();
    }, [token, fetchRooms, fetchDms, fetchGroups]);

    // Auto-select global room
    useEffect(() => {
        if (!selectedRoom && rooms.length > 0) {
            const global = rooms.find(r => r.name === 'global');
            setSelectedRoom(global?.name ?? rooms[0].name);
        }
    }, [rooms, selectedRoom]);

    useEffect(() => {
        if (selectedRoom) fetchMessages(selectedRoom);
    }, [selectedRoom, fetchMessages]);

    const handleSend = async (content: string) => {
        if (!selectedRoom) return;
        await sendMessage(selectedRoom, content);
        await fetchMessages(selectedRoom);
    };

    const handleOpenDm = useCallback(async (handle: string) => {
        const roomName = await openDm(handle);
        if (roomName) {
            await fetchDms();
            setSelectedRoom(roomName);
        }
    }, [openDm, fetchDms]);

    const currentGroup = groups.find(g => g.id === selectedGroup);

    if (!token) {
        return (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-secondary)' }}>
                Sign in to use chat.
            </div>
        );
    }

    return (
        <div className="chat-container">
            {activeTab === 'groups' ? (
                <GroupList
                    token={token}
                    onSelectGroup={setSelectedGroup}
                    selectedGroupId={selectedGroup ?? undefined}
                />
            ) : (
                <ConversationList
                    rooms={rooms}
                    dms={dms}
                    selectedName={selectedRoom}
                    onSelect={name => { setSelectedRoom(name); setActiveTab('messages'); }}
                />
            )}

            <div className="chat-main">
                <div className="chat-tabs">
                    <button
                        className={`tab-button ${activeTab === 'messages' ? 'active' : ''}`}
                        onClick={() => { setActiveTab('messages'); setSelectedGroup(null); }}
                    >
                        Messages
                    </button>
                    <button
                        className={`tab-button ${activeTab === 'instances' ? 'active' : ''}`}
                        onClick={() => { setActiveTab('instances'); setSelectedGroup(null); }}
                    >
                        Online
                    </button>
                    <button
                        className={`tab-button ${activeTab === 'groups' ? 'active' : ''}`}
                        onClick={() => setActiveTab('groups')}
                    >
                        Groups
                    </button>
                </div>

                {activeTab === 'messages' && (
                    <>
                        {selectedRoom ? (
                            <>
                                <ConversationWindow messages={messages} currentNick={currentUser.username} />
                                <MessageInput onSend={handleSend} />
                            </>
                        ) : (
                            <div className="no-conversation">
                                {loading ? 'Loading...' : (
                                    <>Select a room or <ContactDiscovery onOpenDm={handleOpenDm} /></>
                                )}
                            </div>
                        )}
                    </>
                )}

                {activeTab === 'instances' && (
                    <div className="instances-panel">
                        <InstanceDiscovery onInstanceAdded={() => {}} token={token} />
                        <InstanceList token={token} />
                    </div>
                )}

                {activeTab === 'groups' && (
                    <div className="groups-panel">
                        {selectedGroup && currentGroup ? (
                            <div className="group-chat-view">
                                <GroupChat
                                    groupId={selectedGroup}
                                    currentUser={currentUser}
                                    token={token}
                                    currentGroup={currentGroup}
                                />
                                <div className="group-sidebar">
                                    <button className="admin-toggle" onClick={() => setShowGroupAdmin(!showGroupAdmin)}>
                                        {showGroupAdmin ? 'Hide Admin' : 'Show Admin'}
                                    </button>
                                    {showGroupAdmin && (
                                        <GroupAdminPanel
                                            groupId={selectedGroup}
                                            creatorId={currentGroup.is_owner ? currentUser.username : ''}
                                            creatorUserId={currentGroup.is_owner ? currentUser.id : undefined}
                                            currentUser={currentUser}
                                            token={token}
                                        />
                                    )}
                                </div>
                            </div>
                        ) : (
                            <div className="groups-empty">
                                <p>Select a group or create a new one</p>
                                <button className="create-group-button" onClick={() => setShowGroupForm(!showGroupForm)}>
                                    {showGroupForm ? 'Cancel' : '+ Create Group'}
                                </button>
                                {showGroupForm && (
                                    <GroupForm
                                        token={token}
                                        onGroupCreated={id => {
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
