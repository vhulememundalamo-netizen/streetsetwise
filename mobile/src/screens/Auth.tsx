import React, { useState } from 'react';
import { View } from 'react-native';
import { useAuth } from '../auth';
import { ApiError } from '../api';
import { Body, Btn, Card, Checkbox, Field, H1, Label, Notice, Row, Screen } from '../ui';

function adult(dob: string): string | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dob)) return 'Enter your date of birth as YYYY-MM-DD, for example 1998-04-12.';
  const d = new Date(dob + 'T00:00:00');
  if (Number.isNaN(d.getTime()) || d > new Date()) return 'That date of birth does not look right.';
  const now = new Date();
  let age = now.getFullYear() - d.getFullYear();
  if (now.getMonth() < d.getMonth() || (now.getMonth() === d.getMonth() && now.getDate() < d.getDate())) age--;
  return age >= 18 ? null : 'Setwise is for people aged 18 or older.';
}

export default function Auth() {
  const { login, signup } = useAuth();
  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [dob, setDob] = useState('');
  const [terms, setTerms] = useState(false);
  const [health, setHealth] = useState(false);
  const [ai, setAi] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [more, setMore] = useState(false);

  async function submit() {
    setError('');
    if (mode === 'signup') {
      const bad = adult(dob);
      if (bad) return setError(bad);
      if (password.length < 10) return setError('Use a password of at least 10 characters.');
      if (!terms || !health) return setError('Please accept the two required items to create your account.');
    }
    setBusy(true);
    try {
      if (mode === 'login') await login(email, password);
      else await signup({ email, password, dob, ai });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Something went wrong. Try again.');
    } finally { setBusy(false); }
  }

  return (
    <Screen>
      <View style={{ gap: 6, marginTop: 24 }}>
        <Label>Setwise</Label>
        <H1>{mode === 'login' ? 'Welcome back' : 'Create your account'}</H1>
      </View>
      <Field label="Email" value={email} onChangeText={setEmail} autoCapitalize="none" autoComplete="email" keyboardType="email-address" textContentType="emailAddress" />
      <Field label={mode === 'signup' ? 'Password (10+ characters)' : 'Password'} value={password} onChangeText={setPassword} secureTextEntry
        autoComplete={mode === 'signup' ? 'new-password' : 'current-password'} textContentType={mode === 'signup' ? 'newPassword' : 'password'} />
      {mode === 'signup' ? (
        <>
          <Field label="Date of birth (YYYY-MM-DD)" value={dob} onChangeText={setDob} keyboardType="numbers-and-punctuation" maxLength={10} placeholder="1998-04-12" />
          <Card>
            <Label>Your privacy (POPIA)</Label>
            <Body muted>
              We only collect what the app needs: your email, date of birth, body measurements, workouts, steps and food choices. Your health details are encrypted. GPS routes stay on your phone. You can export or delete everything at any time in the You tab.
            </Body>
            {more ? (
              <Body muted>
                Who is responsible: the Setwise operator. We use your data only to build your plan, track progress and coach you. We do not sell it or use it for advertising. The AI coach is optional and, if you switch it on, sends a short summary without your name, email or birth date to our AI provider, which may process it outside South Africa. You can complain to the Information Regulator at inforeg.org.za.
              </Body>
            ) : null}
            <Btn small kind="ghost" title={more ? 'Show less' : 'Read more'} onPress={() => setMore(!more)} />
            <Checkbox checked={terms} onChange={setTerms}>I am 18 or older and accept the terms and privacy notice. (Required)</Checkbox>
            <Checkbox checked={health} onChange={setHealth}>I consent to Setwise processing my health information (weight, height, workouts, steps, food and restrictions) to run the app. I can withdraw this at any time. (Required)</Checkbox>
            <Checkbox checked={ai} onChange={setAi}>I want the optional AI coach, which may send a short anonymised summary to an AI provider. (Optional)</Checkbox>
          </Card>
        </>
      ) : null}
      {error ? <Notice kind="error">{error}</Notice> : null}
      <Btn kind="primary" big title={mode === 'login' ? 'Sign in' : 'Create account'} onPress={submit} busy={busy} />
      <Row style={{ justifyContent: 'center' }}>
        <Btn kind="ghost" small title={mode === 'login' ? 'New here? Create an account' : 'I already have an account'} onPress={() => { setMode(mode === 'login' ? 'signup' : 'login'); setError(''); }} />
      </Row>
    </Screen>
  );
}
