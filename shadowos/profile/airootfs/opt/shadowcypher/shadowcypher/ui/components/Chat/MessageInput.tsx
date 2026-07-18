import React, { useState } from 'react';

interface MessageInputProps {
    onSend: (message: string) => void;
}

export function MessageInput({ onSend }: MessageInputProps) {
    const [input, setInput] = useState('');

    const handleSend = () => {
        if (input.trim()) {
            onSend(input);
            setInput('');
        }
    };

    return (
        <div className="message-input-container">
            <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSend();
                    }
                }}
                placeholder="Type encrypted message..."
                className="message-input"
            />
            <button onClick={handleSend} className="send-button">Send 🔒</button>
        </div>
    );
}
