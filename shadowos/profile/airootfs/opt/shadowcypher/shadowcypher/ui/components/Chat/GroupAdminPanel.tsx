import React, { useState } from 'react';
import { useGroupChat } from '../../hooks/useGroupChat';

interface GroupAdminPanelProps {
    groupId: string;
    creatorId: string;
    creatorUserId?: string;
    currentUser: { username: string; id?: string };
    token: string | null;
}

export const GroupAdminPanel: React.FC<GroupAdminPanelProps> = ({
    groupId, creatorId, creatorUserId, currentUser, token
}) => {
    const [inviteEmail, setInviteEmail] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const { addMember, error } = useGroupChat(token);

    const isOwner = creatorUserId
        ? currentUser.id === creatorUserId
        : currentUser.username === creatorId;

    const handleInvite = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!inviteEmail.trim()) return;
        setSubmitting(true);
        try {
            await addMember(groupId, inviteEmail.trim());
            setInviteEmail('');
        } finally {
            setSubmitting(false);
        }
    };

    if (!isOwner) {
        return <div className="admin-panel"><p className="not-creator">Only the group owner can manage members</p></div>;
    }

    return (
        <div className="admin-panel">
            <h3>Admin Panel</h3>
            {error && <div className="error-message">{error}</div>}
            <form onSubmit={handleInvite} className="add-member-form">
                <div className="form-group">
                    <label htmlFor="invite-email">Invite by email</label>
                    <input
                        id="invite-email"
                        type="email"
                        value={inviteEmail}
                        onChange={e => setInviteEmail(e.target.value)}
                        placeholder="user@example.com"
                        disabled={submitting}
                    />
                </div>
                <button type="submit" disabled={!inviteEmail.trim() || submitting}>
                    {submitting ? 'Inviting...' : 'Send Invite'}
                </button>
            </form>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: 12 }}>
                Invited users accept via the Teams tab. Member listing requires the Operator plan.
            </p>
        </div>
    );
};
