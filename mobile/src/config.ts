// Set EXPO_PUBLIC_API_URL when you build, for example https://api.yourdomain.co.za
const url = process.env.EXPO_PUBLIC_API_URL ?? 'http://10.0.2.2:8000';

// Health data must never travel over plain HTTP outside development.
if (!__DEV__ && !url.startsWith('https://')) {
  throw new Error('EXPO_PUBLIC_API_URL must be https in production builds');
}

export const API_URL = url.replace(/\/$/, '');
