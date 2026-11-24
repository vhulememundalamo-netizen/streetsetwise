// Live estimate while you move. The server recomputes the final numbers when you save.
import type { CardioKind } from '../types';

const TABLES: Record<CardioKind, [number, number][]> = {
  walk: [[2.0, 2.0], [3.2, 2.8], [4.0, 3.0], [4.8, 3.5], [5.6, 4.3], [6.4, 5.0], [7.2, 6.3]],
  run: [[8.0, 8.3], [9.7, 9.8], [11.3, 11.0], [12.9, 11.8], [14.5, 12.8], [16.1, 14.5]],
  cycle: [[10.0, 3.5], [16.0, 6.8], [19.0, 8.0], [22.0, 10.0], [25.0, 12.0], [30.0, 14.0]],
};

export function met(kind: CardioKind, kmh: number): number {
  const t = TABLES[kind];
  if (kmh <= t[0][0]) return t[0][1];
  if (kmh >= t[t.length - 1][0]) return t[t.length - 1][1];
  for (let i = 0; i < t.length - 1; i++) {
    const [s0, m0] = t[i]; const [s1, m1] = t[i + 1];
    if (kmh >= s0 && kmh <= s1) return m0 + ((m1 - m0) * (kmh - s0)) / (s1 - s0);
  }
  return t[t.length - 1][1];
}

/** Active kcal (above resting) */
export function liveKcal(kind: CardioKind, seconds: number, meters: number, weightKg: number): number {
  if (seconds < 30 || meters <= 0) return 0;
  const kmh = meters / 1000 / (seconds / 3600);
  return Math.max(0, met(kind, kmh) - 1) * weightKg * (seconds / 3600);
}

export function stepsToMeters(kind: CardioKind, steps: number, heightCm: number): number {
  const f = kind === 'run' ? 0.6 : kind === 'walk' ? 0.415 : 0;
  return steps * (heightCm / 100) * f;
}

export function haversine(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371000; const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1); const dLon = toRad(lon2 - lon1);
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}
