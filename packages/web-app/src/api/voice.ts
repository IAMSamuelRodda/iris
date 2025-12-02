/**
 * Voice API Client
 *
 * WebSocket client for real-time voice interaction.
 * Handles audio capture, streaming, and playback.
 */

export type VoiceState = "idle" | "connecting" | "ready" | "recording" | "processing" | "speaking";

export interface VoiceClientOptions {
  wsUrl?: string;
  userId: string;
  onStateChange?: (state: VoiceState) => void;
  onTranscription?: (text: string) => void;
  onError?: (error: string) => void;
}

const WS_URL = import.meta.env.VITE_VOICE_WS_URL || "ws://localhost:8002";

export class VoiceClient {
  private ws: WebSocket | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private audioContext: AudioContext | null = null;
  private state: VoiceState = "idle";
  private options: VoiceClientOptions;

  constructor(options: VoiceClientOptions) {
    this.options = options;
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
      const url = `${this.options.wsUrl || WS_URL}?userId=${this.options.userId}`;
      this.ws = new WebSocket(url);

      this.ws.onopen = () => {
        console.log("[Voice] Connected");
      };

      this.ws.onmessage = (event) => {
        this.handleMessage(JSON.parse(event.data));
        if (this.state === "connecting") {
          this.setState("ready");
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
   */
  async startRecording(): Promise<void> {
    if (this.state !== "ready") {
      throw new Error("Not ready to record");
    }

    // Request microphone access
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 16000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });

    // Create audio context for resampling
    this.audioContext = new AudioContext({ sampleRate: 16000 });

    // Create MediaRecorder
    this.mediaRecorder = new MediaRecorder(stream, {
      mimeType: "audio/webm;codecs=opus",
    });

    const audioChunks: Blob[] = [];

    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data);
      }
    };

    this.mediaRecorder.onstop = async () => {
      // Convert to raw PCM
      const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
      const pcmData = await this.convertToPCM(audioBlob);

      // Send to server
      this.send({ type: "audio_end" });

      // Send audio data
      const base64 = btoa(
        Array.from(new Uint8Array(pcmData))
          .map((b) => String.fromCharCode(b))
          .join("")
      );

      // Note: In production, send chunks during recording for lower latency
      // For MVP, we send all at once after recording stops
      this.send({
        type: "audio_chunk",
        data: base64,
      });

      this.setState("processing");

      // Clean up
      stream.getTracks().forEach((track) => track.stop());
    };

    // Start recording
    this.send({
      type: "audio_start",
      sampleRate: 16000,
      channels: 1,
    });

    this.mediaRecorder.start(100); // Collect data every 100ms
    this.setState("recording");
  }

  /**
   * Stop recording audio.
   */
  stopRecording(): void {
    if (this.mediaRecorder?.state === "recording") {
      this.mediaRecorder.stop();
    }
  }

  /**
   * Request speech synthesis.
   */
  synthesize(text: string, exaggeration = 0.5): void {
    this.send({
      type: "synthesize",
      text,
      exaggeration,
    });
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
        break;

      case "audio_chunk":
        // Play audio chunk
        this.playAudioChunk(message.data as string, message.sampleRate as number);
        break;

      case "audio_end":
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

  private async convertToPCM(blob: Blob): Promise<ArrayBuffer> {
    if (!this.audioContext) {
      throw new Error("No audio context");
    }

    const arrayBuffer = await blob.arrayBuffer();
    const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);

    // Get raw PCM data (Float32)
    const channelData = audioBuffer.getChannelData(0);

    // Convert to Int16 PCM
    const pcmBuffer = new ArrayBuffer(channelData.length * 2);
    const pcmView = new DataView(pcmBuffer);

    for (let i = 0; i < channelData.length; i++) {
      const sample = Math.max(-1, Math.min(1, channelData[i]));
      pcmView.setInt16(i * 2, sample * 32767, true);
    }

    return pcmBuffer;
  }

  private playAudioChunk(base64Data: string, sampleRate = 24000): void {
    if (!this.audioContext) {
      this.audioContext = new AudioContext({ sampleRate });
    }

    // Decode base64 to Int16 PCM
    const binaryString = atob(base64Data);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    // Convert Int16 to Float32
    const int16View = new Int16Array(bytes.buffer);
    const floatData = new Float32Array(int16View.length);
    for (let i = 0; i < int16View.length; i++) {
      floatData[i] = int16View[i] / 32768;
    }

    // Create audio buffer and play
    const audioBuffer = this.audioContext.createBuffer(1, floatData.length, sampleRate);
    audioBuffer.getChannelData(0).set(floatData);

    const source = this.audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(this.audioContext.destination);
    source.start();
  }
}
