import type { CoachIntent, CoachUserContext } from './types.js';

const DEFAULT_PROTEIN_TARGET = 120;
const DEFAULT_CALORIE_FLOOR = 1800;

const formatList = (items: string[]) => (items.length > 0 ? items.join(', ') : 'none logged');

export const summarizeUserContext = (context: CoachUserContext | null): string => {
  if (!context) {
    return 'No user context is available yet.';
  }

  return [
    `Calories today: ${context.todayCalories}`,
    `Protein today: ${context.todayProtein}g`,
    `Meals logged: ${context.todayMeals}`,
    `Workouts logged: ${context.todayWorkouts}`,
    `Recent meals: ${formatList(context.recentMeals)}`,
    `Recent workouts: ${formatList(context.recentWorkouts)}`,
  ].join('\n');
};

export const buildDeterministicAnalysis = (
  intent: CoachIntent,
  context: CoachUserContext | null
): string => {
  if (!context) {
    return 'The user has no tracked nutrition or workout context yet, so the response should stay general and ask for more logging when useful.';
  }

  const notes: string[] = [];

  if (intent === 'nutrition' || intent === 'progress') {
    if (context.todayProtein < DEFAULT_PROTEIN_TARGET) {
      notes.push(
        `Protein is below the default target by ${DEFAULT_PROTEIN_TARGET - context.todayProtein}g.`
      );
    } else {
      notes.push('Protein intake is at or above the default daily target.');
    }

    if (context.todayCalories < DEFAULT_CALORIE_FLOOR) {
      notes.push(
        `Calories are below the default floor by ${DEFAULT_CALORIE_FLOOR - context.todayCalories}.`
      );
    } else {
      notes.push('Calories are not below the default floor.');
    }
  }

  if (intent === 'workout' || intent === 'progress') {
    if (context.todayWorkouts === 0) {
      notes.push('No workouts have been logged today.');
    } else {
      notes.push(`The user has already logged ${context.todayWorkouts} workout session(s) today.`);
    }

    if (context.recentWorkouts.length > 0) {
      notes.push(`Recent training includes: ${formatList(context.recentWorkouts)}.`);
    }
  }

  if (intent === 'general') {
    notes.push('Blend training, recovery, and nutrition guidance into one concise answer.');
  }

  return notes.join(' ');
};
