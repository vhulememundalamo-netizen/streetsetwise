import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, TextInputProps, View, ViewStyle } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTheme } from './theme';

export function Screen({ children, bottom = 0 }: { children: React.ReactNode; bottom?: number }) {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  return (
    <ScrollView style={{ flex: 1, backgroundColor: t.bg }} keyboardShouldPersistTaps="handled"
      contentContainerStyle={{ paddingTop: insets.top + 12, paddingBottom: insets.bottom + 24 + bottom, paddingHorizontal: 16, gap: 14 }}>
      {children}
    </ScrollView>
  );
}

export function H1({ children }: { children: React.ReactNode }) {
  const t = useTheme();
  return <Text accessibilityRole="header" style={{ color: t.ink, fontSize: 32, fontWeight: '800', textTransform: 'uppercase', letterSpacing: 0.5 }}>{children}</Text>;
}
export function H2({ children }: { children: React.ReactNode }) {
  const t = useTheme();
  return <Text accessibilityRole="header" style={{ color: t.ink, fontSize: 20, fontWeight: '800', textTransform: 'uppercase', letterSpacing: 0.5 }}>{children}</Text>;
}
export function Body({ children, muted, style }: { children: React.ReactNode; muted?: boolean; style?: object }) {
  const t = useTheme();
  return <Text style={[{ color: muted ? t.ink2 : t.ink, fontSize: 16, lineHeight: 23 }, style]}>{children}</Text>;
}
export function Label({ children }: { children: React.ReactNode }) {
  const t = useTheme();
  return <Text style={{ color: t.ink2, fontSize: 12, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 1.2 }}>{children}</Text>;
}
export function Num({ children, size = 28, color }: { children: React.ReactNode; size?: number; color?: string }) {
  const t = useTheme();
  return <Text style={{ color: color ?? t.ink, fontSize: size, fontWeight: '800', fontVariant: ['tabular-nums'] }}>{children}</Text>;
}

export function Card({ children, style }: { children: React.ReactNode; style?: ViewStyle }) {
  const t = useTheme();
  return <View style={[{ backgroundColor: t.surface, borderColor: t.line, borderWidth: 1, borderRadius: 8, padding: 16, gap: 10 }, style]}>{children}</View>;
}

export function Btn({ title, onPress, kind = 'secondary', disabled, busy, big, small }:
  { title: string; onPress: () => void; kind?: 'primary' | 'secondary' | 'ghost' | 'danger'; disabled?: boolean; busy?: boolean; big?: boolean; small?: boolean }) {
  const t = useTheme();
  const bg = kind === 'primary' ? t.accent : 'transparent';
  const fg = kind === 'primary' ? t.accentInk : kind === 'danger' ? t.bad : kind === 'ghost' ? t.ink2 : t.ink;
  const border = kind === 'primary' ? t.accent : kind === 'danger' ? t.bad : kind === 'ghost' ? t.line : t.ink;
  const off = disabled || busy;
  return (
    <Pressable accessibilityRole="button" accessibilityState={{ disabled: !!off }} disabled={off} onPress={onPress}
      style={({ pressed }) => ({ minHeight: big ? 68 : small ? 42 : 54, borderRadius: 6, borderWidth: 2, borderColor: border, backgroundColor: bg,
        alignItems: 'center', justifyContent: 'center', paddingHorizontal: 18, opacity: off ? 0.45 : pressed ? 0.8 : 1 })}>
      <Text style={{ color: fg, fontSize: big ? 22 : small ? 14 : 17, fontWeight: '800', textTransform: 'uppercase', letterSpacing: 0.8 }}>{busy ? 'Please wait…' : title}</Text>
    </Pressable>
  );
}

export function Chip({ title, on, onPress, danger }: { title: string; on: boolean; onPress: () => void; danger?: boolean }) {
  const t = useTheme();
  const c = danger ? t.warn : t.accent;
  return (
    <Pressable accessibilityRole="button" accessibilityState={{ selected: on }} onPress={onPress}
      style={{ minHeight: 44, paddingHorizontal: 14, justifyContent: 'center', borderRadius: 6, borderWidth: 2, borderColor: on ? c : t.line,
        backgroundColor: on ? (danger ? t.warnSoft : t.accentSoft) : t.surface }}>
      <Text style={{ color: on ? c : t.ink, fontWeight: '700', fontSize: 15 }}>{title}</Text>
    </Pressable>
  );
}

export function Row({ children, style }: { children: React.ReactNode; style?: ViewStyle }) {
  return <View style={[{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, alignItems: 'center' }, style]}>{children}</View>;
}

export function Field({ label, ...p }: { label: string } & TextInputProps) {
  const t = useTheme();
  return (
    <View style={{ gap: 6 }}>
      <Label>{label}</Label>
      <TextInput accessibilityLabel={label} placeholderTextColor={t.ink2} {...p}
        style={{ minHeight: 52, borderWidth: 2, borderColor: t.line, borderRadius: 6, paddingHorizontal: 14, color: t.ink, backgroundColor: t.surface, fontSize: 17 }} />
    </View>
  );
}

export function Notice({ kind = 'info', children }: { kind?: 'info' | 'warn' | 'good' | 'error'; children: React.ReactNode }) {
  const t = useTheme();
  const map = { info: [t.accentSoft, t.accent], warn: [t.warnSoft, t.warn], good: [t.goodSoft, t.good], error: [t.warnSoft, t.bad] } as const;
  const [bg, bar] = map[kind];
  return (
    <View accessibilityRole={kind === 'error' ? 'alert' : undefined}
      style={{ backgroundColor: bg, borderLeftColor: bar, borderLeftWidth: 5, borderRadius: 4, padding: 12 }}>
      <Text style={{ color: t.ink, fontSize: 15, lineHeight: 21 }}>{children}</Text>
    </View>
  );
}

export function Checkbox({ checked, onChange, children }: { checked: boolean; onChange: (v: boolean) => void; children: React.ReactNode }) {
  const t = useTheme();
  return (
    <Pressable accessibilityRole="checkbox" accessibilityState={{ checked }} onPress={() => onChange(!checked)}
      style={{ flexDirection: 'row', gap: 12, alignItems: 'flex-start', minHeight: 44 }}>
      <View style={{ width: 26, height: 26, borderRadius: 4, borderWidth: 2, borderColor: checked ? t.accent : t.ink2,
        backgroundColor: checked ? t.accent : 'transparent', alignItems: 'center', justifyContent: 'center', marginTop: 1 }}>
        {checked ? <Text style={{ color: t.accentInk, fontWeight: '900' }}>✓</Text> : null}
      </View>
      <Text style={{ color: t.ink, fontSize: 15, lineHeight: 21, flex: 1 }}>{children}</Text>
    </Pressable>
  );
}

export function ProgressBar({ value }: { value: number }) {
  const t = useTheme();
  return (
    <View style={{ height: 8, borderRadius: 4, backgroundColor: t.surface2, overflow: 'hidden' }}>
      <View style={{ height: 8, width: `${Math.max(0, Math.min(100, value * 100))}%`, backgroundColor: t.accent }} />
    </View>
  );
}

export const styles = StyleSheet.create({ flex1: { flex: 1 } });
