import { supabase } from './supabase';

interface AiProxyResponse {
  text?: string;
}

interface UserContext {
  todayCalories: number;
  todayProtein: number;
  todayMeals: number;
  todayWorkouts: number;
  recentMeals: string[];
  recentWorkouts: string[];
}

export interface FoodAnalysis {
  meal_name: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
}

const MAX_ATTEMPTS = 3;
const RETRY_DELAY_MS = 500;

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const invokeAiProxy = async (body: Record<string, unknown>): Promise<string> => {
  let lastError: unknown;

  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt += 1) {
    const { data, error } = await supabase.functions.invoke<AiProxyResponse>('ai-proxy', {
      body,
    });

    if (!error && typeof data?.text === 'string' && data.text.trim().length > 0) {
      return data.text.trim();
    }

    lastError = error ?? new Error('Invalid AI proxy response');
    if (attempt < MAX_ATTEMPTS) {
      await delay(RETRY_DELAY_MS * attempt);
    }
  }

  throw lastError instanceof Error ? lastError : new Error('AI request failed');
};

const parseNutritionJson = (text: string): FoodAnalysis => {
  let parsedText = text.trim();

  // Handle fenced markdown JSON blocks from model output.
  if (parsedText.startsWith('```')) {
    parsedText = parsedText
      .replace(/^```(?:json)?\s*/i, '')
      .replace(/\s*```$/, '')
      .trim();
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(parsedText);
  } catch {
    throw new Error('AI returned non-JSON nutrition output');
  }

  if (typeof parsed !== 'object' || parsed === null) {
    throw new Error('AI returned invalid nutrition payload');
  }

  const candidate = parsed as Partial<FoodAnalysis>;
  const normalized: FoodAnalysis = {
    meal_name: String(candidate.meal_name ?? '').trim(),
    calories: Number(candidate.calories),
    protein: Number(candidate.protein),
    carbs: Number(candidate.carbs),
    fat: Number(candidate.fat),
  };

  const hasInvalidNumbers = [normalized.calories, normalized.protein, normalized.carbs, normalized.fat]
    .some((value) => !Number.isFinite(value) || value < 0);

  if (!normalized.meal_name || hasInvalidNumbers) {
    throw new Error('AI returned incomplete nutrition values');
  }

  return normalized;
};

export const getCoachReply = async (question: string, userContext: UserContext | null): Promise<string> => {
  return invokeAiProxy({
    task: 'chat_coach',
    payload: {
      question,
      userContext,
    },
  });
};

export const getWorkoutRecommendation = async (
  totalCalories: number,
  totalProtein: number,
  workoutsCompleted: number
): Promise<string> => {
  return invokeAiProxy({
    task: 'workout_recommendation',
    payload: {
      totalCalories,
      totalProtein,
      workoutsCompleted,
    },
  });
};

export const analyzeFoodImage = async (base64Image: string, mediaType = 'image/jpeg'): Promise<FoodAnalysis> => {
  const text = await invokeAiProxy({
    task: 'food_analysis',
    payload: {
      base64Image,
      mediaType,
    },
  });

  return parseNutritionJson(text);
};
