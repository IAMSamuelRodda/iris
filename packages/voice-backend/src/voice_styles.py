"""
Voice Styles for IRIS Native Client

Controls how IRIS communicates in voice mode:
- Response verbosity and thinking feedback
- Confirmation/clarification behavior
- TTS parameters (speech rate)

Port of packages/agent-core/src/voice-styles.ts for Python native client.
"""

from dataclasses import dataclass
from typing import Literal

# Type alias for voice style IDs
VoiceStyleId = Literal["normal", "formal", "concise", "immersive", "learning"]


@dataclass
class VoiceProperties:
    """Voice output parameters."""
    speech_rate: float  # TTS speed multiplier (0.8 = slower, 1.2 = faster)
    exaggeration: float  # Emotion intensity 0.0-1.0
    pause_tolerance: float  # Seconds before optional acknowledgment
    thinking_feedback: Literal["none", "minimal", "verbose"]


@dataclass
class VoiceStyle:
    """Voice style configuration."""
    id: VoiceStyleId
    name: str
    description: str
    prompt_modifier: str
    voice_properties: VoiceProperties


# ==============================================================================
# Style Definitions
# ==============================================================================

NORMAL_STYLE = VoiceStyle(
    id="normal",
    name="Normal",
    description="Balanced responses - silence is fine when you know what's happening",
    prompt_modifier="""
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
""",
    voice_properties=VoiceProperties(
        speech_rate=1.0,
        exaggeration=0.5,
        pause_tolerance=3.0,
        thinking_feedback="minimal",
    ),
)

FORMAL_STYLE = VoiceStyle(
    id="formal",
    name="Formal",
    description="Professional tone with minimal commentary",
    prompt_modifier="""
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
""",
    voice_properties=VoiceProperties(
        speech_rate=0.95,
        exaggeration=0.3,
        pause_tolerance=5.0,
        thinking_feedback="none",
    ),
)

CONCISE_STYLE = VoiceStyle(
    id="concise",
    name="Concise",
    description="Brief answers, minimal words",
    prompt_modifier="""
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
""",
    voice_properties=VoiceProperties(
        speech_rate=1.1,
        exaggeration=0.3,
        pause_tolerance=2.0,
        thinking_feedback="minimal",
    ),
)

IMMERSIVE_STYLE = VoiceStyle(
    id="immersive",
    name="Immersive",
    description="Roleplay-friendly with dramatic pacing",
    prompt_modifier="""
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
""",
    voice_properties=VoiceProperties(
        speech_rate=0.9,
        exaggeration=0.7,
        pause_tolerance=8.0,
        thinking_feedback="minimal",
    ),
)

LEARNING_STYLE = VoiceStyle(
    id="learning",
    name="Learning",
    description="Educational - explains concepts as it answers",
    prompt_modifier="""
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
""",
    voice_properties=VoiceProperties(
        speech_rate=0.9,
        exaggeration=0.5,
        pause_tolerance=2.0,
        thinking_feedback="verbose",
    ),
)


# ==============================================================================
# Style Registry
# ==============================================================================

VOICE_STYLES: dict[VoiceStyleId, VoiceStyle] = {
    "normal": NORMAL_STYLE,
    "formal": FORMAL_STYLE,
    "concise": CONCISE_STYLE,
    "immersive": IMMERSIVE_STYLE,
    "learning": LEARNING_STYLE,
}

# For GUI dropdown - list of (id, display_name)
VOICE_STYLE_OPTIONS: list[tuple[VoiceStyleId, str]] = [
    ("normal", "Normal - Balanced"),
    ("formal", "Formal - Professional"),
    ("concise", "Concise - Brief"),
    ("immersive", "Immersive - Roleplay"),
    ("learning", "Learning - Educational"),
]


# ==============================================================================
# Helper Functions
# ==============================================================================

def get_voice_style(style_id: VoiceStyleId) -> VoiceStyle:
    """Get a voice style by ID. Returns normal if not found."""
    return VOICE_STYLES.get(style_id, NORMAL_STYLE)


def get_voice_style_prompt(style_id: VoiceStyleId) -> str:
    """Get the prompt modifier for a voice style."""
    return get_voice_style(style_id).prompt_modifier


def get_voice_style_names() -> list[str]:
    """Get list of display names for GUI dropdown."""
    return [name for _, name in VOICE_STYLE_OPTIONS]


def get_style_id_from_name(display_name: str) -> VoiceStyleId:
    """Convert display name back to style ID."""
    for style_id, name in VOICE_STYLE_OPTIONS:
        if name == display_name:
            return style_id
    return "normal"
