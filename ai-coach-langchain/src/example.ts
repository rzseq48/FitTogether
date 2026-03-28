import { createAiCoach } from './coach.js';

const coach = createAiCoach();

const run = async () => {
  const response = await coach.generateCoachReply({
    question: 'Should I eat more protein today if I want to build muscle?',
    userContext: {
      todayCalories: 1450,
      todayProtein: 72,
      todayMeals: 2,
      todayWorkouts: 1,
      recentMeals: ['oats with milk', 'rice and paneer curry'],
      recentWorkouts: ['push day 4x8 bench press', 'dumbbell shoulder press 3x10'],
    },
    history: [
      {
        role: 'assistant',
        content: 'How are you feeling after your workout today?',
      },
      {
        role: 'user',
        content: 'Pretty good, just unsure what to eat tonight.',
      },
    ],
  });

  console.log(response);
};

run().catch((error) => {
  console.error(error);
  process.exit(1);
});
