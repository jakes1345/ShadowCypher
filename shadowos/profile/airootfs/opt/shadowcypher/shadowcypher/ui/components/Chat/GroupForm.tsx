import React, { useState } from 'react';
import { useGroupChat } from '../../hooks/useGroupChat';

interface GroupFormProps {
    token: string | null;
    onGroupCreated?: (groupId: string) => void;
    onCancel?: () => void;
}

export const GroupForm: React.FC<GroupFormProps> = ({ token, onGroupCreated, onCancel }) => {
    const [groupName, setGroupName] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const { createGroup, error } = useGroupChat(token);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!groupName.trim()) return;

        setSubmitting(true);
        try {
            const group = await createGroup(groupName);
            if (group) {
                setGroupName('');
                onGroupCreated?.(group.id);
            }
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <form className="group-form" onSubmit={handleSubmit}>
            <h3>Create New Group</h3>
            <div className="form-group">
                <label htmlFor="group-name">Group Name</label>
                <input
                    id="group-name"
                    type="text"
                    value={groupName}
                    onChange={(e) => setGroupName(e.target.value)}
                    placeholder="Enter group name..."
                    disabled={submitting}
                />
            </div>
            {error && <div className="error-message">{error}</div>}
            <div className="form-actions">
                <button type="submit" disabled={!groupName.trim() || submitting}>
                    {submitting ? 'Creating...' : 'Create Group'}
                </button>
                {onCancel && (
                    <button type="button" onClick={onCancel} className="cancel-button">
                        Cancel
                    </button>
                )}
            </div>
        </form>
    );
};
