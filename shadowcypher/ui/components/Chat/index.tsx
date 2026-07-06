import React, { useState, useEffect } from 'react';
import { VaultUnlock } from './VaultUnlock';
import { ConversationList } from './ConversationList';
import { ConversationWindow } from './ConversationWindow';
import { MessageInput } from './MessageInput';
import { ContactDiscovery } from './ContactDiscovery';
import { useChat } from '../../hooks/useChat';
import './styles.css';

interface ChatProps {
    token: string | null;
    currentUser: string;
}

export default function Chat({ token, currentUser }: ChatProps) {
    const [vaultUnlocked, setVaultUnlocked] = useState(false);
    const [selectedConversation, setSelectedConversation] = useState<number | null>(null);
    const { conversations, messages, fetchConversations, fetchMessages, sendMessage } = useChat(token);

    useEffect(() => {
        if (vaultUnlocked && token) {
            fetchConversations();
        }
    }, [vaultUnlocked, token, fetchConversations]);

    useEffect(() => {
        if (selectedConversation && token) {
            fetchMessages(selectedConversation);
        }
    }, [selectedConversation, token, fetchMessages]);

    if (!vaultUnlocked) {
        return <VaultUnlock onUnlock={() => setVaultUnlocked(true)} />;
    }

    const handleSendMessage = async (plaintext: string) => {
        if (!selectedConversation) return;
        // Encrypt message client-side
        // const { ciphertext, nonce } = await encryptMessage(...);
        // await sendMessage(selectedConversation, ciphertext, nonce);
    };

    return (
        <div className="chat-container">
            <ConversationList
                conversations={conversations}
                selectedId={selectedConversation}
                onSelect={setSelectedConversation}
            />
            <div className="chat-main">
                {selectedConversation ? (
                    <>
                        <ConversationWindow messages={messages} currentUser={currentUser} />
                        <MessageInput onSend={handleSendMessage} />
                    </>
                ) : (
                    <div className="no-conversation">Select a conversation or <ContactDiscovery onAddContact={() => {}} /></div>
                )}
            </div>
        </div>
    );
}
