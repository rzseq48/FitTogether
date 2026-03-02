import fs from 'node:fs';
import path from 'node:path';
import { createClient } from '@supabase/supabase-js';

function loadDotEnvIfPresent() {
  const envPath = path.resolve(process.cwd(), '.env');
  if (!fs.existsSync(envPath)) return;

  const raw = fs.readFileSync(envPath, 'utf8');
  for (const line of raw.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eqIndex = trimmed.indexOf('=');
    if (eqIndex === -1) continue;
    const key = trimmed.slice(0, eqIndex).trim();
    const value = trimmed.slice(eqIndex + 1).trim().replace(/^['"]|['"]$/g, '');
    if (!(key in process.env)) process.env[key] = value;
  }
}

function fail(message) {
  console.error(`\nSupabase connection test failed: ${message}`);
  process.exit(1);
}

async function main() {
  loadDotEnvIfPresent();

  const supabaseUrl = process.env.EXPO_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl) fail('Missing EXPO_PUBLIC_SUPABASE_URL in environment or .env.');
  if (!supabaseAnonKey) fail('Missing EXPO_PUBLIC_SUPABASE_ANON_KEY in environment or .env.');

  let normalizedUrl = supabaseUrl.trim();
  if (normalizedUrl.endsWith('/')) normalizedUrl = normalizedUrl.slice(0, -1);

  try {
    new URL(normalizedUrl);
  } catch {
    fail('EXPO_PUBLIC_SUPABASE_URL is not a valid URL.');
  }

  const supabase = createClient(normalizedUrl, supabaseAnonKey);

  try {
    const authRes = await fetch(`${normalizedUrl}/auth/v1/settings`, {
      headers: { apikey: supabaseAnonKey },
    });
    if (!authRes.ok) {
      fail(`Auth settings endpoint returned ${authRes.status} ${authRes.statusText}.`);
    }

    const restRes = await fetch(`${normalizedUrl}/rest/v1/`, {
      headers: {
        apikey: supabaseAnonKey,
        Authorization: `Bearer ${supabaseAnonKey}`,
      },
    });
    if (!restRes.ok) {
      fail(`REST endpoint returned ${restRes.status} ${restRes.statusText}.`);
    }

    // Lightweight sanity check that client can be instantiated without runtime errors.
    if (!supabase) fail('Supabase client could not be created.');

    console.log('\nSupabase connection OK.');
    console.log(`Project URL: ${normalizedUrl}`);
    console.log('Auth and REST endpoints are reachable with anon key.');
  } catch (error) {
    if (error instanceof Error) {
      const cause =
        error.cause && typeof error.cause === 'object'
          ? JSON.stringify(error.cause)
          : String(error.cause ?? '');
      fail(cause ? `${error.message} | cause: ${cause}` : error.message);
    }
    fail(String(error));
  }
}

await main();
