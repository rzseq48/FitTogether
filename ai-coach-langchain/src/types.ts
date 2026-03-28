export interface CoachUserContext {
  todayCalories: number;
  todayProtein: number;
  todayMeals: number;
  todayWorkouts: number;
  recentMeals: string[];
  recentWorkouts: string[];
}

export interface CoachMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface CoachRequest {
  question: string;
  userContext: CoachUserContext | null;
  history?: CoachMessage[];
}

export interface CoachReply {
  text: string;
  intent: CoachIntent;
  analysisSummary: string;
}

export type CoachIntent = 'nutrition' | 'workout' | 'progress' | 'general';
