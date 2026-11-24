import { activateKeepAwakeAsync, deactivateKeepAwake } from 'expo-keep-awake';
import * as Haptics from 'expo-haptics';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Pressable, Text, Vibration, View } from 'react-native';
import { api, ApiError } from '../api';
import { adviseSet, down, fmtClock, snap, up, volume, type SetAdvice } from '../lib/gym';
import { useTheme } from '../theme';
import type { Effort, Goal, PlanDay, PlanOut, SetLog } from '../types';
import { Body, Btn, Card, H1, H2, Label, Notice, Num, ProgressBar, Row, Screen } from '../ui';

type Stage = 'pick' | 'set' | 'log' | 'rest' | 'summary';
const localDay = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; };

export default function Gym({ plan, day, goal, onExit }: { plan: PlanOut; day: PlanDay; goal: Goal; onExit: () => void }) {
  const t = useTheme();
  const list = day.exercises ?? [];
  const [i, setI] = useState(0);
  const [s, setS] = useState(0);
  const [stage, setStage] = useState<Stage>('pick');
  const [w, setW] = useState(0);
  const [reps, setReps] = useState(0);
  const [eff, setEff] = useState<Effort | null>(null);
  const [sets, setSets] = useState<SetLog[]>([]);
  const [hardRun, setHardRun] = useState(0);
  const [advice, setAdvice] = useState<SetAdvice | null>(null);
  const [exNote, setExNote] = useState('');
  const [restEnd, setRestEnd] = useState(0);
  const [restTotal, setRestTotal] = useState(1);
  const [nextIsExercise, setNextIsExercise] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [confirmEnd, setConfirmEnd] = useState(false);
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [saveMsg, setSaveMsg] = useState('');
  const [nextWeights, setNextWeights] = useState<Record<string, { weight: number; note: string }>>({});
  const startedAt = useRef(Date.now());
  const beeped = useRef(false);

  const x = list[i];
  const def = x ? plan.exercises[x.id] : undefined;

  useEffect(() => {
    activateKeepAwakeAsync('gym').catch(() => {});
    return () => { deactivateKeepAwake('gym').catch(() => {}); };
  }, []);

  useEffect(() => {
    if (stage !== 'rest') return;
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, [stage]);

  const left = Math.max(0, (restEnd - now) / 1000);
  useEffect(() => {
    if (stage === 'rest' && left <= 0 && !beeped.current) {
      beeped.current = true;
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {});
      Vibration.vibrate([0, 200, 100, 200]);
    }
  }, [stage, left]);

  function startExercise(idx: number) {
    const e = list[idx]; const d = plan.exercises[e.id];
    setI(idx); setS(0); setAdvice(null); setEff(null); setHardRun(0);
    setExNote(plan.notes[e.id] ?? '');
    if (d.bw) { setW(0); setStage('set'); } else { setW(e.start_weight || snap(plan.dumbbells, d.start)); setStage('pick'); }
  }
  useEffect(() => { if (list.length) startExercise(0); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

  function saveSet() {
    if (!x || !def || !eff) return;
    const a = adviseSet({ goal, compound: def.type === 'c', bodyweight: def.bw, timed: def.timed, list: plan.dumbbells, w, reps, eff, lo: x.reps_lo, hi: x.reps_hi, hardRun });
    const logged = [...sets, { ex: x.id, w, reps, eff }];
    setSets(logged); setHardRun(eff === 'hard' ? hardRun + 1 : 0); setAdvice(a); setW(a.nextWeight);
    const ns = s + 1;
    const lastSet = ns >= x.sets;
    const lastEx = i + 1 >= list.length;
    setS(ns);
    setEff(null);
    if (lastSet && lastEx) { finish(logged); return; }
    setNextIsExercise(lastSet);
    beeped.current = false;
    setRestTotal(a.rest); setRestEnd(Date.now() + a.rest * 1000); setNow(Date.now());
    setStage('rest');
  }

  async function finish(logged: SetLog[]) {
    setStage('summary');
    if (!logged.length) { setSaveState('saved'); return; }
    await persist(logged);
  }

  async function persist(logged: SetLog[]) {
    setSaveState('saving'); setSaveMsg('');
    try {
      const r = await api<{ next: Record<string, { weight: number; note: string }> }>('/workouts', { method: 'POST', body: {
        day: localDay(), name: day.name, minutes: Math.max(1, Math.round((Date.now() - startedAt.current) / 60000)), sets: logged } });
      setNextWeights(r.next); setSaveState('saved');
    } catch (e) {
      setSaveState('error'); setSaveMsg(e instanceof ApiError ? e.message : 'Could not save.');
    }
  }

  const minutes = Math.round((Date.now() - startedAt.current) / 60000);
  const unit = def?.timed ? 'sec' : 'reps';
  const range = x ? `${x.reps_lo}–${x.reps_hi} ${unit}` : '';

  const Big = ({ children }: { children: React.ReactNode }) => <Text style={{ color: t.ink, fontSize: 56, fontWeight: '800', fontVariant: ['tabular-nums'], textAlign: 'center', flex: 1 }}>{children}</Text>;
  const Round = ({ label, onPress }: { label: string; onPress: () => void }) => (
    <Pressable accessibilityRole="button" accessibilityLabel={label === '+' ? 'More' : 'Less'} onPress={onPress}
      style={{ width: 64, height: 64, borderRadius: 32, borderWidth: 3, borderColor: t.ink, alignItems: 'center', justifyContent: 'center' }}>
      <Text style={{ color: t.ink, fontSize: 30, fontWeight: '800' }}>{label}</Text>
    </Pressable>
  );
  const Pips = () => (
    <Row>{Array.from({ length: x?.sets ?? 0 }).map((_, k) => (
      <View key={k} style={{ width: 34, height: 34, borderRadius: 17, borderWidth: 3, alignItems: 'center', justifyContent: 'center',
        borderColor: k <= s ? t.accent : t.ink2, backgroundColor: k < s ? t.accent : 'transparent' }}>
        <Text style={{ color: k < s ? t.accentInk : k === s ? t.accent : t.ink2, fontWeight: '800' }}>{k + 1}</Text>
      </View>))}</Row>
  );
  const End = () => confirmEnd ? (
    <Card><Body>End the workout and save the sets you have done?</Body>
      <Row><Btn small title="Keep going" onPress={() => setConfirmEnd(false)} />
        <Btn small kind="danger" title="End and save" onPress={() => { setConfirmEnd(false); finish(sets); }} /></Row></Card>
  ) : <Btn small kind="ghost" title="End workout" onPress={() => setConfirmEnd(true)} />;

  const effOptions = useMemo<[Effort, string, string][]>(() => [['easy', 'Easy', '3 or more reps left in the tank'], ['good', 'Just right', '1 to 2 reps left'], ['hard', 'Hard', 'Nothing left, form was slipping']], []);

  if (stage === 'summary') {
    const ids = [...new Set(sets.map((q) => q.ex))];
    return (
      <Screen>
        <Label>Workout complete</Label><H1>{day.name}</H1>
        {sets.length === 0 ? <Body muted>No sets were logged, so nothing was saved.</Body> : (
          <Row>
            {[[String(sets.length), 'Sets'], [`${Math.max(1, minutes)} min`, 'Time'], [String(ids.length), 'Exercises'], [String(Math.round(volume(sets))), 'Volume kg×reps']].map(([v, l]) => (
              <Card key={l} style={{ flexGrow: 1, flexBasis: '45%' }}><Num>{v}</Num><Label>{l}</Label></Card>))}
          </Row>)}
        {saveState === 'saving' ? <Notice kind="info">Saving your workout…</Notice> : null}
        {saveState === 'error' ? <><Notice kind="error">{saveMsg} Your sets are still on this screen. Do not close the app until it saves.</Notice><Btn title="Try saving again" kind="primary" onPress={() => persist(sets)} /></> : null}
        {saveState === 'saved' && ids.length ? (
          <Card><H2>Next time</H2>
            {ids.map((id) => (<View key={id}><Body>{plan.exercises[id].name}{nextWeights[id] && !plan.exercises[id].bw ? ` · ${nextWeights[id].weight} kg` : ''}</Body>
              <Body muted>{nextWeights[id]?.note ?? ''}</Body></View>))}
          </Card>) : null}
        <Notice kind="good">Eat 25 to 40 g of protein with some carbs within 2 hours, drink water, and sleep well tonight.</Notice>
        <Btn kind="primary" big title="Done" onPress={onExit} disabled={saveState === 'saving' || saveState === 'error'} />
        {saveState === 'error' ? <Btn kind="ghost" small title="Leave without saving" onPress={onExit} /> : null}
      </Screen>
    );
  }
  if (!x || !def) return <Screen><Body>No exercises today.</Body><Btn title="Back" onPress={onExit} /></Screen>;

  const nx = list[i + 1];
  return (
    <Screen>
      <Row style={{ justifyContent: 'space-between' }}>
        <Label>{`Exercise ${i + 1} of ${list.length} · ${minutes} min`}</Label>
      </Row>
      <ProgressBar value={(i + (s / x.sets)) / list.length} />
      <View style={{ gap: 2 }}><H1>{def.name}</H1><Body muted>{def.muscles}</Body></View>

      {stage === 'pick' ? (<>
        <Body muted>{def.cue}</Body>
        <Card>
          <Label>Choose your dumbbell</Label>
          <Row style={{ flexWrap: 'nowrap' }}><Round label="−" onPress={() => setW(down(plan.dumbbells, w))} /><Big>{w}<Text style={{ fontSize: 18, color: t.ink2 }}> kg</Text></Big><Round label="+" onPress={() => setW(up(plan.dumbbells, w))} /></Row>
          <Body muted style={{ textAlign: 'center' }}>{def.one ? 'One dumbbell, held with both hands.' : 'Each hand.'}</Body>
          <Body>Pick a size you can lift for about {x.reps_hi} clean reps with 2 reps left in the tank. Not sure? Start lighter. You can go up after any set.</Body>
          {exNote ? <Notice kind="good">{exNote}</Notice> : null}
        </Card>
        <Btn kind="primary" big title={`Start set 1 of ${x.sets}`} onPress={() => setStage('set')} />
      </>) : null}

      {stage === 'set' ? (<>
        <Pips />
        <Card style={{ alignItems: 'center' }}>
          <Label>{`Set ${s + 1} of ${x.sets} · target`}</Label>
          <Num size={40}>{range}</Num>
          {!def.bw ? <Num size={26}>{w} kg {def.one ? '' : 'each hand'}</Num> : null}
        </Card>
        {advice ? <Notice kind={advice.kind === 'up' ? 'good' : advice.kind === 'ok' ? 'info' : 'warn'}>{advice.msg}</Notice> : null}
        <Body muted>{def.cue}</Body>
        <Btn kind="primary" big title="Done set" onPress={() => { setReps(def.timed ? 30 : x.reps_hi); setEff(null); setStage('log'); }} />
        <Row>{!def.bw ? <Btn small kind="ghost" title="Change dumbbell" onPress={() => setStage('pick')} /> : null}
          <Btn small kind="ghost" title="Skip exercise" onPress={() => (nx ? startExercise(i + 1) : finish(sets))} /></Row>
      </>) : null}

      {stage === 'log' ? (<>
        <Pips />
        <H2>{`How did set ${s + 1} go?`}</H2>
        <Card>
          <Label>{def.timed ? 'Seconds held' : 'Reps completed'}</Label>
          <Row style={{ flexWrap: 'nowrap' }}><Round label="−" onPress={() => setReps(Math.max(0, reps - (def.timed ? 5 : 1)))} /><Big>{reps}</Big><Round label="+" onPress={() => setReps(Math.min(200, reps + (def.timed ? 5 : 1)))} /></Row>
        </Card>
        {effOptions.map(([k, title, sub]) => (
          <Pressable key={k} accessibilityRole="button" accessibilityState={{ selected: eff === k }} onPress={() => setEff(k)}
            style={{ borderWidth: 2, borderColor: eff === k ? t.accent : t.line, backgroundColor: eff === k ? t.accentSoft : t.surface, borderRadius: 8, padding: 14, minHeight: 60 }}>
            <Text style={{ color: t.ink, fontSize: 18, fontWeight: '800', textTransform: 'uppercase' }}>{title}</Text>
            <Text style={{ color: t.ink2, fontSize: 14 }}>{sub}</Text>
          </Pressable>))}
        <Btn kind="primary" big title="Save set and rest" disabled={!eff} onPress={saveSet} />
      </>) : null}

      {stage === 'rest' ? (<>
        <Card style={{ alignItems: 'center' }}>
          <Label>{nextIsExercise ? 'Exercise done · rest' : 'Rest'}</Label>
          <Text accessibilityLiveRegion="polite" style={{ color: t.ink, fontSize: 80, fontWeight: '800', fontVariant: ['tabular-nums'] }}>{fmtClock(left)}</Text>
          <View style={{ alignSelf: 'stretch' }}><ProgressBar value={1 - left / restTotal} /></View>
        </Card>
        {left <= 0 ? <Notice kind="good">Rest is over. Go when you feel ready.</Notice> : null}
        {advice ? <Notice kind={advice.kind === 'up' ? 'good' : advice.kind === 'ok' ? 'info' : 'warn'}>{advice.msg}</Notice> : null}
        {minutes >= 75 ? <Notice kind="warn">You have trained for over 75 minutes. Finish this exercise and wrap up with a stretch.</Notice> : null}
        <Body>
          <Text style={{ fontWeight: '800' }}>Next up: </Text>
          {nextIsExercise && nx ? `${plan.exercises[nx.id].name} · ${nx.sets} sets of ${nx.reps_lo}–${nx.reps_hi}` : `Set ${s + 1} of ${x.sets} · ${range}${def.bw ? '' : ` at ${w} kg`}`}
        </Body>
        <Row>
          <Btn title="+15 s" onPress={() => { setRestEnd((r) => r + 15000); setRestTotal((r) => r + 15); beeped.current = false; }} />
          <Btn kind="primary" title={nextIsExercise ? 'Next exercise' : `Start set ${s + 1}`} onPress={() => { if (nextIsExercise) startExercise(i + 1); else { setStage('set'); } }} />
        </Row>
      </>) : null}
      <End />
    </Screen>
  );
}
