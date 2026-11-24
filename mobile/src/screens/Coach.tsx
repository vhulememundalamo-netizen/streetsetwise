import React, { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from '../api';
import { useAuth } from '../auth';
import type { ChatMsg, CoachReply } from '../types';
import { Body, Btn, Card, Field, H1, Label, Notice, Row, Screen } from '../ui';
import { useTheme } from '../theme';
import { View } from 'react-native';

const IDEAS = ['How heavy should I go?', 'What should I eat today?', 'I missed some workouts', 'How are my steps?'];

export default function Coach() {
  const t = useTheme();
  const { me } = useAuth();
  const [msgs, setMsgs] = useState<ChatMsg[]>([]);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [hint, setHint] = useState<string | null>(null);

  const load = useCallback(async () => {
    try { setMsgs(await api<ChatMsg[]>('/coach/history')); } catch { /* empty history is fine */ }
  }, []);
  useEffect(() => { load(); }, [load]);

  async function send(m: string) {
    const message = m.trim();
    if (!message || busy) return;
    setBusy(true); setError(''); setText('');
    setMsgs((x) => [...x, { role: 'user', content: message }]);
    try {
      const r = await api<CoachReply>('/coach', { method: 'POST', body: { message } });
      setMsgs((x) => [...x, { role: 'assistant', content: r.reply, source: r.source }]);
      setHint(r.hint);
    } catch (e) { setError(e instanceof ApiError ? e.message : 'The coach could not answer. Try again.'); }
    finally { setBusy(false); }
  }

  return (
    <Screen>
      <Label>Coach</Label><H1>Ask your coach</H1>
      <Body muted>{me?.consents.ai_coach
        ? 'AI coach is on. A short summary without your name, email or birth date is sent to our AI provider to answer. Switch it off in You.'
        : 'Answers come from your own data on our server. Turn on the AI coach in You for open-ended questions.'}</Body>
      {msgs.length === 0 ? <Row>{IDEAS.map((i) => <Btn key={i} small title={i} onPress={() => send(i)} />)}</Row> : null}
      {msgs.map((m, k) => (
        <View key={k} style={{ alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start', maxWidth: '88%' }}>
          <Card style={{ backgroundColor: m.role === 'user' ? t.accentSoft : t.surface }}>
            <Body>{m.content}</Body>
            {m.source === 'safety' ? <Label>Safety message</Label> : m.source === 'ai' ? <Label>AI coach</Label> : null}
          </Card>
        </View>))}
      {busy ? <Body muted>Thinking…</Body> : null}
      {hint ? <Notice kind="info">{hint}</Notice> : null}
      {error ? <Notice kind="error">{error}</Notice> : null}
      <Field label="Your message" value={text} onChangeText={setText} multiline maxLength={800} returnKeyType="send" blurOnSubmit onSubmitEditing={() => send(text)} />
      <Btn kind="primary" title="Send" onPress={() => send(text)} disabled={!text.trim()} busy={busy} />
      <Notice kind="warn">The coach gives general fitness guidance, not medical advice. For pain, injury, illness or a medical condition, see a doctor.</Notice>
    </Screen>
  );
}
