import React, { useCallback, useEffect, useState } from 'react';
import { View } from 'react-native';
import { api, ApiError } from '../api';
import { useAuth } from '../auth';
import type { CardioSummary, PlanOut } from '../types';
import { Body, Btn, Card, H1, H2, Label, Notice, Num, Row, Screen } from '../ui';
import Gym from './Gym';

const DAY_IDX = () => (new Date().getDay() + 6) % 7; // Monday = 0

export default function Today({ setImmersive }: { setImmersive: (v: boolean) => void }) {
  const { me } = useAuth();
  const [plan, setPlan] = useState<PlanOut | null>(null);
  const [summary, setSummary] = useState<CardioSummary | null>(null);
  const [error, setError] = useState('');
  const [gymDay, setGymDay] = useState<number | null>(null);
  const [openDay, setOpenDay] = useState<number | null>(null);

  const load = useCallback(async () => {
    setError('');
    try {
      setPlan(await api<PlanOut>('/plan'));
      setSummary(await api<CardioSummary>(`/cardio/summary?tz_offset_minutes=${-new Date().getTimezoneOffset()}`));
    } catch (e) { setError(e instanceof ApiError ? e.message : 'Could not load your plan.'); }
  }, []);
  useEffect(() => { load(); }, [load]);

  if (gymDay !== null && plan && me) {
    return <Gym plan={plan} goal={me.goal} day={plan.plan[gymDay]} onExit={() => { setGymDay(null); setImmersive(false); load(); }} />;
  }
  const idx = DAY_IDX();
  const today = plan?.plan[idx];
  const next = plan ? plan.plan.map((d, k) => ({ d, k })).filter(({ d, k }) => d.type === 'lift' && k !== idx)[0] : undefined;
  const start = (k: number) => { setGymDay(k); setImmersive(true); };

  return (
    <Screen>
      <Label>{new Date().toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'short' })}</Label>
      {error ? <Notice kind="error">{error}</Notice> : null}
      {!plan && !error ? <Body muted>Loading your plan…</Body> : null}
      {today ? (<>
        <H1>{today.name}</H1>
        {today.type === 'lift' ? (<>
          <Body muted>{`${today.exercises?.length ?? 0} exercises`}</Body>
          <Btn kind="primary" big title="I am at the gym" onPress={() => start(idx)} />
          <Card>
            {today.exercises?.map((e) => (
              <Row key={e.id} style={{ justifyContent: 'space-between', flexWrap: 'nowrap' }}>
                <View style={{ flex: 1 }}><Body>{plan!.exercises[e.id].name}</Body><Body muted>{plan!.exercises[e.id].muscles}</Body></View>
                <Body muted>{`${e.sets} × ${e.reps_lo}–${e.reps_hi}`}</Body>
              </Row>))}
          </Card>
        </>) : (<>
          <Card><Body>{today.note}</Body></Card>
          {next ? <Btn title={`Train anyway: ${next.d.name}`} onPress={() => start(next.k)} /> : null}
        </>)}
      </>) : null}

      {plan ? (<>
        <Row>
          <Card style={{ flexGrow: 1, flexBasis: '45%' }}><Num>{plan.targets.kcal}</Num><Label>kcal target</Label></Card>
          <Card style={{ flexGrow: 1, flexBasis: '45%' }}><Num>{plan.targets.protein} g</Num><Label>protein target</Label></Card>
          <Card style={{ flexGrow: 1, flexBasis: '45%' }}><Num>{summary?.today.steps.toLocaleString() ?? '–'}</Num><Label>steps logged today</Label></Card>
          <Card style={{ flexGrow: 1, flexBasis: '45%' }}><Num>{summary?.today.kcal ?? '–'}</Num><Label>cardio kcal today</Label></Card>
        </Row>
        <Notice kind="info">{plan.adherence.message}</Notice>
        <H2>Your week</H2>
        {plan.plan.map((d, k) => (
          <Card key={d.day}>
            <Row style={{ justifyContent: 'space-between' }}>
              <Body>{`${d.day} · ${d.name}${k === idx ? ' (today)' : ''}`}</Body>
              {d.type === 'lift' ? <Btn small kind="ghost" title={openDay === k ? 'Hide' : 'Show'} onPress={() => setOpenDay(openDay === k ? null : k)} /> : null}
            </Row>
            {d.type !== 'lift' ? <Body muted>{d.note}</Body> : null}
            {d.type === 'lift' && openDay === k ? d.exercises?.map((e) => (
              <Row key={e.id} style={{ justifyContent: 'space-between', flexWrap: 'nowrap' }}>
                <Body style={{ flex: 1 }}>{plan.exercises[e.id].name}</Body>
                <Body muted>{`${e.sets} × ${e.reps_lo}–${e.reps_hi}${plan.exercises[e.id].bw ? '' : ` · ${e.start_weight} kg`}`}</Body>
              </Row>)) : null}
          </Card>))}
      </>) : null}
    </Screen>
  );
}
