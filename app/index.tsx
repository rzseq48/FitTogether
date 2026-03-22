import { Redirect } from 'expo-router';
import { AuthLoadingScreen, useAuth } from '../lib/auth';

export default function Index() {
  const { loading, session } = useAuth();

  if (loading) {
    return <AuthLoadingScreen />;
  }

  if (session) {
    return <Redirect href="/(tabs)/food" />;
  }

  return <Redirect href="/auth/login" />;
}
