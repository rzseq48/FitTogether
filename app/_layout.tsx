import { Slot, useRouter, useSegments } from 'expo-router';
import { useEffect } from 'react';
import { AuthLoadingScreen, AuthProvider, useAuth } from '../lib/auth';

export default function RootLayout() {
  return (
    <AuthProvider>
      <AuthGate />
    </AuthProvider>
  );
}

function AuthGate() {
  const { loading, session } = useAuth();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;

    const inAuthGroup = segments[0] === 'auth';

    if (!session && !inAuthGroup) {
      router.replace('/auth/login');
    } else if (session && inAuthGroup) {
      router.replace('/(tabs)/food');
    }
  }, [session, segments, loading, router]);

  if (loading) {
    return <AuthLoadingScreen />;
  }

  return <Slot />;
}
