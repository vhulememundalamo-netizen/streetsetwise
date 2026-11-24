// In-session coaching. Runs on the phone so a workout works with no signal.
// Between sessions the server model (progression.py) decides your next starting weight.
import type { Effort, Goal, SetLog } from '../types';

export const up = (list: number[], w: number) => list.find((x) => x > w) ?? w;
export const down = (list: number[], w: number) => [...list].reverse().find((x) => x < w) ?? w;
export const snap = (list: number[], w: number) => list.reduce((b, x) => (Math.abs(x - w) < Math.abs(b - w) ? x : b), list[0]);

export function restSeconds(goal: Goal, compound: boolean, eff: Effort, reps: number, lo: number): number {
  let base: number;
  if (goal === 'strength') base = compound ? 150 : 90;
  else if (goal === 'muscle') base = compound ? 90 : 60;
  else if (goal === 'lose') base = compound ? 60 : 45;
  else base = compound ? 75 : 60;
  if (eff === 'hard') base += 30;
  if (reps < lo) base += 30;
  if (eff === 'easy') base -= 15;
  return Math.max(30, base);
}

export interface SetAdvice { msg: string; kind: 'up' | 'down' | 'warn' | 'ok'; nextWeight: number; rest: number }

export function adviseSet(o: {
  goal: Goal; compound: boolean; bodyweight: boolean; timed: boolean; list: number[];
  w: number; reps: number; eff: Effort; lo: number; hi: number; hardRun: number;
}): SetAdvice {
  const { w, reps, eff, lo, hi, list, bodyweight, timed } = o;
  let msg: string; let kind: SetAdvice['kind'] = 'ok'; let nw = w;
  const unit = timed ? 'seconds' : 'reps';
  if (bodyweight) {
    if (reps < lo) { msg = `Short of ${lo} ${unit}. Rest, then aim for ${lo} on the next set. An easier version is fine.`; kind = 'down'; }
    else if (reps >= hi && eff === 'easy') { msg = timed ? `Strong hold. Try to pass ${hi} seconds next set.` : 'Strong. Next set go slower with a one second pause at the bottom.'; kind = 'up'; }
    else if (eff === 'hard') { msg = 'Hard set. Take the longer rest.'; kind = 'warn'; }
    else msg = 'Good set. Same effort next set.';
  } else if (reps < lo) {
    nw = down(list, w);
    msg = nw < w ? `Too heavy for ${lo} reps. Drop to ${nw} kg for the next set.` : 'Below target. Keep it light and focus on form.'; kind = 'down';
  } else if (reps >= hi && eff === 'easy') {
    nw = up(list, w);
    msg = nw > w ? `That was easy at ${hi} reps. Move up to ${nw} kg for the next set.` : 'Easy at the heaviest dumbbell in the list. Slow the reps down.'; kind = 'up';
  } else if (eff === 'hard') { msg = `Hard set. Stay at ${w} kg and take the longer rest.`; kind = 'warn'; }
  else if (reps >= hi) { msg = `Top of the range. Stay at ${w} kg. Hit ${hi} reps on every set and you move up next workout.`; kind = 'up'; }
  else msg = `Good set. Stay at ${w} kg and try for one more rep next set.`;

  const hardRun = eff === 'hard' ? o.hardRun + 1 : 0;
  let rest = restSeconds(o.goal, o.compound, eff, reps, lo);
  if (hardRun >= 2) { msg += ' Two hard sets in a row. Drink water, take the longer break, and drop one size if your form slips.'; kind = 'warn'; rest += 60; }
  return { msg, kind, nextWeight: nw, rest };
}

export function volume(sets: SetLog[]) { return sets.reduce((a, s) => a + s.w * s.reps, 0); }
export function fmtClock(sec: number) { const s = Math.max(0, Math.round(sec)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; }
