import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, clearTokens, getRefreshToken, loadTokens, saveTokens, setSignedOutHandler } from './api';
import type { Me, TokenOut } from './types';

type Status = 'loading' | 'out' | 'in';
interface Ctx {
  status: Status; me: Me | null;
  signup: (v: { email: string; password: string; dob: string; ai: boolean }) => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  reload: () => Promise<Me | null>;
}
const AuthCtx = createContext<Ctx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<Status>('loading');
  const [me, setMe] = useState<Me | null>(null);

  const reload = useCallback(async () => {
    const m = await api<Me>('/me');
    setMe(m);
    return m;
  }, []);

  const finish = useCallback(async (t: TokenOut) => {
    await saveTokens(t);
    await reload();
    setStatus('in');
  }, [reload]);

  useEffect(() => {
    setSignedOutHandler(() => { setMe(null); setStatus('out'); });
    (async () => {
      try {
        if (await loadTokens()) { await reload(); setStatus('in'); } else setStatus('out');
      } catch { await clearTokens(); setStatus('out'); }
    })();
  }, [reload]);

  const value = useMemo<Ctx>(() => ({
    status, me, reload,
    signup: async ({ email, password, dob, ai }) => {
      const t = await api<TokenOut>('/auth/signup', { method: 'POST', auth: false, body: {
        email: email.trim(), password, date_of_birth: dob, accept_terms_privacy: true, consent_health_data: true, consent_ai_coach: ai } });
      await finish(t);
    },
    login: async (email, password) => {
      const t = await api<TokenOut>('/auth/login', { method: 'POST', auth: false, body: { email: email.trim(), password } });
      await finish(t);
    },
    logout: async () => {
      const rt = await getRefreshToken();
      try { if (rt) await api('/auth/logout', { method: 'POST', auth: false, body: { refresh_token: rt } }); } catch { /* offline: still clear locally */ }
      await clearTokens(); setMe(null); setStatus('out');
    },
  }), [status, me, reload, finish]);

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): Ctx {
  const c = useContext(AuthCtx);
  if (!c) throw new Error('AuthProvider missing');
  return c;
}
