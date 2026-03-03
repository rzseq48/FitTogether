import fs from 'node:fs';
import path from 'node:path';

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
    const value = trimmed.slice(eqIndex + 1).trim().replace(/^['\"]|['\"]$/g, '');
    if (!(key in process.env)) process.env[key] = value;
  }
}

function nowMs() {
  return Number(process.hrtime.bigint()) / 1e6;
}

async function timedFetch(name, url, init) {
  const start = nowMs();
  try {
    const res = await fetch(url, init);
    const end = nowMs();
    return {
      name,
      status: res.status,
      statusText: res.statusText,
      ms: end - start,
      ok: res.ok,
      error: null,
    };
  } catch (error) {
    const end = nowMs();
    return {
      name,
      status: 0,
      statusText: 'FETCH_FAILED',
      ms: end - start,
      ok: false,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}

function fmt(ms) {
  return `${ms.toFixed(2)} ms`;
}

async function main() {
  loadDotEnvIfPresent();

  const supabaseUrl = (process.env.EXPO_PUBLIC_SUPABASE_URL || '').trim().replace(/\/$/, '');
  const supabaseAnonKey = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY || '';
  const accessToken = process.env.SUPABASE_ACCESS_TOKEN || '';

  if (!supabaseUrl || !supabaseAnonKey) {
    console.error('Missing EXPO_PUBLIC_SUPABASE_URL or EXPO_PUBLIC_SUPABASE_ANON_KEY');
    process.exit(1);
  }

  const dayStart = new Date();
  dayStart.setHours(0, 0, 0, 0);
  const dayEnd = new Date(dayStart);
  dayEnd.setDate(dayEnd.getDate() + 1);

  const baseHeaders = {
    apikey: supabaseAnonKey,
    Authorization: `Bearer ${accessToken || supabaseAnonKey}`,
    Accept: 'application/json',
  };

  const results = [];

  // Endpoint used in the app session check path.
  results.push(
    await timedFetch('Auth user check', `${supabaseUrl}/auth/v1/user`, {
      headers: baseHeaders,
    })
  );

  // More direct approximation of the food page list query.
  const foodLogsUrl =
    `${supabaseUrl}/rest/v1/food_logs?select=*` +
    `&meal_time=gte.${encodeURIComponent(dayStart.toISOString())}` +
    `&meal_time=lt.${encodeURIComponent(dayEnd.toISOString())}` +
    `&order=meal_time.desc&limit=25`;

  results.push(
    await timedFetch('Food logs query', foodLogsUrl, {
      headers: baseHeaders,
    })
  );

  const valid = results.filter((r) => Number.isFinite(r.ms));
  const avg = valid.reduce((sum, r) => sum + r.ms, 0) / valid.length;
  const min = Math.min(...valid.map((r) => r.ms));
  const max = Math.max(...valid.map((r) => r.ms));

  console.log('\nFood page backend timing benchmark');
  console.log(`Timestamp: ${new Date().toISOString()}`);
  console.log(`Auth mode: ${accessToken ? 'User token' : 'Anon key only'}`);

  for (const r of results) {
    console.log(`- ${r.name}: ${fmt(r.ms)} (${r.status} ${r.statusText})`);
    if (r.error) {
      console.log(`  error: ${r.error}`);
    }
  }

  const failed = results.filter((r) => r.error);
  if (failed.length > 0) {
    console.log(`Summary: ${failed.length}/${results.length} request(s) failed.`);
    process.exit(1);
  }

  console.log(`Summary: avg=${fmt(avg)}, min=${fmt(min)}, max=${fmt(max)}`);

  if (!accessToken) {
    console.log('\nNote: Run with SUPABASE_ACCESS_TOKEN set to measure true signed-in food page timings.');
  }
}

await main();
