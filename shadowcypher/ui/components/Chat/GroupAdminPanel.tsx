import React, { useState, useEffect } from 'react';
import { useGroupChat } from '../../hooks/useGroupChat';

interface GroupAdminPanelProps {
    groupId: string;
    creatorId: string;
    currentUser: string;
    token: string | null;
}

export const GroupAdminPanel: React.FC<GroupAdminPanelProps> = ({
    groupId,
    creatorId,
    currentUser,
    token
}) => {
    const [newMemberId, setNewMemberId] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const { currentGroupMembers, fetchGroupMembers, addMember, removeMember, error } = useGroupChat(token);

    useEffect(() => {
        if (groupId) {
            fetchGroupMembers(groupId);
        }
    }, [groupId, fetchGroupMembers]);

    // Only creator can manage
    const isCreator = currentUser === creatorId;

    const handleAddMember = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newMemberId.trim()) return;

        setSubmitting(true);
        try {
            const success = await addMember(groupId, newMemberId);
            if (success) {
                setNewMemberId('');
            }
        } finally {
            setSubmitting(false);
        }
    };

    const handleRemoveMember = async (memberId: string, userId: string) => {
        if (!window.confirm(`Remove ${userId} from group?`)) return;

        setSubmitting(true);
        try {
            await removeMember(groupId, memberId);
        } finally {
            setSubmitting(false);
        }
    };

    if (!isCreator) {
        return (
            <div className="admin-panel">
                <p className="not-creator">Only the group creator can manage members</p>
            </div>
        );
    }

    return (
        <div className="admin-panel">
            <h3>👨‍💼 Admin Panel</h3>

            {error && <div className="error-message">{error}</div>}

            <form onSubmit={handleAddMember} className="add-member-form">
                <div className="form-group">
                    <label htmlFor="member-id">Add Member by ID</label>
                    <input
                        id="member-id"
                        type="text"
                        value={newMemberId}
                        onChange={(e) => setNewMemberId(e.target.value)}
                        placeholder="Enter user ID..."
                        disabled={submitting}
                    />
                </div>
                <button type="submit" disabled={!newMemberId.trim() || submitting}>
                    {submitting ? 'Adding...' : 'Add Member'}
                </button>
            </form>

            <div className="members-management">
                <h4>Current Members</h4>
                {currentGroupMembers.length === 0 ? (
                    <p>No members in this group</p>
                ) : (
                    <div className="members-list">
                        {currentGroupMembers.map(member => (
                            <div key={member.id} className="member-row">
                                <span className="member-id">
                                    {member.user_id}
                                    {member.user_id === creatorId && <span className="creator-badge">👑</span>}
                                </span>
                                {member.user_id !== creatorId && (
                                    <button
                                        className="remove-button"
                                        onClick={() => handleRemoveMember(member.id, member.user_id)}
                                        disabled={submitting}
                                    >
                                        Remove
                                    </button>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};
