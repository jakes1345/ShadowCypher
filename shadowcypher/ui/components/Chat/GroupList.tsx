import React, { useEffect } from 'react';
import { useGroupChat, Group } from '../../hooks/useGroupChat';

interface GroupListProps {
    onSelectGroup: (groupId: string) => void;
    selectedGroupId?: string;
    token: string | null;
}

export const GroupList: React.FC<GroupListProps> = ({ onSelectGroup, selectedGroupId, token }) => {
    const { groups, loading, error, fetchGroups } = useGroupChat(token);

    useEffect(() => {
        fetchGroups();
    }, [fetchGroups]);

    if (loading) {
        return (
            <div className="group-list-container">
                <h3>🔐 Groups</h3>
                <div className="loading-indicator">Loading groups...</div>
            </div>
        );
    }

    return (
        <div className="group-list-container">
            <h3>🔐 Groups</h3>
            {error && <div className="error-message">{error}</div>}
            {groups.length === 0 ? (
                <div className="no-groups">No groups yet</div>
            ) : (
                <div className="group-list">
                    {groups.map(group => (
                        <div
                            key={group.id}
                            className={`group-item ${selectedGroupId === group.id ? 'active' : ''}`}
                            onClick={() => onSelectGroup(group.id)}
                        >
                            <div className="group-name">{group.name}</div>
                            <div className="group-creator">Created by {group.creator_id}</div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};
