import React, { useState, useEffect } from 'react';
import { VaultUnlock } from './VaultUnlock';
import { ConversationList } from './ConversationList';
import { ConversationWindow } from './ConversationWindow';
import { MessageInput } from './MessageInput';
import { ContactDiscovery } from './ContactDiscovery';
import { InstanceDiscovery } from './InstanceDiscovery';
import { InstanceList } from './InstanceList';
import { useChat } from '../../hooks/useChat';
import { encryptMessage } from '../../crypto/chatCrypto';
import './styles.css';

interface ChatProps {
    token: string | null;
    currentUser: string;
}

export default function Chat({ token, currentUser }: ChatProps) {
    const [vaultUnlocked, setVaultUnlocked] = useState(false);
    const [selectedConversation, setSelectedConversation] = useState<number | null>(null);
    const [sessionKey, setSessionKey] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<'messages' | 'instances'>('messages');
    const { conversations, messages, fetchConversations, fetchMessages, sendMessage } = useChat(token);

    useEffect(() => {
        if (vaultUnlocked && token) {
            fetchConversations();
        }
    }, [vaultUnlocked, token, fetchConversations]);

    useEffect(() => {
        if (selectedConversation && token) {
            fetchMessages(selectedConversation);
            // In a real app, fetch or derive the session key for this conversation
            // For now, use a placeholder that would be set via context or state management
            setSessionKey(localStorage.getItem(`sessionKey_${selectedConversation}`) || null);
        }
    }, [selectedConversation, token, fetchMessages]);

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

    return (
        <div className="chat-container">
            <ConversationList
                conversations={conversations}
                selectedId={selectedConversation}
                onSelect={setSelectedConversation}
            />
            <div className="chat-main">
                <div className="chat-tabs">
                    <button
                        className={`tab-button ${activeTab === 'messages' ? 'active' : ''}`}
                        onClick={() => setActiveTab('messages')}
                    >
                        Messages
                    </button>
                    <button
                        className={`tab-button ${activeTab === 'instances' ? 'active' : ''}`}
                        onClick={() => setActiveTab('instances')}
                    >
                        Instances
                    </button>
                </div>
                {activeTab === 'messages' ? (
                    <>
                        {selectedConversation ? (
                            <>
                                <ConversationWindow messages={messages} currentUser={currentUser} />
                                <MessageInput onSend={handleSendMessage} />
                            </>
                        ) : (
                            <div className="no-conversation">Select a conversation or <ContactDiscovery onAddContact={() => {}} /></div>
                        )}
                    </>
                ) : (
                    <div className="instances-panel">
                        <InstanceDiscovery onInstanceAdded={() => {}} />
                        <InstanceList />
                    </div>
                )}
            </div>
        </div>
    );
}
