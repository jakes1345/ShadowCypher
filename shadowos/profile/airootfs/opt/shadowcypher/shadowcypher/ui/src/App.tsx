import React, { useEffect, useState, useCallback } from 'react';
import { createClient, type SupabaseClient, type User } from '@supabase/supabase-js';
import Chat from '../components/Chat/index';

const SUPABASE_URL = 'https://umruqwvyipylfslwwozj.supabase.co';
const SUPABASE_ANON_KEY =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVtcnVxd3Z5aXB5bGZzbHd3b3pqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzcyNDY1NzYsImV4cCI6MjA5MjgyMjU3Nn0.KSjgi54wIOZ_6LSp6Bs_plmtyeOKpul8FXwQhHqwtm4';

const supabase: SupabaseClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

const KEY_PATTERN = /^sc_live_[a-f0-9]{48}$/;

function generateApiKey(): string {
  const bytes = new Uint8Array(24);
  crypto.getRandomValues(bytes);
  return 'sc_live_' + Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
}

async function ensureApiKey(user: User): Promise<string | null> {
  const existing = (user.user_metadata as { api_key?: string })?.api_key;
  if (existing && KEY_PATTERN.test(existing)) return existing;

  const key = generateApiKey();
  const { error } = await supabase.auth.updateUser({
    data: { ...user.user_metadata, api_key: key, api_key_created_at: new Date().toISOString() },
  });
  return error ? null : key;
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [handle, setHandle] = useState('');
  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [submitting, setSubmitting] = useState(false);

  const bootstrap = useCallback(async (u: User) => {
    const key = await ensureApiKey(u);
    setUser(u);
    setApiKey(key);
    setLoading(false);
  }, []);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) { bootstrap(session.user); }
      else { setLoading(false); }
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) { bootstrap(session.user); }
      else { setUser(null); setApiKey(null); }
    });

    return () => subscription.unsubscribe();
  }, [bootstrap]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setAuthError('');
    try {
      if (mode === 'login') {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
      } else {
        const h = handle.trim() || email.split('@')[0];
        const key = generateApiKey();
        const { error } = await supabase.auth.signUp({
          email,
          password,
          options: { data: { handle: h, api_key: key, api_key_created_at: new Date().toISOString() } },
        });
        if (error) throw error;
      }
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : 'Auth failed');
    } finally {
      setSubmitting(false);
    }
  };

  const signOut = () => supabase.auth.signOut();

  if (loading) {
    return (
      <div style={styles.center}>
        <div style={styles.spinner} />
      </div>
    );
  }

  if (!user || !apiKey) {
    return (
      <div style={styles.center}>
        <div style={styles.card}>
          <div style={styles.logo}>SHADOWCYPHER</div>
          <div style={styles.tabs}>
            <button style={{ ...styles.tab, ...(mode === 'login' ? styles.tabActive : {}) }} onClick={() => setMode('login')}>Sign In</button>
            <button style={{ ...styles.tab, ...(mode === 'signup' ? styles.tabActive : {}) }} onClick={() => setMode('signup')}>Register</button>
          </div>
          <form onSubmit={handleSubmit} style={styles.form}>
            {mode === 'signup' && (
              <input
                style={styles.input}
                type="text"
                placeholder="Handle (e.g. shadow_jack)"
                value={handle}
                onChange={e => setHandle(e.target.value)}
              />
            )}
            <input
              style={styles.input}
              type="email"
              placeholder="Email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
            />
            <input
              style={styles.input}
              type="password"
              placeholder="Password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
            />
            {authError && <div style={styles.error}>{authError}</div>}
            <button style={styles.btn} type="submit" disabled={submitting}>
              {submitting ? '...' : mode === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  const nick = (user.user_metadata as { handle?: string })?.handle ?? user.email?.split('@')[0] ?? 'user';

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <div style={styles.topbar}>
        <span style={{ color: '#00f2ff', fontWeight: 700 }}>SHADOWCYPHER</span>
        <span style={{ color: '#8899aa', fontSize: '0.8rem' }}>@{nick}</span>
        <button style={styles.signOutBtn} onClick={signOut}>Sign out</button>
      </div>
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <Chat token={apiKey} currentUser={{ username: nick, id: user.id }} />
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  center: { display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', background: '#020202' },
  spinner: { width: 32, height: 32, border: '3px solid #1e2a45', borderTop: '3px solid #00f2ff', borderRadius: '50%', animation: 'spin 0.8s linear infinite' },
  card: { background: '#0d1117', border: '1px solid #1e2a45', borderRadius: 8, padding: 32, width: 360, display: 'flex', flexDirection: 'column', gap: 16 },
  logo: { color: '#00f2ff', fontWeight: 800, fontSize: '1.2rem', letterSpacing: '0.1em', textAlign: 'center' },
  tabs: { display: 'flex', gap: 0, borderBottom: '1px solid #1e2a45' },
  tab: { flex: 1, padding: '8px 0', background: 'none', border: 'none', color: '#8899aa', cursor: 'pointer', fontSize: '0.9rem' },
  tabActive: { color: '#00f2ff', borderBottom: '2px solid #00f2ff' },
  form: { display: 'flex', flexDirection: 'column', gap: 10 },
  input: { padding: '10px 12px', background: '#0a0f1a', border: '1px solid #1e2a45', borderRadius: 4, color: '#e2e8f0', fontSize: '0.9rem', outline: 'none' },
  error: { color: '#ff3b3b', fontSize: '0.8rem', padding: '6px 0' },
  btn: { padding: '10px', background: '#00f2ff', color: '#020202', border: 'none', borderRadius: 4, fontWeight: 700, cursor: 'pointer', fontSize: '0.95rem' },
  topbar: { display: 'flex', alignItems: 'center', gap: 12, padding: '8px 16px', background: '#0d1117', borderBottom: '1px solid #1e2a45' },
  signOutBtn: { marginLeft: 'auto', background: 'none', border: '1px solid #1e2a45', color: '#8899aa', padding: '4px 10px', borderRadius: 4, cursor: 'pointer', fontSize: '0.8rem' },
};
