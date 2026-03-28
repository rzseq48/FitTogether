# AI Coach LangChain Workspace

This folder contains a standalone LangChain implementation for the FitTogether AI coach.

It is intentionally isolated from the Expo app so you can iterate on the coach backend without affecting the mobile build.

## What is included

- `src/coach.ts`: main LangChain coach pipeline
- `src/analysis.ts`: deterministic nutrition and workout analysis helpers
- `src/prompts.ts`: reusable prompt templates
- `src/types.ts`: shared coach request/response types
- `src/example.ts`: small local usage example

## Why this is separate

The current app uses `lib/ai.ts` and the Supabase Edge Function in `supabase/functions/ai-proxy/index.ts`.
This workspace gives you a cleaner server-side implementation path for replacing the direct prompt call with a LangChain orchestration layer.

## Install

From this folder:

```bash
npm install
```

## Environment

Set:

```bash
ANTHROPIC_API_KEY=your_key_here
```

## Run the example

```bash
npm run dev
```

## Suggested integration

1. Move the logic from `supabase/functions/ai-proxy/index.ts` into a server runtime that can import this package.
2. Call `generateCoachReply()` with the same `question` and `userContext` already sent by the mobile app.
3. Return the resulting text to the client exactly like the current proxy does.

## Notes

- This implementation uses LangChain with Anthropic.
- The current version focuses on coach chat, which is the cleanest first migration target.
- If you want, we can add a LangGraph version next for multi-step stateful coaching flows.
