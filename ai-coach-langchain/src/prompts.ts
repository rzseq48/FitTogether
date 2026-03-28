import { ChatPromptTemplate } from '@langchain/core/prompts';

export const intentPrompt = ChatPromptTemplate.fromMessages([
  [
    'system',
    [
      'You classify fitness coaching questions.',
      'Return one label only: nutrition, workout, progress, or general.',
    ].join(' '),
  ],
  [
    'human',
    'Question: {question}\n\nChoose the single best label.',
  ],
]);

export const coachPrompt = ChatPromptTemplate.fromMessages([
  [
    'system',
    [
      'You are FitTogether\'s AI coach.',
      'Be encouraging, practical, and specific.',
      'Use the supplied user context and deterministic analysis.',
      'Do not invent tracked data that is not provided.',
      'Keep the answer to 2 short paragraphs or a short paragraph plus bullet list.',
      'If the user asks for workout help, include a sensible next step.',
      'If the user asks for nutrition help, include a concrete meal or macro suggestion.',
    ].join(' '),
  ],
  [
    'human',
    [
      'User question: {question}',
      '',
      'Conversation history:',
      '{history}',
      '',
      'Tracked user context:',
      '{contextSummary}',
      '',
      'Deterministic coaching notes:',
      '{analysisSummary}',
    ].join('\n'),
  ],
]);
