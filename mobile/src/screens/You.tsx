import React, { useCallback, useEffect, useState } from 'react';
import { Share, Switch, View } from 'react-native';
import { api, ApiError, clearTokens, saveTokens } from '../api';
import { useAuth } from '../auth';
import { useTheme } from '../theme';
import type { Purpose } from '../types';
import { Body, Btn, Card, Field, H1, H2, Label, Notice, Num, Row, Screen } from '../ui';

interface W { day: string; kg: number }

export default function You({ onEditProfile, paused }: { onEditProfile: () => void; paused?: boolean }) {
  const t = useTheme();
  const { me, reload, logout } = useAuth();
  const [weights, setWeights] = useState<W[]>([]);
  const [kg, setKg] = useState('');
  const [msg, setMsg] = useState<{ kind: 'good' | 'error' | 'info'; text: string } | null>(null);
  const [cur, setCur] = useState(''); const [next, setNext] = useState('');
  const [delPw, setDelPw] = useState(''); const [delOpen, setDelOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const loadW = useCallback(async () => { try { setWeights(await api<W[]>('/me/weights')); } catch { setWeights([]); } }, []);
  useEffect(() => { loadW(); }, [loadW]);

  const fail = (e: unknown) => setMsg({ kind: 'error', text: e instanceof ApiError ? e.message : 'Something went wrong. Try again.' });

  async function logWeight() {
    const v = parseFloat(kg.replace(',', '.'));
    if (!(v >= 30 && v <= 250)) return setMsg({ kind: 'error', text: 'Enter your weight in kilograms, between 30 and 250.' });
    try { await api('/me/weight', { method: 'POST', body: { kg: v } }); setKg(''); await loadW(); await reload(); setMsg({ kind: 'good', text: 'Weight saved. Your calorie target uses it.' }); } catch (e) { fail(e); }
  }
  async function setConsent(purpose: Purpose, granted: boolean) {
    try { await api('/me/consents', { method: 'POST', body: { purpose, granted } }); await reload();
      setMsg({ kind: 'info', text: granted ? 'Permission switched on.' : purpose === 'ai_coach' ? 'AI coach switched off and your coach chat was deleted.' : 'Permission withdrawn. Features that need your health data are paused. You can delete your data below.' }); } catch (e) { fail(e); }
  }
  async function exportData() {
    setBusy(true);
    try {
      const data = await api<unknown>('/me/export');
      await Share.share({ title: 'My Setwise data', message: JSON.stringify(data, null, 2) });
    } catch (e) { fail(e); } finally { setBusy(false); }
  }
  async function changePw() {
    if (next.length < 10) return setMsg({ kind: 'error', text: 'Use a new password of at least 10 characters.' });
    try {
      const tokens = await api<{ access_token: string; refresh_token: string; expires_in: number }>('/auth/change-password', { method: 'POST', body: { current_password: cur, new_password: next } });
      await saveTokens(tokens); setCur(''); setNext('');
      setMsg({ kind: 'good', text: 'Password changed. Other devices were signed out.' });
    } catch (e) { fail(e); }
  }
  async function deleteAccount() {
    setBusy(true);
    try { await api('/me/delete', { method: 'POST', body: { password: delPw } }); await clearTokens(); await logout(); } catch (e) { fail(e); } finally { setBusy(false); }
  }
  async function logoutAll() { try { await api('/auth/logout-all', { method: 'POST' }); await logout(); } catch (e) { fail(e); } }

  const c = me?.consents ?? {};
  return (
    <Screen>
      <Label>You</Label><H1>{me?.email ?? ''}</H1>
      {paused ? <Notice kind="warn">Health features are paused because you withdrew consent. Switch it back on below to continue, or export or delete your data.</Notice> : null}
      {msg ? <Notice kind={msg.kind}>{msg.text}</Notice> : null}

      {!paused ? <Card>
        <H2>Body weight</H2>
        <Row style={{ gap: 24 }}>
          <View><Num>{me?.weight_kg ?? '–'}</Num><Label>kg now</Label></View>
          {weights.length > 1 ? <View><Num>{(weights[weights.length - 1].kg - weights[0].kg).toFixed(1)}</Num><Label>kg change</Label></View> : null}
        </Row>
        {weights.slice(-5).reverse().map((w) => <Body key={w.day} muted>{`${w.day} · ${w.kg} kg`}</Body>)}
        <Field label="Today (kg)" value={kg} onChangeText={setKg} keyboardType="decimal-pad" />
        <Btn title="Save weight" onPress={logWeight} />
        <Btn kind="ghost" small title="Change goal or schedule" onPress={onEditProfile} />
      </Card> : null}

      <Card>
        <H2>Your permissions</H2>
        <Row style={{ justifyContent: 'space-between', flexWrap: 'nowrap' }}>
          <View style={{ flex: 1 }}><Body>Health information</Body><Body muted>Needed for your plan, tracking and meals. Switching it off pauses these features.</Body></View>
          <Switch accessibilityLabel="Health information consent" value={!!c.health_data} onValueChange={(v) => setConsent('health_data', v)} trackColor={{ true: t.accent, false: t.line }} />
        </Row>
        <Row style={{ justifyContent: 'space-between', flexWrap: 'nowrap' }}>
          <View style={{ flex: 1 }}><Body>AI coach</Body><Body muted>Sends a short summary without your name, email or birth date to an AI provider. Off by default.</Body></View>
          <Switch accessibilityLabel="AI coach consent" value={!!c.ai_coach} onValueChange={(v) => setConsent('ai_coach', v)} trackColor={{ true: t.accent, false: t.line }} />
        </Row>
      </Card>

      <Card>
        <H2>Your data</H2>
        <Body muted>Get a copy of everything Setwise holds about you, or erase it. The export contains sensitive health information, so only share it somewhere you trust.</Body>
        <Btn title="Export my data" onPress={exportData} busy={busy} />
        {!delOpen ? <Btn kind="danger" title="Delete my account" onPress={() => setDelOpen(true)} /> : (
          <>
            <Notice kind="warn">This permanently deletes your account, plan, workouts, steps, meals and chats. It cannot be undone.</Notice>
            <Field label="Enter your password to confirm" value={delPw} onChangeText={setDelPw} secureTextEntry />
            <Row><Btn small title="Cancel" onPress={() => { setDelOpen(false); setDelPw(''); }} /><Btn small kind="danger" title="Delete everything" onPress={deleteAccount} disabled={!delPw} busy={busy} /></Row>
          </>)}
      </Card>

      <Card>
        <H2>Security</H2>
        <Field label="Current password" value={cur} onChangeText={setCur} secureTextEntry autoComplete="current-password" />
        <Field label="New password (10+ characters)" value={next} onChangeText={setNext} secureTextEntry autoComplete="new-password" />
        <Btn title="Change password" onPress={changePw} disabled={!cur || !next} />
        <Btn kind="ghost" title="Sign out on all devices" onPress={logoutAll} />
        <Btn kind="ghost" title="Sign out" onPress={() => logout()} />
      </Card>

      <Card>
        <H2>About your privacy</H2>
        <Body muted>{`Questions, corrections or complaints: ${me?.information_officer ?? ''}. You can also contact the Information Regulator at inforeg.org.za. Privacy notice version ${me?.policy_version ?? ''}.`}</Body>
      </Card>
    </Screen>
  );
}
