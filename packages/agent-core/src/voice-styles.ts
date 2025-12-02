/**
 * Voice Styles for IRIS
 *
 * Controls how IRIS communicates in voice mode:
 * - Response verbosity and thinking feedback
 * - Confirmation/clarification behavior
 * - TTS parameters (speech rate, emotion)
 *
 * Inspired by pip-by-arc-forge's response style system.
 */

// ============================================================================
// Types
// ============================================================================

export type VoiceStyleId = "normal" | "formal" | "concise" | "immersive" | "learning";

/**
 * Voice style configuration.
 * Controls both the LLM prompt behavior and TTS output parameters.
 */
export interface VoiceStyle {
  id: VoiceStyleId;
  name: string;
  description: string;
  /** Prompt instructions injected into system prompt */
  promptModifier: string;
  /** Voice output parameters */
  voiceProperties: {
    /** TTS speech rate multiplier (0.8 = slower, 1.2 = faster) */
    speechRate: number;
    /** Chatterbox exaggeration parameter (emotion intensity 0.0-1.0) */
    exaggeration: number;
    /** Seconds of silence before optional acknowledgment */
    pauseTolerance: number;
    /** How much thinking/progress to vocalize */
    thinkingFeedback: "none" | "minimal" | "verbose";
  };
  /** Conversation flow settings */
  conversationFlow: {
    /** Whether to paraphrase complex requests for confirmation */
    confirmUnderstanding: boolean;
    /** Seconds of silence to treat as implicit agreement */
    implicitConfirmationDelay: number;
    /** Whether to announce delegation ("Let me check the logs...") */
    announceDelegation: boolean;
  };
}

// ============================================================================
// Style Definitions
// ============================================================================

/**
 * Normal: Balanced responses with natural conversation flow.
 * Silence is fine when the user knows what's happening.
 */
export const normalVoiceStyle: VoiceStyle = {
  id: "normal",
  name: "Normal",
  description: "Balanced responses - silence is fine when you know what's happening",
  promptModifier: `
## Voice Conversation Style: Normal

You are having a natural voice conversation. Apply these behaviors:

### Understanding Check (Complex Requests)
When the user makes a complex or ambiguous request:
1. Paraphrase your understanding naturally: "So you're wondering if the explosion affected your ship's power?"
2. Pause briefly (2-3 seconds) for confirmation or correction
3. If silence: proceed with your understanding
4. If correction: acknowledge and adjust

### Delegation Announcement
When you need to do deeper analysis or use tools:
- Briefly state your intent: "Let me check the system logs for that."
- Then proceed without waiting for acknowledgment
- Don't narrate every tool use, just major actions

### Response Delivery
- Speak naturally, not in lists or bullet points
- Max 2-3 sentences per turn unless explaining something complex
- Round numbers for speech ("about 2 SOL" not "2.3847 SOL")
- Silence during processing is acceptable - user sees visual progress

### Pacing
- Normal speaking pace
- Natural pauses between thoughts
- Don't rush, but don't over-explain
`,
  voiceProperties: {
    speechRate: 1.0,
    exaggeration: 0.5,
    pauseTolerance: 3.0,
    thinkingFeedback: "minimal",
  },
  conversationFlow: {
    confirmUnderstanding: true,
    implicitConfirmationDelay: 3.0,
    announceDelegation: true,
  },
};

/**
 * Formal: Professional tone with minimal feedback.
 * Suitable for streaming or business contexts.
 */
export const formalVoiceStyle: VoiceStyle = {
  id: "formal",
  name: "Formal",
  description: "Professional tone with minimal commentary",
  promptModifier: `
## Voice Conversation Style: Formal

You are a professional assistant. Apply these behaviors:

### Communication
- Use professional, clear language
- Complete sentences, no casual contractions
- State facts directly without hedging
- Don't paraphrase requests - proceed directly if clear

### Processing
- Work silently - don't announce what you're doing
- Provide results when ready
- If clarification needed, ask once precisely

### Response Delivery
- Measured pace, clear enunciation
- One topic per response
- Avoid filler words and casual acknowledgments
`,
  voiceProperties: {
    speechRate: 0.95,
    exaggeration: 0.3,
    pauseTolerance: 5.0,
    thinkingFeedback: "none",
  },
  conversationFlow: {
    confirmUnderstanding: false,
    implicitConfirmationDelay: 5.0,
    announceDelegation: false,
  },
};

/**
 * Concise: Minimal words, fast answers.
 * For experienced users who want quick information.
 */
export const conciseVoiceStyle: VoiceStyle = {
  id: "concise",
  name: "Concise",
  description: "Brief answers, minimal words",
  promptModifier: `
## Voice Conversation Style: Concise

Be extremely brief. Apply these behaviors:

### Communication
- Lead with the answer, skip preamble
- Maximum 1-2 sentences
- Numbers and facts only
- No "let me check" or "I'll look into that" - just do it

### Acknowledgment
- Quick acknowledgment for complex requests: "Got it."
- Then proceed silently
- Results only when ready

### Examples
Good: "Fleet's at 70% fuel, 3 days left."
Bad: "Let me check your fleet status for you. Looking at the data, it appears..."
`,
  voiceProperties: {
    speechRate: 1.1,
    exaggeration: 0.3,
    pauseTolerance: 2.0,
    thinkingFeedback: "minimal",
  },
  conversationFlow: {
    confirmUnderstanding: false,
    implicitConfirmationDelay: 2.0,
    announceDelegation: false,
  },
};

/**
 * Immersive: Roleplay-friendly with dramatic pacing.
 * Extended silence tolerance for atmosphere.
 */
export const immersiveVoiceStyle: VoiceStyle = {
  id: "immersive",
  name: "Immersive",
  description: "Roleplay-friendly with dramatic pacing",
  promptModifier: `
## Voice Conversation Style: Immersive

You are IRIS, mission control for a Star Atlas commander. Stay in character.

### Character Voice
- Speak as a real person in this universe
- Reference game lore naturally
- Use terms like "Commander", fleet names, sector names
- Show genuine investment in the commander's success

### Dramatic Pacing
- Take your time with important information
- Silence can build tension - use it intentionally
- Don't rush bad news or critical alerts

### Conversation
- React naturally to what the commander says
- Express appropriate concern, excitement, or caution
- "That explosion near the mining outpost... I'm pulling up the logs now. This might take a moment."

### Processing
- Announce significant actions in character
- Long silence is acceptable - you're "working on it"
- Results delivered with appropriate gravity or relief
`,
  voiceProperties: {
    speechRate: 0.9,
    exaggeration: 0.7,
    pauseTolerance: 8.0,
    thinkingFeedback: "minimal",
  },
  conversationFlow: {
    confirmUnderstanding: true,
    implicitConfirmationDelay: 4.0,
    announceDelegation: true,
  },
};

/**
 * Learning: Educational mode with explanations.
 * Teaches concepts as it answers.
 */
export const learningVoiceStyle: VoiceStyle = {
  id: "learning",
  name: "Learning",
  description: "Educational - explains concepts as it answers",
  promptModifier: `
## Voice Conversation Style: Learning

You are teaching the user about Star Atlas and their operations.

### Teaching Approach
- Explain the "why" behind information
- Define terms when first used
- Connect new info to what they already know
- "Your fleet's fuel is at 70% - that's actually good for a mining operation because..."

### Thinking Aloud
- Share your reasoning process
- "I'm checking the transaction history to see if... yes, here it is."
- Announce what you're looking for and why

### Confirmation
- Paraphrase to ensure understanding
- "So you want to know why the ship lost power - let me walk through what I'm checking."
- Welcome corrections and questions

### Response Delivery
- Slightly slower pace for clarity
- Break complex info into digestible pieces
- Pause for questions: "Does that make sense so far?"
`,
  voiceProperties: {
    speechRate: 0.9,
    exaggeration: 0.5,
    pauseTolerance: 2.0,
    thinkingFeedback: "verbose",
  },
  conversationFlow: {
    confirmUnderstanding: true,
    implicitConfirmationDelay: 3.0,
    announceDelegation: true,
  },
};

// ============================================================================
// Style Registry
// ============================================================================

export const voiceStyles: Record<VoiceStyleId, VoiceStyle> = {
  normal: normalVoiceStyle,
  formal: formalVoiceStyle,
  concise: conciseVoiceStyle,
  immersive: immersiveVoiceStyle,
  learning: learningVoiceStyle,
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get a voice style by ID.
 * Returns normal style if ID not found.
 */
export function getVoiceStyle(styleId: VoiceStyleId): VoiceStyle {
  return voiceStyles[styleId] || normalVoiceStyle;
}

/**
 * Get the prompt modifier for a voice style.
 * Returns empty string for styles that don't modify the prompt.
 */
export function buildVoiceStylePrompt(styleId: VoiceStyleId): string {
  const style = getVoiceStyle(styleId);
  return style.promptModifier;
}

/**
 * Get all available voice styles for UI display.
 */
export function getVoiceStyleOptions(): Array<{
  id: VoiceStyleId;
  name: string;
  description: string;
  voiceProperties: {
    speechRate: number;
    exaggeration: number;
  };
}> {
  return Object.values(voiceStyles).map((style) => ({
    id: style.id,
    name: style.name,
    description: style.description,
    voiceProperties: {
      speechRate: style.voiceProperties.speechRate,
      exaggeration: style.voiceProperties.exaggeration,
    },
  }));
}

/**
 * Validate a style ID.
 */
export function isValidVoiceStyleId(id: string): id is VoiceStyleId {
  return id in voiceStyles;
}
