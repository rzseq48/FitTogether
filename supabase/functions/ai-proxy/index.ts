import { serve } from 'https://deno.land/std@0.224.0/http/server.ts';
import { createClient } from 'jsr:@supabase/supabase-js@2';

const ANTHROPIC_API_URL = 'https://api.anthropic.com/v1/messages';
const ANTHROPIC_MODEL = 'claude-3-haiku-20240307';

type AiTask = 'chat_coach' | 'workout_recommendation' | 'food_analysis';

interface ProxyRequest {
  task: AiTask;
  payload: Record<string, unknown>;
}

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });

const getBearerToken = (authorizationHeader: string | null) => {
  if (!authorizationHeader) return null;

  const [scheme, token] = authorizationHeader.split(' ');
  if (scheme?.toLowerCase() !== 'bearer' || !token) {
    return null;
  }

  return token;
};

const authenticateRequest = async (req: Request) => {
  const supabaseUrl = Deno.env.get('SUPABASE_URL');
  const supabaseAnonKey = Deno.env.get('SUPABASE_ANON_KEY');

  if (!supabaseUrl || !supabaseAnonKey) {
    throw new Error('SUPABASE_URL or SUPABASE_ANON_KEY is not configured');
  }

  const accessToken = getBearerToken(req.headers.get('Authorization'));
  if (!accessToken) {
    return { error: json(401, { error: 'Missing or invalid Authorization header' }) };
  }

  const supabase = createClient(supabaseUrl, supabaseAnonKey, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
    global: {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    },
  });

  const {
    data: { user },
    error,
  } = await supabase.auth.getUser(accessToken);

  if (error || !user) {
    return { error: json(401, { error: 'Unauthorized' }) };
  }

  return { user };
};

const anthropicRequest = async (apiKey: string, body: Record<string, unknown>) => {
  const response = await fetch(ANTHROPIC_API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify(body),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const details = typeof data?.error?.message === 'string' ? data.error.message : 'Unknown Anthropic error';
    throw new Error(`Anthropic API error: ${details}`);
  }

  const text = data?.content?.[0]?.text;
  if (typeof text !== 'string' || !text.trim()) {
    throw new Error('Anthropic response missing text content');
  }

  return text.trim();
};

const buildPrompt = (task: AiTask, payload: Record<string, unknown>) => {
  if (task === 'chat_coach') {
    const question = String(payload.question ?? '');
    const ctx = (payload.userContext ?? {}) as Record<string, unknown>;
    return {
      max_tokens: 500,
      messages: [
        {
          role: 'user',
          content: `You are a knowledgeable fitness and nutrition coach. Be helpful, encouraging, and specific.

User's context today:
- Calories consumed: ${Number(ctx.todayCalories ?? 0)}
- Protein consumed: ${Number(ctx.todayProtein ?? 0)}g
- Meals logged: ${Number(ctx.todayMeals ?? 0)}
- Workouts completed: ${Number(ctx.todayWorkouts ?? 0)}
- Recent meals: ${Array.isArray(ctx.recentMeals) ? ctx.recentMeals.join(', ') : 'None'}
- Recent workouts: ${Array.isArray(ctx.recentWorkouts) ? ctx.recentWorkouts.join(', ') : 'None'}

User question: ${question}

Provide a helpful, personalized response in 2-3 short paragraphs.`,
        },
      ],
    };
  }

  if (task === 'workout_recommendation') {
    return {
      max_tokens: 300,
      messages: [
        {
          role: 'user',
          content: `Based on today's nutrition:
- Calories consumed: ${Number(payload.totalCalories ?? 0)}
- Protein consumed: ${Number(payload.totalProtein ?? 0)}g
- Workouts completed today: ${Number(payload.workoutsCompleted ?? 0)}

Provide a brief workout recommendation (2-3 sentences), including 3-4 specific exercises with sets/reps when possible.
Keep it concise and actionable.`,
        },
      ],
    };
  }

  const base64Image = String(payload.base64Image ?? '');
  const mediaType = String(payload.mediaType ?? 'image/jpeg');

  if (!base64Image) {
    throw new Error('Missing base64 image payload');
  }

  return {
    max_tokens: 700,
    messages: [
      {
        role: 'user',
        content: [
          {
            type: 'image',
            source: {
              type: 'base64',
              media_type: mediaType,
              data: base64Image,
            },
          },
          {
            type: 'text',
            text: `Analyze this food image and respond ONLY with valid JSON:
{
  "meal_name": "name of the dish",
  "calories": number,
  "protein": number,
  "carbs": number,
  "fat": number
}`,
          },
        ],
      },
    ],
  };
};

serve(async (req) => {
  if (req.method !== 'POST') {
    return json(405, { error: 'Method not allowed' });
  }

  const authResult = await authenticateRequest(req).catch((error) => ({
    error: json(500, { error: error instanceof Error ? error.message : 'Authentication setup failed' }),
  }));
  if (authResult.error) {
    return authResult.error;
  }

  const apiKey = Deno.env.get('ANTHROPIC_API_KEY');
  if (!apiKey) {
    return json(500, { error: 'ANTHROPIC_API_KEY is not configured' });
  }

  const body = (await req.json().catch(() => null)) as ProxyRequest | null;
  if (!body?.task || !body.payload) {
    return json(400, { error: 'Invalid request body' });
  }

  if (!['chat_coach', 'workout_recommendation', 'food_analysis'].includes(body.task)) {
    return json(400, { error: 'Unsupported task' });
  }

  try {
    const prompt = buildPrompt(body.task, body.payload);
    const text = await anthropicRequest(apiKey, {
      model: ANTHROPIC_MODEL,
      ...prompt,
    });
    return json(200, { text });
  } catch (error) {
    console.error('AI proxy error:', error);
    return json(502, { error: error instanceof Error ? error.message : 'AI proxy failed' });
  }
});
