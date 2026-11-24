import React, { useState } from 'react';
import { api, ApiError } from '../api';
import { useAuth } from '../auth';
import { useTheme } from '../theme';
import type { Goal, Level } from '../types';
import { Body, Btn, Card, Chip, Field, H1, Label, Notice, ProgressBar, Row, Screen } from '../ui';

const GOALS: [Goal, string, string][] = [
  ['lose', 'Lose weight', 'Burn fat, keep muscle, get fitter'],
  ['muscle', 'Build muscle', 'Add size with steady progressive lifting'],
  ['strength', 'Get stronger', 'Heavier dumbbells, fewer reps, longer rests'],
  ['fit', 'Stay fit', 'Balanced training to feel and move well'],
];
const LEVELS: [Level, string, string][] = [
  ['beginner', 'Beginner', 'New to lifting or coming back after a long break'],
  ['intermediate', 'Intermediate', 'Training regularly for 6 months or more'],
  ['advanced', 'Advanced', 'Training consistently for 2 years or more'],
];
const AVOID = ['dairy', 'gluten', 'nuts', 'egg', 'fish', 'meat'];

export default function Onboarding({ onDone }: { onDone: () => void }) {
  const t = useTheme();
  const { me, reload } = useAuth();
  const [step, setStep] = useState(0);
  const [goal, setGoal] = useState<Goal>(me?.goal ?? 'fit');
  const [level, setLevel] = useState<Level>(me?.level ?? 'beginner');
  const [days, setDays] = useState(me?.days_per_week ?? 3);
  const [sex, setSex] = useState<'m' | 'f' | 'x'>(me?.sex ?? 'x');
  const [height, setHeight] = useState(me?.height_cm ? String(me.height_cm) : '');
  const [weight, setWeight] = useState(me?.weight_kg ? String(me.weight_kg) : '');
  const [avoid, setAvoid] = useState<string[]>(me?.restrictions ?? []);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function save() {
    const h = parseFloat(height.replace(',', '.')); const w = parseFloat(weight.replace(',', '.'));
    if (!(h >= 120 && h <= 230)) return setError('Enter your height in centimetres, between 120 and 230.');
    if (!(w >= 30 && w <= 250)) return setError('Enter your weight in kilograms, between 30 and 250.');
    setBusy(true); setError('');
    try {
      await api('/me/profile', { method: 'PUT', body: { goal, level, days_per_week: days, sex, height_cm: h, weight_kg: w, restrictions: avoid } });
      await reload();
      onDone();
    } catch (e) { setError(e instanceof ApiError ? e.message : 'Could not save. Try again.'); }
    finally { setBusy(false); }
  }

  return (
    <Screen>
      <ProgressBar value={(step + 1) / 4} />
      <Label>{`Step ${step + 1} of 4`}</Label>
      {step === 0 ? (<>
        <H1>What is your goal?</H1>
        {GOALS.map(([k, title, d]) => (
          <Card key={k} style={{ borderColor: goal === k ? t.accent : undefined, borderWidth: goal === k ? 2 : 1 }}>
            <Chip title={title} on={goal === k} onPress={() => setGoal(k)} /><Body muted>{d}</Body>
          </Card>))}
      </>) : null}
      {step === 1 ? (<>
        <H1>Your experience</H1>
        {LEVELS.map(([k, title, d]) => (<Card key={k}><Chip title={title} on={level === k} onPress={() => setLevel(k)} /><Body muted>{d}</Body></Card>))}
        <H1>Days a week</H1>
        <Body muted>Pick what you can keep up. Beginners do well with 3.</Body>
        <Row>{[2, 3, 4, 5, 6].map((n) => <Chip key={n} title={String(n)} on={days === n} onPress={() => setDays(n)} />)}</Row>
      </>) : null}
      {step === 2 ? (<>
        <H1>About you</H1>
        <Body muted>Used to estimate your calories, protein and steps. Stored encrypted. Only you can see it.</Body>
        <Label>Sex (for calorie formula)</Label>
        <Row>{([['m', 'Male'], ['f', 'Female'], ['x', 'Prefer not to say']] as const).map(([k, t]) => <Chip key={k} title={t} on={sex === k} onPress={() => setSex(k)} />)}</Row>
        <Field label="Height (cm)" value={height} onChangeText={setHeight} keyboardType="decimal-pad" />
        <Field label="Weight (kg)" value={weight} onChangeText={setWeight} keyboardType="decimal-pad" />
      </>) : null}
      {step === 3 ? (<>
        <H1>Foods to avoid</H1>
        <Body muted>Allergies or choices. We will never put these in your meal plan. Skip if none.</Body>
        <Row>{AVOID.map((a) => <Chip key={a} danger title={a} on={avoid.includes(a)} onPress={() => setAvoid(avoid.includes(a) ? avoid.filter((x) => x !== a) : [...avoid, a])} />)}</Row>
        <Notice kind="info">Setwise gives general fitness guidance, not medical advice. If you have a health condition, are pregnant or take medication, check with your doctor before starting.</Notice>
      </>) : null}
      {error ? <Notice kind="error">{error}</Notice> : null}
      <Row>
        {step > 0 ? <Btn title="Back" onPress={() => setStep(step - 1)} /> : null}
        <Btn kind="primary" title={step === 3 ? 'Build my plan' : 'Next'} busy={busy} onPress={() => (step === 3 ? save() : setStep(step + 1))} />
      </Row>
    </Screen>
  );
}
