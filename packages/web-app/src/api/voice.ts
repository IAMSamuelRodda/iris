/**
 * Voice API Client
 *
 * WebSocket client for real-time voice interaction.
 * Handles audio capture, streaming, and playback.
 *
 * Protocol Support:
 * - Binary mode (default): Raw PCM audio, ~33% less overhead than base64
 * - JSON mode (fallback): Base64 encoded audio for compatibility
 */

export type VoiceState = "idle" | "connecting" | "ready" | "recording" | "processing" | "speaking";

export interface VoiceClientOptions {
  wsUrl?: string;
  userId: string;
  binaryMode?: boolean; // Default: true (use binary protocol)
  onStateChange?: (state: VoiceState) => void;
  onTranscription?: (text: string) => void;
  onSynthesisComplete?: (text: string) => void;
  onError?: (error: string) => void;
}

// Direct connection to Python voice-backend WebSocket (eliminates Node.js relay)
// Old: ws://localhost:8002 (Node.js voice-service)
// New: ws://localhost:8001/ws/voice (Python FastAPI direct)
const WS_URL = import.meta.env.VITE_VOICE_WS_URL || "ws://localhost:8001/ws/voice";

// Binary protocol message types (must match Python protocol.py)
const MessageType = {
  AUDIO_START: 0x01,
  AUDIO_CHUNK: 0x02,
  AUDIO_END: 0x03,
  TRANSCRIPTION: 0x04,
  LLM_CHUNK: 0x05,
  TTS_AUDIO: 0x06,
  ERROR: 0x07,
  READY: 0x08,
  DONE: 0x09,
  SYNTHESIZE: 0x0a,
  PING: 0x0b,
  PONG: 0x0c,
} as const;

// Binary protocol flags
const MessageFlags = {
  NONE: 0x00,
  IS_FINAL: 0x01,
  NEEDS_FOLLOWUP: 0x02,
} as const;

export class VoiceClient {
  private ws: WebSocket | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private audioContext: AudioContext | null = null;
  private playbackContext: AudioContext | null = null;
  private nextPlayTime = 0; // For scheduling audio chunks sequentially
  private state: VoiceState = "idle";
  private options: VoiceClientOptions;
  private pendingSynthesisText: string | null = null; // Track text being spoken
  private binaryMode: boolean; // Use binary protocol for lower overhead

  // Streaming audio capture (Phase 3)
  private captureStream: MediaStream | null = null;
  private captureSource: MediaStreamAudioSourceNode | null = null;
  private captureProcessor: ScriptProcessorNode | null = null;

  constructor(options: VoiceClientOptions) {
    this.options = options;
    this.binaryMode = options.binaryMode !== false; // Default: true
  }

  /**
   * Connect to the voice WebSocket server.
   */
  async connect(): Promise<void> {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    this.setState("connecting");

    return new Promise((resolve, reject) => {
      // Add binary=true query param if using binary protocol
      const baseUrl = this.options.wsUrl || WS_URL;
      const params = new URLSearchParams({ userId: this.options.userId });
      if (this.binaryMode) {
        params.set("binary", "true");
      }
      const url = `${baseUrl}?${params.toString()}`;
      this.ws = new WebSocket(url);

      // Enable binary mode for ArrayBuffer handling
      if (this.binaryMode) {
        this.ws.binaryType = "arraybuffer";
      }

      this.ws.onopen = () => {
        console.log("[Voice] Connected", this.binaryMode ? "(binary mode)" : "(JSON mode)");
      };

      this.ws.onmessage = (event) => {
        // Check state BEFORE handling message (handler may change state)
        const wasConnecting = this.state === "connecting";

        if (event.data instanceof ArrayBuffer) {
          // Binary protocol message
          this.handleBinaryMessage(event.data);
        } else {
          // JSON protocol message
          this.handleMessage(JSON.parse(event.data));
        }

        // Resolve connect() promise on first message
        if (wasConnecting) {
          resolve();
        }
      };

      this.ws.onerror = (error) => {
        console.error("[Voice] WebSocket error:", error);
        this.options.onError?.("Connection error");
        reject(error);
      };

      this.ws.onclose = () => {
        console.log("[Voice] Disconnected");
        this.setState("idle");
      };
    });
  }

  /**
   * Disconnect from the voice server.
   */
  disconnect(): void {
    this.stopRecording();
    this.ws?.close();
    this.ws = null;
    this.setState("idle");
  }

  /**
   * Start recording audio.
   *
   * Uses streaming PCM capture (ScriptProcessorNode) for real-time audio streaming.
   * Sends audio chunks every ~93ms (4096 samples @ 44100Hz) during recording,
   * reducing latency compared to batch send after recording.
   */
  async startRecording(): Promise<void> {
    if (this.state !== "ready") {
      throw new Error("Not ready to record");
    }

    // Request microphone access
    this.captureStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 16000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });

    // Create audio context (browser may give us different sample rate)
    this.audioContext = new AudioContext();
    const actualSampleRate = this.audioContext.sampleRate;

    // Send audio_start with actual sample rate
    if (this.binaryMode) {
      const metadata = JSON.stringify({ sampleRate: actualSampleRate, channels: 1 });
      this.sendBinary(MessageType.AUDIO_START, new TextEncoder().encode(metadata));
    } else {
      this.send({ type: "audio_start", sampleRate: actualSampleRate, channels: 1 });
    }

    // Create source from microphone
    this.captureSource = this.audioContext.createMediaStreamSource(this.captureStream);

    // Use ScriptProcessorNode to capture raw PCM samples
    // Buffer size 4096 = ~93ms at 44.1kHz, good balance of latency vs overhead
    const bufferSize = 4096;
    this.captureProcessor = this.audioContext.createScriptProcessor(bufferSize, 1, 1);

    this.captureProcessor.onaudioprocess = (event) => {
      if (this.state !== "recording") return;

      // Get Float32 PCM data from input buffer
      const inputData = event.inputBuffer.getChannelData(0);

      // Convert Float32 to Int16 PCM
      const pcmBuffer = new ArrayBuffer(inputData.length * 2);
      const pcmView = new DataView(pcmBuffer);
      for (let i = 0; i < inputData.length; i++) {
        const sample = Math.max(-1, Math.min(1, inputData[i]));
        pcmView.setInt16(i * 2, sample * 32767, true); // little-endian
      }

      // Send chunk immediately (streaming!)
      if (this.binaryMode) {
        this.sendBinary(MessageType.AUDIO_CHUNK, new Uint8Array(pcmBuffer));
      } else {
        const base64 = btoa(
          Array.from(new Uint8Array(pcmBuffer))
            .map((b) => String.fromCharCode(b))
            .join("")
        );
        this.send({ type: "audio_chunk", data: base64 });
      }
    };

    // Connect: microphone -> processor -> destination (required for processing)
    this.captureSource.connect(this.captureProcessor);
    this.captureProcessor.connect(this.audioContext.destination);

    this.setState("recording");
    console.log(`[Voice] Recording started (streaming PCM @ ${actualSampleRate}Hz)`);
  }

  /**
   * Stop recording audio.
   */
  stopRecording(): void {
    // Handle legacy MediaRecorder mode
    if (this.mediaRecorder?.state === "recording") {
      this.mediaRecorder.stop();
      return;
    }

    // Handle streaming capture mode
    if (this.state !== "recording") return;

    console.log("[Voice] Recording stopped, sending audio_end");

    // Disconnect audio nodes
    if (this.captureProcessor) {
      this.captureProcessor.disconnect();
      this.captureProcessor = null;
    }
    if (this.captureSource) {
      this.captureSource.disconnect();
      this.captureSource = null;
    }

    // Stop microphone
    if (this.captureStream) {
      this.captureStream.getTracks().forEach((track) => track.stop());
      this.captureStream = null;
    }

    // Close audio context
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }

    // Send audio_end (server already has all chunks)
    if (this.binaryMode) {
      this.sendBinary(MessageType.AUDIO_END);
    } else {
      this.send({ type: "audio_end" });
    }

    this.setState("processing");
  }

  /**
   * Request speech synthesis.
   */
  synthesize(text: string, exaggeration = 0.5, speechRate = 1.0): void {
    console.log("[Voice] Synthesize requested:", text.slice(0, 50) + (text.length > 50 ? "..." : ""));
    this.pendingSynthesisText = text;

    if (this.binaryMode) {
      // Binary mode: send synthesize request with JSON payload
      const payload = JSON.stringify({ text, exaggeration, speechRate });
      this.sendBinary(MessageType.SYNTHESIZE, new TextEncoder().encode(payload));
    } else {
      this.send({
        type: "synthesize",
        text,
        exaggeration,
        speechRate,
      });
    }
    this.setState("speaking");
  }

  /**
   * Get current state.
   */
  getState(): VoiceState {
    return this.state;
  }

  /**
   * Check if connected.
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Stop all audio playback immediately.
   * Clears the audio queue and resets to ready state.
   */
  stopAudio(): void {
    console.log("[Voice] Stopping audio playback");

    // Close and recreate playback context to stop all scheduled audio
    if (this.playbackContext) {
      this.playbackContext.close().catch(() => {});
      this.playbackContext = null;
    }

    // Reset playback timing
    this.nextPlayTime = 0;

    // Clear pending synthesis
    this.pendingSynthesisText = null;

    // Return to ready state if we were speaking
    if (this.state === "speaking") {
      this.setState("ready");
    }
  }

  /**
   * Stop everything - audio, recording, and reset state.
   * Use this for full interrupt (e.g., Escape key).
   */
  interruptAll(): void {
    console.log("[Voice] Full interrupt");
    this.stopRecording();
    this.stopAudio();
  }

  // Private methods

  private setState(state: VoiceState): void {
    this.state = state;
    this.options.onStateChange?.(state);
  }

  private send(message: object): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  /**
   * Send a binary protocol message.
   */
  private sendBinary(msgType: number, payload?: Uint8Array): void {
    if (this.ws?.readyState !== WebSocket.OPEN) return;

    // Header: 2 bytes (type + flags)
    const payloadLen = payload?.length ?? 0;
    const buffer = new ArrayBuffer(2 + payloadLen);
    const view = new DataView(buffer);

    view.setUint8(0, msgType);
    view.setUint8(1, MessageFlags.NONE);

    if (payload && payloadLen > 0) {
      new Uint8Array(buffer, 2).set(payload);
    }

    this.ws.send(buffer);
  }

  /**
   * Handle a binary protocol message.
   */
  private handleBinaryMessage(data: ArrayBuffer): void {
    const view = new DataView(data);
    if (data.byteLength < 2) return;

    const msgType = view.getUint8(0);
    // Byte 1 is flags (IS_FINAL, NEEDS_FOLLOWUP) - reserved for future use
    const payload = data.byteLength > 2 ? new Uint8Array(data, 2) : null;

    switch (msgType) {
      case MessageType.READY:
        this.setState("ready");
        break;

      case MessageType.TRANSCRIPTION:
        if (payload) {
          const text = new TextDecoder().decode(payload);
          this.options.onTranscription?.(text);
        }
        this.setState("ready");
        break;

      case MessageType.AUDIO_START:
        this.setState("speaking");
        // DON'T reset nextPlayTime - we want to queue audio sequentially
        break;

      case MessageType.TTS_AUDIO:
        // Play raw PCM audio (no base64 decode needed!)
        if (payload) {
          this.playRawAudio(payload);
        }
        break;

      case MessageType.AUDIO_END:
        // Log and callback with the text that was spoken
        if (this.pendingSynthesisText) {
          console.log(
            "[Voice] Synthesis complete:",
            this.pendingSynthesisText.slice(0, 50) +
              (this.pendingSynthesisText.length > 50 ? "..." : "")
          );
          this.options.onSynthesisComplete?.(this.pendingSynthesisText);
          this.pendingSynthesisText = null;
        }
        this.setState("ready");
        break;

      case MessageType.ERROR:
        if (payload) {
          const errorData = JSON.parse(new TextDecoder().decode(payload));
          this.options.onError?.(errorData.message);
        }
        this.setState("ready");
        break;

      case MessageType.PONG:
        // Heartbeat response
        break;
    }
  }

  private handleMessage(message: { type: string; [key: string]: unknown }): void {
    switch (message.type) {
      case "ready":
        this.setState("ready");
        break;

      case "transcription":
        this.options.onTranscription?.(message.text as string);
        this.setState("ready");
        break;

      case "audio_start":
        this.setState("speaking");
        // DON'T reset nextPlayTime - we want to queue audio sequentially
        // If there's already audio scheduled, the new audio will play after it
        // This fixes the overlap issue where acknowledgment + response play together
        break;

      case "audio_chunk":
        // Play audio chunk
        this.playAudioChunk(message.data as string, message.sampleRate as number);
        break;

      case "audio_end":
        // Log and callback with the text that was spoken
        if (this.pendingSynthesisText) {
          console.log("[Voice] Synthesis complete:", this.pendingSynthesisText.slice(0, 50) + (this.pendingSynthesisText.length > 50 ? "..." : ""));
          this.options.onSynthesisComplete?.(this.pendingSynthesisText);
          this.pendingSynthesisText = null;
        }
        this.setState("ready");
        break;

      case "error":
        this.options.onError?.(message.message as string);
        this.setState("ready");
        break;

      case "pong":
        // Heartbeat response
        break;
    }
  }

  /**
   * Play audio from base64-encoded PCM data (JSON mode).
   */
  private playAudioChunk(base64Data: string, sampleRate = 24000): void {
    // Decode base64 to Int16 PCM
    const binaryString = atob(base64Data);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    // Convert to Int16 view and play
    this.playPcmBytes(new Int16Array(bytes.buffer), sampleRate);
  }

  /**
   * Play raw PCM audio from Uint8Array (binary mode).
   * Eliminates base64 decode overhead (~33% savings).
   */
  private playRawAudio(pcmData: Uint8Array, sampleRate = 24000): void {
    // Create Int16Array view of the PCM data
    // Note: Uint8Array may not be aligned, so we need to copy
    const alignedBuffer = new ArrayBuffer(pcmData.length);
    new Uint8Array(alignedBuffer).set(pcmData);
    const int16Data = new Int16Array(alignedBuffer);

    this.playPcmBytes(int16Data, sampleRate);
  }

  /**
   * Play Int16 PCM audio samples.
   * Shared by both JSON (base64) and binary modes.
   */
  private playPcmBytes(int16Data: Int16Array, sampleRate: number): void {
    // Use separate playback context at correct sample rate
    if (!this.playbackContext || this.playbackContext.sampleRate !== sampleRate) {
      this.playbackContext?.close();
      this.playbackContext = new AudioContext({ sampleRate });
      this.nextPlayTime = 0;
    }

    // Convert Int16 to Float32
    const floatData = new Float32Array(int16Data.length);
    for (let i = 0; i < int16Data.length; i++) {
      floatData[i] = int16Data[i] / 32768;
    }

    // Create audio buffer
    const audioBuffer = this.playbackContext.createBuffer(1, floatData.length, sampleRate);
    audioBuffer.getChannelData(0).set(floatData);

    // Schedule chunk to play after previous chunks (sequential playback)
    const currentTime = this.playbackContext.currentTime;
    if (this.nextPlayTime < currentTime) {
      this.nextPlayTime = currentTime;
    }

    const source = this.playbackContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(this.playbackContext.destination);
    source.start(this.nextPlayTime);

    // Update next play time for subsequent chunks
    this.nextPlayTime += audioBuffer.duration;
  }
}

// =============================================================================
// Voice Management API (HTTP calls to voice-backend)
// =============================================================================

const VOICE_API_URL = import.meta.env.VITE_VOICE_API_URL || "http://localhost:8001";

export interface VoicesResponse {
  voices: string[];
  current: string;
}

export interface VoiceSelectResponse {
  success: boolean;
  voice: string;
  message: string;
}

export interface WarmupResponse {
  ready: boolean;
  voice: string;
  warmup_time_ms: number;
}

/**
 * Get list of available TTS voices.
 */
export async function getAvailableVoices(): Promise<VoicesResponse> {
  const response = await fetch(`${VOICE_API_URL}/api/voices`);
  if (!response.ok) {
    throw new Error(`Failed to get voices: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Select a voice and warm it up.
 * This may take a few seconds on first use.
 */
export async function selectVoice(voiceName: string): Promise<VoiceSelectResponse> {
  const response = await fetch(`${VOICE_API_URL}/api/voice/select`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ voice: voiceName }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `Failed to select voice: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Warmup the current voice (call on app startup).
 */
export async function warmupVoice(): Promise<WarmupResponse> {
  const response = await fetch(`${VOICE_API_URL}/api/warmup`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(`Failed to warmup: ${response.statusText}`);
  }
  return response.json();
}
