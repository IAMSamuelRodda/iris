/**
 * IRIS Voice Service Types
 *
 * Shared types for voice processing pipeline.
 */

// ============================================================================
// WebSocket Message Types
// ============================================================================

/**
 * Messages sent from client to server.
 */
export type ClientMessage =
  | { type: "audio_start"; sampleRate: number; channels: number }
  | { type: "audio_chunk"; data: string } // Base64 encoded audio
  | { type: "audio_end" }
  | { type: "synthesize"; text: string; exaggeration?: number; speechRate?: number }
  | { type: "ping" };

/**
 * Messages sent from server to client.
 */
export type ServerMessage =
  | { type: "transcription"; text: string; language: string; isFinal: boolean }
  | { type: "audio_start"; sampleRate: number }
  | { type: "audio_chunk"; data: string } // Base64 encoded audio
  | { type: "audio_end"; durationSeconds: number }
  | { type: "error"; message: string; code?: string }
  | { type: "ready" }
  | { type: "pong" };

// ============================================================================
// Voice Backend Types
// ============================================================================

/**
 * Response from /transcribe endpoint.
 */
export interface TranscribeResponse {
  text: string;
  language: string;
  language_probability: number;
  duration_seconds: number;
}

/**
 * Request for /synthesize endpoint.
 */
export interface SynthesizeRequest {
  text: string;
  exaggeration?: number;
  cfg_weight?: number;
  speech_rate?: number;
}

/**
 * Health check response.
 */
export interface HealthResponse {
  status: string;
  stt_loaded: boolean;
  tts_loaded: boolean;
  device: string;
}

// ============================================================================
// Session Types
// ============================================================================

/**
 * Voice session state.
 */
export interface VoiceSession {
  id: string;
  userId: string;
  state: "idle" | "listening" | "processing" | "speaking";
  audioBuffer: Buffer[];
  startTime: number;
}

// ============================================================================
// Configuration
// ============================================================================

export interface VoiceServiceConfig {
  /** Port for WebSocket server */
  port: number;
  /** URL of the Python voice backend */
  backendUrl: string;
  /** Maximum audio chunk size in bytes */
  maxChunkSize: number;
  /** Session timeout in milliseconds */
  sessionTimeout: number;
}

export const DEFAULT_CONFIG: VoiceServiceConfig = {
  port: 8002,
  backendUrl: "http://localhost:8001",
  maxChunkSize: 32768, // 32KB
  sessionTimeout: 300000, // 5 minutes
};
