import React, { useCallback, useEffect, useState } from 'react';
import { View } from 'react-native';
import { api, ApiError } from '../api';
import type { Food, MealPlan, Pantry, Shake } from '../types';
import { Body, Btn, Card, Chip, Field, H1, H2, Label, Notice, Num, Row, Screen } from '../ui';

const ROLES: [string, string][] = [['protein', 'Protein'], ['dairy', 'Dairy'], ['carb', 'Carbs'], ['veg', 'Vegetables'], ['fruit', 'Fruit'], ['fat', 'Fats']];
const AVOID = ['dairy', 'gluten', 'nuts', 'egg', 'fish', 'meat'];
const EMPTY: Pantry = { foods: [], shakes: [], avoid: [], meals_per_day: 4, max_shakes: 2 };

export default function Eat() {
  const [foods, setFoods] = useState<Food[]>([]);
  const [pantry, setPantry] = useState<Pantry>(EMPTY);
  const [plan, setPlan] = useState<MealPlan | null>(null);
  const [day, setDay] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const [sName, setSName] = useState(''); const [sP, setSP] = useState(''); const [sK, setSK] = useState(''); const [sC, setSC] = useState(''); const [sF, setSF] = useState('');

  const load = useCallback(async () => {
    try {
      const [f, p, last] = await Promise.all([api<{ foods: Food[] }>('/nutrition/foods'), api<Pantry>('/nutrition/pantry'), api<MealPlan | null>('/nutrition/plan/latest')]);
      setFoods(f.foods); setPantry(p); setPlan(last);
    } catch (e) { setError(e instanceof ApiError ? e.message : 'Could not load your foods.'); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const toggle = (id: string) => { setSaved(false); setPantry((p) => ({ ...p, foods: p.foods.includes(id) ? p.foods.filter((x) => x !== id) : [...p.foods, id] })); };
  const toggleAvoid = (a: string) => { setSaved(false); setPantry((p) => ({ ...p, avoid: p.avoid.includes(a) ? p.avoid.filter((x) => x !== a) : [...p.avoid, a] })); };

  function addShake() {
    const protein = parseFloat(sP.replace(',', '.')); const kcal = parseFloat(sK.replace(',', '.'));
    if (!sName.trim()) return setError('Give the shake a name.');
    if (!(protein >= 1 && protein <= 80)) return setError('Protein per serving should be between 1 and 80 g. Check the tub label.');
    if (!(kcal >= 10 && kcal <= 600)) return setError('Calories per serving should be between 10 and 600. Check the tub label.');
    const shake: Shake = { name: sName.trim().slice(0, 40), protein_g: protein, kcal, carbs_g: parseFloat(sC.replace(',', '.')) || 0, fat_g: parseFloat(sF.replace(',', '.')) || 0, contains: [] };
    setError(''); setSaved(false);
    setPantry((p) => ({ ...p, shakes: [...p.shakes, shake].slice(0, 5) }));
    setSName(''); setSP(''); setSK(''); setSC(''); setSF('');
  }

  async function generate(days: number) {
    setBusy(true); setError('');
    try {
      await api('/nutrition/pantry', { method: 'PUT', body: pantry });
      setSaved(true);
      setPlan(await api<MealPlan>('/nutrition/plan', { method: 'POST', body: { days } }));
      setDay(0);
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) setError('Pick at least one food you have at home first.');
      else setError(e instanceof ApiError ? e.message : 'Could not build your plan.');
    } finally { setBusy(false); }
  }

  const d = plan?.days[Math.min(day, (plan?.days.length ?? 1) - 1)];
  return (
    <Screen>
      <Label>Eat</Label><H1>What do you have?</H1>
      <Body muted>Tick the foods you have at home and add your protein shakes. Setwise builds meals from them to match your calories and protein.</Body>

      {ROLES.map(([role, title]) => (
        <Card key={role}>
          <H2>{title}</H2>
          <Row>{foods.filter((f) => f.role === role).map((f) => <Chip key={f.id} title={f.name} on={pantry.foods.includes(f.id)} onPress={() => toggle(f.id)} />)}</Row>
        </Card>))}

      <Card>
        <H2>Protein shakes</H2>
        {pantry.shakes.map((s, k) => (
          <Row key={k} style={{ justifyContent: 'space-between' }}>
            <View style={{ flex: 1 }}><Body>{s.name}</Body><Body muted>{`${s.protein_g} g protein · ${s.kcal} kcal per serving`}</Body></View>
            <Btn small kind="ghost" title="Remove" onPress={() => { setSaved(false); setPantry((p) => ({ ...p, shakes: p.shakes.filter((_, j) => j !== k) })); }} />
          </Row>))}
        <Field label="Shake name" value={sName} onChangeText={setSName} placeholder="e.g. Whey vanilla" />
        <Row>
          <View style={{ flexGrow: 1, flexBasis: '45%' }}><Field label="Protein (g)" value={sP} onChangeText={setSP} keyboardType="decimal-pad" /></View>
          <View style={{ flexGrow: 1, flexBasis: '45%' }}><Field label="Calories" value={sK} onChangeText={setSK} keyboardType="decimal-pad" /></View>
          <View style={{ flexGrow: 1, flexBasis: '45%' }}><Field label="Carbs (g)" value={sC} onChangeText={setSC} keyboardType="decimal-pad" /></View>
          <View style={{ flexGrow: 1, flexBasis: '45%' }}><Field label="Fat (g)" value={sF} onChangeText={setSF} keyboardType="decimal-pad" /></View>
        </Row>
        <Body muted>Use the numbers for one serving from the tub label, mixed the way you drink it.</Body>
        <Btn title="Add shake" onPress={addShake} />
      </Card>

      <Card>
        <H2>Avoid</H2>
        <Row>{AVOID.map((a) => <Chip key={a} danger title={a} on={pantry.avoid.includes(a)} onPress={() => toggleAvoid(a)} />)}</Row>
        <Label>Meals a day</Label>
        <Row>{([3, 4, 5] as const).map((n) => <Chip key={n} title={String(n)} on={pantry.meals_per_day === n} onPress={() => { setSaved(false); setPantry((p) => ({ ...p, meals_per_day: n })); }} />)}</Row>
        <Label>Shakes a day (at most)</Label>
        <Row>{[0, 1, 2].map((n) => <Chip key={n} title={String(n)} on={pantry.max_shakes === n} onPress={() => { setSaved(false); setPantry((p) => ({ ...p, max_shakes: n })); }} />)}</Row>
      </Card>

      {error ? <Notice kind="error">{error}</Notice> : null}
      <Row>
        <View style={{ flex: 1 }}><Btn kind="primary" title="Build today" busy={busy} onPress={() => generate(1)} /></View>
        <View style={{ flex: 1 }}><Btn title="Build my week" busy={busy} onPress={() => generate(7)} /></View>
      </Row>
      {saved ? <Body muted>Your foods are saved.</Body> : null}

      {plan && d ? (<>
        <H1>Your meals</H1>
        {plan.days.length > 1 ? <Row>{plan.days.map((_, k) => <Chip key={k} title={`Day ${k + 1}`} on={day === k} onPress={() => setDay(k)} />)}</Row> : null}
        <Row style={{ gap: 20 }}>
          <View><Num>{d.totals.kcal}</Num><Label>{`of ${d.targets.kcal} kcal`}</Label></View>
          <View><Num>{d.totals.protein} g</Num><Label>{`of ${d.targets.protein} g protein`}</Label></View>
        </Row>
        {d.warnings.map((w, k) => <Notice key={k} kind="warn">{w}</Notice>)}
        {d.meals.map((m) => (
          <Card key={m.name}>
            <Row style={{ justifyContent: 'space-between' }}><H2>{m.name}</H2><Body muted>{`${m.kcal} kcal · ${m.protein} g protein`}</Body></Row>
            {m.items.map((it, k) => (
              <Row key={k} style={{ justifyContent: 'space-between', flexWrap: 'nowrap' }}>
                <Body style={{ flex: 1 }}>{it.name}</Body><Body muted>{it.amount}</Body>
              </Row>))}
          </Card>))}
        <Notice kind="info">Calorie and protein figures are estimates from typical food values. Weigh food cooked, as eaten. This is general guidance, not medical or dietitian advice.</Notice>
      </>) : null}
    </Screen>
  );
}
