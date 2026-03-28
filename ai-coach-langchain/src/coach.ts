import { ChatAnthropic } from '@langchain/anthropic';
import { StringOutputParser } from '@langchain/core/output_parsers';
import { RunnableSequence } from '@langchain/core/runnables';
import { z } from 'zod';
import { buildDeterministicAnalysis, summarizeUserContext } from './analysis.js';
import { coachPrompt, intentPrompt } from './prompts.js';
import type { CoachIntent, CoachReply, CoachRequest } from './types.js';

const intentSchema = z.object({
  intent: z.enum(['nutrition', 'workout', 'progress', 'general']),
});

const formatHistory = (history: CoachRequest['history'] = []) => {
  if (history.length === 0) {
    return 'No previous messages.';
  }

  return history.map((message) => `${message.role}: ${message.content}`).join('\n');
};

export interface AiCoachOptions {
  anthropicApiKey?: string;
  model?: string;
}

export class AiCoachService {
  private readonly model: ChatAnthropic;

  constructor(options: AiCoachOptions = {}) {
    this.model = new ChatAnthropic({
      apiKey: options.anthropicApiKey ?? process.env.ANTHROPIC_API_KEY,
      model: options.model ?? 'claude-3-5-haiku-latest',
      temperature: 0.4,
    });
  }

  async detectIntent(question: string): Promise<CoachIntent> {
    const classifier = intentPrompt.pipe(
      this.model.withStructuredOutput(intentSchema)
    );

    const result = await classifier.invoke({ question });
    return result.intent;
  }

  async generateCoachReply(request: CoachRequest): Promise<CoachReply> {
    const intent = await this.detectIntent(request.question);
    const contextSummary = summarizeUserContext(request.userContext);
    const analysisSummary = buildDeterministicAnalysis(intent, request.userContext);

    const chain = RunnableSequence.from([
      coachPrompt,
      this.model,
      new StringOutputParser(),
    ]);

    const text = await chain.invoke({
      question: request.question,
      history: formatHistory(request.history),
      contextSummary,
      analysisSummary,
    });

    return {
      text: text.trim(),
      intent,
      analysisSummary,
    };
  }
}

export const createAiCoach = (options?: AiCoachOptions) => new AiCoachService(options);
