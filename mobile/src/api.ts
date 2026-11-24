import * as SecureStore from 'expo-secure-store';
import { API_URL } from './config';
import type { TokenOut } from './types';

const ACCESS = 'sw.access';
const REFRESH = 'sw.refresh';
// Tokens stay on this device only and are excluded from backups.
const OPTS: SecureStore.SecureStoreOptions = { keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY };

let access: string | null = null;
let refreshing: Promise<boolean> | null = null;
let onSignedOut: () => void = () => {};

export function setSignedOutHandler(fn: () => void) { onSignedOut = fn; }

export class ApiError extends Error {
  status: number;
  code?: string;
  purpose?: string;
  constructor(status: number, message: string, code?: string, purpose?: string) {
    super(message);
    this.status = status; this.code = code; this.purpose = purpose;
  }
}

export async function loadTokens(): Promise<boolean> {
  access = await SecureStore.getItemAsync(ACCESS, OPTS);
  const r = await SecureStore.getItemAsync(REFRESH, OPTS);
  return !!(access || r);
}

export async function saveTokens(t: TokenOut) {
  access = t.access_token;
  await SecureStore.setItemAsync(ACCESS, t.access_token, OPTS);
  await SecureStore.setItemAsync(REFRESH, t.refresh_token, OPTS);
}

export async function clearTokens() {
  access = null;
  await SecureStore.deleteItemAsync(ACCESS, OPTS);
  await SecureStore.deleteItemAsync(REFRESH, OPTS);
}

export async function getRefreshToken() { return SecureStore.getItemAsync(REFRESH, OPTS); }

function messageFrom(detail: unknown, fallback: string): { message: string; code?: string; purpose?: string } {
  if (typeof detail === 'string') return { message: detail };
  if (Array.isArray(detail)) {
    const first = detail[0] as { msg?: string; loc?: (string | number)[] } | undefined;
    const field = first?.loc?.[first.loc.length - 1];
    return { message: first?.msg ? `${field ? String(field).replace(/_/g, ' ') + ': ' : ''}${first.msg}` : fallback };
  }
  if (detail && typeof detail === 'object') {
    const d = detail as { code?: string; purpose?: string };
    return { message: d.code === 'consent_required' ? 'You have switched off a permission this feature needs.' : fallback, code: d.code, purpose: d.purpose };
  }
  return { message: fallback };
}

async function send(path: string, method: string, body: unknown, token: string | null): Promise<Response> {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), 20000);
  try {
    return await fetch(API_URL + path, {
      method,
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: ctl.signal,
    });
  } catch {
    throw new ApiError(0, 'Cannot reach Setwise. Check your connection and try again.');
  } finally {
    clearTimeout(timer);
  }
}

async function refreshOnce(): Promise<boolean> {
  if (!refreshing) {
    refreshing = (async () => {
      const rt = await getRefreshToken();
      if (!rt) return false;
      try {
        const r = await send('/auth/refresh', 'POST', { refresh_token: rt }, null);
        if (!r.ok) { await clearTokens(); return false; }
        await saveTokens((await r.json()) as TokenOut);
        return true;
      } catch { return false; }
    })().finally(() => { refreshing = null; });
  }
  return refreshing;
}

export async function api<T>(path: string, opts: { method?: string; body?: unknown; auth?: boolean } = {}): Promise<T> {
  const { method = 'GET', body, auth = true } = opts;
  let res = await send(path, method, body, auth ? access : null);
  if (res.status === 401 && auth) {
    if (await refreshOnce()) res = await send(path, method, body, access);
    else { onSignedOut(); throw new ApiError(401, 'Please sign in again.'); }
  }
  if (res.status === 204) return undefined as T;
  let data: unknown = null;
  try { data = await res.json(); } catch { /* empty body */ }
  if (!res.ok) {
    const detail = (data as { detail?: unknown } | null)?.detail;
    const m = messageFrom(detail, `Something went wrong (${res.status}).`);
    throw new ApiError(res.status, m.message, m.code, m.purpose);
  }
  return data as T;
}
