import { useColorScheme } from 'react-native';

const light = { bg: '#E7EAEC', surface: '#F5F7F8', surface2: '#DADFE2', ink: '#10181C', ink2: '#47565D', line: '#C3CBD0',
  accent: '#2347C9', accentInk: '#FFFFFF', accentSoft: '#D6DEF7', warn: '#9A4B06', warnSoft: '#F4E2CB', bad: '#B3261E',
  good: '#1B7A38', goodSoft: '#D3EBD9' };
const dark: typeof light = { bg: '#0D1215', surface: '#151C20', surface2: '#1F292E', ink: '#E7EEF0', ink2: '#98A8AF', line: '#2A373D',
  accent: '#86A5FF', accentInk: '#0A1230', accentSoft: '#1B2750', warn: '#F0B35A', warnSoft: '#3A2C14', bad: '#FF8A80',
  good: '#78D690', goodSoft: '#143322' };

export type Theme = typeof light;
export function useTheme(): Theme { return useColorScheme() === 'dark' ? dark : light; }
export const mono = { fontVariant: ['tabular-nums' as const] };
