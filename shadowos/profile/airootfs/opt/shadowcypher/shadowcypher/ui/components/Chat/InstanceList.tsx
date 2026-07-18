import React, { useEffect } from 'react';
import { useInstanceDiscovery } from '../../hooks/useInstanceDiscovery';
import './InstanceList.css';

export const InstanceList = ({ token }: { token?: string | null }) => {
  const { instances, loading, error, listInstances } = useInstanceDiscovery(token);

  useEffect(() => {
    listInstances();
    const interval = setInterval(listInstances, 30000);
    return () => clearInterval(interval);
  }, [listInstances]);

  if (loading) return <div>Loading instances...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div className="instance-list">
      <h3>Shadow Instances</h3>
      {instances.length === 0 ? (
        <p>No instances found</p>
      ) : (
        <ul>
          {instances.map((inst) => (
            <li key={inst.instance_id} className={inst.is_online ? 'online' : 'offline'}>
              <span className="status-indicator">{inst.is_online ? '🟢' : '🔴'}</span>
              <span className="instance-id">{inst.instance_id.slice(0, 8)}...</span>
              <span className="endpoint">{inst.endpoint || 'relay-only'}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
