import { StatusBar } from 'expo-status-bar';
import React, { useState } from 'react';
import { ActivityIndicator, Pressable, Text, View } from 'react-native';
import { SafeAreaProvider, useSafeAreaInsets } from 'react-native-safe-area-context';
import { AuthProvider, useAuth } from './src/auth';
import Auth from './src/screens/Auth';
import Cardio from './src/screens/Cardio';
import Coach from './src/screens/Coach';
import Eat from './src/screens/Eat';
import Onboarding from './src/screens/Onboarding';
import Today from './src/screens/Today';
import You from './src/screens/You';
import { useTheme } from './src/theme';

type Tab = 'today' | 'cardio' | 'eat' | 'coach' | 'you';
const TABS: [Tab, string][] = [['today', 'Today'], ['cardio', 'Cardio'], ['eat', 'Eat'], ['coach', 'Coach'], ['you', 'You']];

function Shell() {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  const { status, me } = useAuth();
  const [tab, setTab] = useState<Tab>('today');
  const [immersive, setImmersive] = useState(false);
  const [editing, setEditing] = useState(false);

  if (status === 'loading') return <View style={{ flex: 1, backgroundColor: t.bg, justifyContent: 'center' }}><ActivityIndicator color={t.accent} size="large" /></View>;
  if (status === 'out') return <Auth />;
  if (me?.health_paused) {
    // Health consent is withdrawn: only the privacy controls are available until it is switched back on.
    return <You onEditProfile={() => {}} paused />;
  }
  if (me && (!me.onboarded || editing)) return <Onboarding onDone={() => setEditing(false)} />;

  return (
    <View style={{ flex: 1, backgroundColor: t.bg }}>
      <View style={{ flex: 1 }}>
        {tab === 'today' ? <Today setImmersive={setImmersive} /> : null}
        {tab === 'cardio' ? <Cardio /> : null}
        {tab === 'eat' ? <Eat /> : null}
        {tab === 'coach' ? <Coach /> : null}
        {tab === 'you' ? <You onEditProfile={() => setEditing(true)} /> : null}
      </View>
      {!immersive ? (
        <View accessibilityRole="tablist" style={{ flexDirection: 'row', backgroundColor: t.surface, borderTopColor: t.line, borderTopWidth: 1, paddingBottom: insets.bottom }}>
          {TABS.map(([k, label]) => (
            <Pressable key={k} accessibilityRole="tab" accessibilityState={{ selected: tab === k }} onPress={() => setTab(k)}
              style={{ flex: 1, minHeight: 58, alignItems: 'center', justifyContent: 'center', borderTopWidth: 3, borderTopColor: tab === k ? t.accent : 'transparent' }}>
              <Text style={{ color: tab === k ? t.accent : t.ink2, fontWeight: '800', fontSize: 13, textTransform: 'uppercase', letterSpacing: 0.6 }}>{label}</Text>
            </Pressable>))}
        </View>) : null}
    </View>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <StatusBar style="auto" />
        <Shell />
      </AuthProvider>
    </SafeAreaProvider>
  );
}
