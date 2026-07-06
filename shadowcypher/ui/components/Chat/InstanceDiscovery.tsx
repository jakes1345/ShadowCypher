import React, { useState } from 'react';
import { useInstanceDiscovery } from '../../hooks/useInstanceDiscovery';
import './InstanceDiscovery.css';

interface InstanceDiscoveryProps {
  onInstanceAdded: () => void;
}

export const InstanceDiscovery = ({ onInstanceAdded }: InstanceDiscoveryProps) => {
  const { registerInstance, error, loading } = useInstanceDiscovery();
  const [showManualEntry, setShowManualEntry] = useState(false);
  const [instanceId, setInstanceId] = useState('');
  const [pubkey, setPubkey] = useState('');
  const [endpoint, setEndpoint] = useState('');

  const handleAddInstance = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    try {
      await registerInstance(instanceId, pubkey, endpoint);
      setInstanceId('');
      setPubkey('');
      setEndpoint('');
      onInstanceAdded();
    } catch (err) {
      console.error('Failed to add instance:', err);
    }
  };

  return (
    <div className="instance-discovery">
      <h3>🔗 Add Shadow Instance</h3>
      {error && <div className="error-banner">{error}</div>}
      <div className="discovery-methods">
        <button onClick={() => setShowManualEntry(!showManualEntry)}>📱 Manual Entry</button>
        <button disabled>🔗 Share Link (coming soon)</button>
      </div>
      {showManualEntry && (
        <form onSubmit={handleAddInstance} className="manual-entry-form">
          <input type="text" placeholder="Instance ID" value={instanceId} onChange={(e) => setInstanceId(e.target.value)} required />
          <input type="text" placeholder="Public Key (hex)" value={pubkey} onChange={(e) => setPubkey(e.target.value)} required />
          <input type="text" placeholder="Endpoint (IP:port or onion)" value={endpoint} onChange={(e) => setEndpoint(e.target.value)} />
          <button type="submit" disabled={loading}>{loading ? 'Adding...' : 'Add Instance'}</button>
        </form>
      )}
    </div>
  );
};
