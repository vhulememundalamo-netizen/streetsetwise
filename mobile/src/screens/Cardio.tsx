import { activateKeepAwakeAsync, deactivateKeepAwake } from 'expo-keep-awake';
import * as Location from 'expo-location';
import { Pedometer } from 'expo-sensors';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Text, View } from 'react-native';
import { api, ApiError } from '../api';
import { useAuth } from '../auth';
import { haversine, liveKcal, stepsToMeters } from '../lib/cardio';
import { fmtClock } from '../lib/gym';
import { useTheme } from '../theme';
import type { CardioKind, CardioResult, CardioSummary } from '../types';
import { Body, Btn, Card, Chip, Field, H1, H2, Label, Notice, Num, Row, Screen } from '../ui';

const KINDS: [CardioKind, string][] = [['walk', 'Walk'], ['run', 'Run'], ['cycle', 'Cycle']];
const tzOffset = () => -new Date().getTimezoneOffset();

export default function Cardio() {
  const t = useTheme();
  const { me } = useAuth();
  const weight = me?.weight_kg ?? 70; const height = me?.height_cm ?? 170;
  const [kind, setKind] = useState<CardioKind>('walk');
  const [tracking, setTracking] = useState(false);
  const [steps, setSteps] = useState(0);
  const [gpsMeters, setGpsMeters] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [gpsOk, setGpsOk] = useState(true);
  const [pedoOk, setPedoOk] = useState(true);
  const [error, setError] = useState('');
  const [result, setResult] = useState<CardioResult | null>(null);
  const [summary, setSummary] = useState<CardioSummary | null>(null);
  const [busy, setBusy] = useState(false);
  const [mMin, setMMin] = useState(''); const [mKm, setMKm] = useState(''); const [mSteps, setMSteps] = useState('');
  const startRef = useRef(0);
  const subs = useRef<{ remove: () => void }[]>([]);
  const last = useRef<{ lat: number; lon: number; t: number } | null>(null);

  const loadSummary = useCallback(async () => {
    try { setSummary(await api<CardioSummary>(`/cardio/summary?tz_offset_minutes=${tzOffset()}`)); } catch { /* shown only when saving fails */ }
  }, []);
  useEffect(() => { loadSummary(); }, [loadSummary]);

  useEffect(() => {
    if (!tracking) return;
    const id = setInterval(() => setElapsed(Math.round((Date.now() - startRef.current) / 1000)), 1000);
    return () => clearInterval(id);
  }, [tracking]);
  useEffect(() => () => { subs.current.forEach((s) => s.remove()); deactivateKeepAwake('cardio').catch(() => {}); }, []);

  const meters = gpsMeters > 0 ? gpsMeters : stepsToMeters(kind, steps, height);
  const kcal = liveKcal(kind, elapsed, meters, weight);

  async function start() {
    setError(''); setResult(null); setSteps(0); setGpsMeters(0); setElapsed(0); last.current = null;
    // Permissions are asked now, when you start, and only for as long as the session runs.
    const loc = await Location.requestForegroundPermissionsAsync();
    setGpsOk(loc.granted);
    let pedo = false;
    if (kind !== 'cycle') {
      try { pedo = (await Pedometer.isAvailableAsync()) && (await Pedometer.requestPermissionsAsync()).granted; } catch { pedo = false; }
    }
    setPedoOk(pedo);
    if (!loc.granted && !pedo) { setError('Allow motion or location access in your phone settings so Setwise can measure your session. You can also enter it by hand below.'); return; }
    startRef.current = Date.now();
    if (pedo) subs.current.push(Pedometer.watchStepCount((r) => setSteps(r.steps)));
    if (loc.granted) {
      try {
        subs.current.push(await Location.watchPositionAsync({ accuracy: Location.LocationAccuracy.High, timeInterval: 2000, distanceInterval: 3 }, (p) => {
          const { latitude: lat, longitude: lon, accuracy } = p.coords;
          if (accuracy != null && accuracy > 25) return;
          const prev = last.current;
          last.current = { lat, lon, t: p.timestamp };
          if (!prev) return;
          const d = haversine(prev.lat, prev.lon, lat, lon);
          const dt = (p.timestamp - prev.t) / 1000;
          const maxSpeed = kind === 'cycle' ? 20 : kind === 'run' ? 8 : 4; // m/s, drops GPS jumps
          if (d >= 2 && dt > 0 && d / dt <= maxSpeed) setGpsMeters((m) => m + d); // route is never stored, only the total
        }));
      } catch { setGpsOk(false); }
    }
    activateKeepAwakeAsync('cardio').catch(() => {});
    setTracking(true);
  }

  async function stop() {
    subs.current.forEach((s) => s.remove()); subs.current = [];
    deactivateKeepAwake('cardio').catch(() => {});
    setTracking(false);
    const secs = Math.round((Date.now() - startRef.current) / 1000);
    await save({ kind, seconds: secs, steps, distance_m: Math.round(gpsMeters), started_at: new Date(startRef.current).toISOString() });
  }

  async function save(body: { kind: CardioKind; seconds: number; steps: number; distance_m: number; started_at: string }) {
    setBusy(true); setError('');
    try {
      setResult(await api<CardioResult>('/cardio', { method: 'POST', body }));
      loadSummary();
    } catch (e) { setError(e instanceof ApiError ? e.message : 'Could not save this session.'); }
    finally { setBusy(false); }
  }

  async function saveManual() {
    const minutes = parseFloat(mMin.replace(',', '.')); const km = parseFloat((mKm || '0').replace(',', '.')); const st = parseInt(mSteps || '0', 10);
    if (!(minutes >= 1)) return setError('Enter how many minutes you trained.');
    await save({ kind, seconds: Math.round(minutes * 60), steps: Number.isFinite(st) ? st : 0, distance_m: Math.round((Number.isFinite(km) ? km : 0) * 1000), started_at: new Date(Date.now() - minutes * 60000).toISOString() });
    setMMin(''); setMKm(''); setMSteps('');
  }

  const maxSteps = Math.max(1, ...(summary?.week.map((d) => d.steps) ?? [1]));
  return (
    <Screen>
      <Label>Cardio</Label><H1>Steps and distance</H1>
      {!tracking ? <Row>{KINDS.map(([k, n]) => <Chip key={k} title={n} on={kind === k} onPress={() => setKind(k)} />)}</Row> : null}

      {tracking ? (
        <Card style={{ alignItems: 'center' }}>
          <Label>{`${kind} in progress`}</Label>
          <Text style={{ color: t.ink, fontSize: 64, fontWeight: '800', fontVariant: ['tabular-nums'] }}>{fmtClock(elapsed)}</Text>
          <Row style={{ justifyContent: 'center', gap: 24 }}>
            <View style={{ alignItems: 'center' }}><Num>{kind === 'cycle' ? '–' : steps}</Num><Label>Steps</Label></View>
            <View style={{ alignItems: 'center' }}><Num>{(meters / 1000).toFixed(2)}</Num><Label>km</Label></View>
            <View style={{ alignItems: 'center' }}><Num>{Math.round(kcal)}</Num><Label>kcal</Label></View>
          </Row>
          {!gpsOk && kind !== 'cycle' ? <Body muted>GPS is off, so distance is estimated from your steps.</Body> : null}
          {!pedoOk && kind !== 'cycle' ? <Body muted>Step counting is unavailable, so distance comes from GPS.</Body> : null}
          <Body muted style={{ textAlign: 'center' }}>Keep Setwise open and the screen on. Your phone stops counting steps in the background.</Body>
          <Btn kind="primary" big title="Finish" onPress={stop} />
        </Card>
      ) : (
        <Btn kind="primary" big title={`Start ${kind}`} onPress={start} busy={busy} />
      )}

      {error ? <Notice kind="error">{error}</Notice> : null}
      {result ? (
        <Card>
          <H2>Session saved</H2>
          <Row style={{ gap: 24 }}>
            <View><Num>{(result.distance_m / 1000).toFixed(2)}</Num><Label>km</Label></View>
            <View><Num>{result.kcal}</Num><Label>active kcal</Label></View>
            {result.speed_kmh > 0 ? <View><Num>{result.speed_kmh.toFixed(1)}</Num><Label>km/h</Label></View> : null}
          </Row>
          <Body muted>{result.note}</Body>
        </Card>
      ) : null}

      {summary ? (
        <Card>
          <H2>This week</H2>
          <Row style={{ gap: 24 }}>
            <View><Num>{summary.week_total.steps.toLocaleString()}</Num><Label>Steps</Label></View>
            <View><Num>{(summary.week_total.distance_m / 1000).toFixed(1)}</Num><Label>km</Label></View>
            <View><Num>{summary.week_total.kcal}</Num><Label>kcal</Label></View>
          </Row>
          <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 6, height: 90 }} accessibilityLabel="Steps per day this week">
            {summary.week.map((d) => (
              <View key={d.day} style={{ flex: 1, alignItems: 'center', gap: 4 }}>
                <View style={{ width: '100%', height: Math.max(3, (d.steps / maxSteps) * 70), backgroundColor: d.day === summary.week[summary.week.length - 1].day ? t.accent : t.surface2, borderRadius: 3 }} />
                <Text style={{ color: t.ink2, fontSize: 11 }}>{['S', 'M', 'T', 'W', 'T', 'F', 'S'][new Date(d.day + 'T12:00:00').getDay()]}</Text>
              </View>))}
          </View>
        </Card>
      ) : null}

      {!tracking ? (
        <Card>
          <H2>Add a session by hand</H2>
          <Body muted>For treadmills, bikes or a run you forgot to start. Distance and steps are optional.</Body>
          <Field label="Minutes" value={mMin} onChangeText={setMMin} keyboardType="decimal-pad" />
          <Field label="Distance (km, optional)" value={mKm} onChangeText={setMKm} keyboardType="decimal-pad" />
          <Field label="Steps (optional)" value={mSteps} onChangeText={setMSteps} keyboardType="number-pad" />
          <Btn title="Save session" onPress={saveManual} busy={busy} />
        </Card>
      ) : null}
      <Notice kind="info">Calories shown are active calories above resting, an estimate with roughly 20% error. GPS routes stay on your phone. Only the totals are saved.</Notice>
    </Screen>
  );
}
