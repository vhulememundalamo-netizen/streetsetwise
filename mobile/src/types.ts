export type Goal = 'lose' | 'muscle' | 'strength' | 'fit';
export type Level = 'beginner' | 'intermediate' | 'advanced';
export type Effort = 'easy' | 'good' | 'hard';
export type CardioKind = 'walk' | 'run' | 'cycle';
export type Purpose = 'terms_privacy' | 'health_data' | 'ai_coach';

export interface Targets { kcal: number; protein: number; carbs: number; fat: number; water_l: number; maintenance_kcal: number }
export interface Me {
  email: string; goal: Goal; level: Level; days_per_week: number; sex: 'm' | 'f' | 'x' | null;
  height_cm: number | null; weight_kg: number | null; restrictions: string[]; onboarded: boolean;
  targets: Targets | null; health_paused?: boolean; consents: Partial<Record<Purpose, boolean>>; policy_version: string; information_officer: string;
}
export interface TokenOut { access_token: string; refresh_token: string; expires_in: number }

export interface ExerciseDef { name: string; muscles: string; type: 'c' | 'i'; cue: string; start: number; one: boolean; bw: boolean; timed: boolean }
export interface PlanExercise { id: string; sets: number; reps_lo: number; reps_hi: number; start_weight: number }
export interface PlanDay { day: string; type: 'lift' | 'cardio' | 'rest'; name: string; note?: string; exercises?: PlanExercise[] }
export interface PlanOut {
  plan: PlanDay[]; exercises: Record<string, ExerciseDef>; notes: Record<string, string>; dumbbells: number[]; targets: Targets;
  adherence: { rate: number; suggest_days: number; message: string };
}
export interface SetLog { ex: string; w: number; reps: number; eff: Effort }

export interface CardioResult { id?: string; distance_m: number; kcal: number; speed_kmh: number; met: number; method: string; note: string }
export interface CardioSummary {
  today: { steps: number; distance_m: number; kcal: number; seconds: number };
  week: { day: string; steps: number; distance_m: number; kcal: number; seconds: number }[];
  week_total: { steps: number; distance_m: number; kcal: number; seconds: number };
}

export interface Food { id: string; name: string; role: string; kcal: number; protein: number; carbs: number; fat: number; tags: string[] }
export interface Shake { name: string; protein_g: number; kcal: number; carbs_g: number; fat_g: number; contains: string[] }
export interface Pantry { foods: string[]; shakes: Shake[]; avoid: string[]; meals_per_day: 3 | 4 | 5; max_shakes: number }
export interface MealItem { name: string; amount: string; kind: string; kcal: number; protein: number; carbs: number; fat: number }
export interface Meal { name: string; items: MealItem[]; kcal: number; protein: number; carbs: number; fat: number }
export interface MealDay { meals: Meal[]; totals: { kcal: number; protein: number; carbs: number; fat: number }; targets: Record<string, number>; shakes_used: number; warnings: string[] }
export interface MealPlan { targets: Targets; days: MealDay[] }

export interface CoachReply { reply: string; source: 'safety' | 'ai' | 'rules'; hint: string | null }
export interface ChatMsg { role: 'user' | 'assistant'; content: string; source?: string }
