/**
 * IRIS Voice WebSocket Server
 *
 * Handles real-time audio streaming for voice interaction.
 * Bridges browser WebSocket connections to the Python voice backend.
 *
 * Protocol:
 * 1. Client sends audio_start → server acknowledges with ready
 * 2. Client streams audio_chunk messages (base64 encoded PCM)
 * 3. Client sends audio_end → server transcribes and responds
 * 4. Server sends transcription → client can request synthesis
 */

import { WebSocket, WebSocketServer } from "ws";
import type { IncomingMessage, Server } from "http";
import { VoiceClient } from "./voice-client.js";
import type { ClientMessage, ServerMessage, VoiceSession, VoiceServiceConfig } from "./types.js";
import { randomUUID } from "crypto";

export class VoiceWebSocketServer {
  private wss: WebSocketServer;
  private voiceClient: VoiceClient;
  private sessions: Map<WebSocket, VoiceSession> = new Map();
  private config: VoiceServiceConfig;

  constructor(config: Partial<VoiceServiceConfig> = {}) {
    const defaults: VoiceServiceConfig = {
      port: 8002,
      backendUrl: "http://localhost:8001",
      maxChunkSize: 1048576, // 1MB - MVP sends all audio at once
      sessionTimeout: 300000,
    };

    this.config = { ...defaults, ...config };
    this.voiceClient = new VoiceClient({ backendUrl: this.config.backendUrl });

    this.wss = new WebSocketServer({
      port: this.config.port,
      perMessageDeflate: false, // Disable compression for lower latency
    });

    this.wss.on("connection", this.handleConnection.bind(this));
    this.wss.on("error", (error) => {
      console.error("[VoiceWS] Server error:", error);
    });

    console.log(`[VoiceWS] Server listening on port ${this.config.port}`);
  }

  /**
   * Attach to an existing HTTP server instead of creating a new one.
   */
  static attachToServer(server: Server, config: Partial<VoiceServiceConfig> = {}): VoiceWebSocketServer {
    const instance = new VoiceWebSocketServer({ ...config, port: 0 });

    // Close the auto-created server and attach to the provided one
    instance.wss.close();
    instance.wss = new WebSocketServer({
      server,
      path: "/voice",
      perMessageDeflate: false,
    });

    instance.wss.on("connection", instance.handleConnection.bind(instance));
    instance.wss.on("error", (error) => {
      console.error("[VoiceWS] Server error:", error);
    });

    console.log("[VoiceWS] Attached to HTTP server on /voice");
    return instance;
  }

  private handleConnection(ws: WebSocket, request: IncomingMessage): void {
    const sessionId = randomUUID();
    const userId = this.extractUserId(request) || "anonymous";

    console.log(`[VoiceWS] New connection: ${sessionId} (user: ${userId})`);

    // Initialize session
    const session: VoiceSession = {
      id: sessionId,
      userId,
      state: "idle",
      audioBuffer: [],
      startTime: Date.now(),
    };
    this.sessions.set(ws, session);

    // Send ready message
    this.send(ws, { type: "ready" });

    // Set up event handlers
    ws.on("message", async (data) => {
      try {
        const message = JSON.parse(data.toString()) as ClientMessage;
        await this.handleMessage(ws, session, message);
      } catch (error) {
        console.error(`[VoiceWS] Message error (${sessionId}):`, error);
        this.send(ws, {
          type: "error",
          message: error instanceof Error ? error.message : "Unknown error",
        });
      }
    });

    ws.on("close", () => {
      console.log(`[VoiceWS] Connection closed: ${sessionId}`);
      this.sessions.delete(ws);
    });

    ws.on("error", (error) => {
      console.error(`[VoiceWS] Connection error (${sessionId}):`, error);
      this.sessions.delete(ws);
    });

    // Set up session timeout
    setTimeout(() => {
      if (this.sessions.has(ws)) {
        console.log(`[VoiceWS] Session timeout: ${sessionId}`);
        ws.close(1000, "Session timeout");
      }
    }, this.config.sessionTimeout);
  }

  private async handleMessage(ws: WebSocket, session: VoiceSession, message: ClientMessage): Promise<void> {
    switch (message.type) {
      case "ping":
        this.send(ws, { type: "pong" });
        break;

      case "audio_start":
        session.state = "listening";
        session.audioBuffer = [];
        console.log(`[VoiceWS] Audio start (${session.id}): ${message.sampleRate}Hz, ${message.channels}ch`);
        break;

      case "audio_chunk":
        if (session.state !== "listening") {
          throw new Error("Not in listening state");
        }
        // Decode base64 and add to buffer
        const chunk = Buffer.from(message.data, "base64");
        if (chunk.length > this.config.maxChunkSize) {
          throw new Error(`Chunk too large: ${chunk.length} > ${this.config.maxChunkSize}`);
        }
        session.audioBuffer.push(chunk);
        break;

      case "audio_end":
        if (session.state !== "listening") {
          throw new Error("Not in listening state");
        }
        session.state = "processing";
        console.log(`[VoiceWS] Audio end (${session.id}): ${session.audioBuffer.length} chunks`);

        // Concatenate audio chunks
        const audioData = Buffer.concat(session.audioBuffer);
        session.audioBuffer = [];

        // Create WAV header (16-bit PCM, 16kHz, mono)
        const wavBuffer = this.createWavBuffer(audioData, 16000, 1);

        try {
          // Transcribe
          const result = await this.voiceClient.transcribe(wavBuffer);
          console.log(`[VoiceWS] Transcription (${session.id}): "${result.text}"`);

          this.send(ws, {
            type: "transcription",
            text: result.text,
            language: result.language,
            isFinal: true,
          });
        } catch (error) {
          console.error(`[VoiceWS] Transcription failed (${session.id}):`, error);
          this.send(ws, {
            type: "error",
            message: "Transcription failed",
            code: "TRANSCRIPTION_ERROR",
          });
        }

        session.state = "idle";
        break;

      case "synthesize":
        session.state = "speaking";
        console.log(`[VoiceWS] Synthesize (${session.id}): "${message.text.slice(0, 50)}..."`);

        try {
          // Synthesize speech (returns WAV file bytes)
          const wavBuffer = await this.voiceClient.synthesize({
            text: message.text,
            exaggeration: message.exaggeration ?? 0.5,
            speech_rate: message.speechRate,
          });

          // Strip 44-byte WAV header to get raw PCM data
          const pcmData = wavBuffer.slice(44);

          // Send audio start
          this.send(ws, { type: "audio_start", sampleRate: 24000 });

          // Send PCM audio in chunks
          const chunkSize = 8192;
          for (let i = 0; i < pcmData.length; i += chunkSize) {
            const chunk = pcmData.slice(i, i + chunkSize);
            this.send(ws, {
              type: "audio_chunk",
              data: chunk.toString("base64"),
            });
          }

          // Send audio end
          const durationSeconds = pcmData.length / (24000 * 2); // 16-bit samples
          this.send(ws, { type: "audio_end", durationSeconds });

          console.log(`[VoiceWS] Synthesis complete (${session.id}): ${durationSeconds.toFixed(2)}s`);
        } catch (error) {
          console.error(`[VoiceWS] Synthesis failed (${session.id}):`, error);
          this.send(ws, {
            type: "error",
            message: "Synthesis failed",
            code: "SYNTHESIS_ERROR",
          });
        }

        session.state = "idle";
        break;

      default:
        throw new Error(`Unknown message type: ${(message as ClientMessage).type}`);
    }
  }

  private send(ws: WebSocket, message: ServerMessage): void {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message));
    }
  }

  private extractUserId(request: IncomingMessage): string | null {
    // Extract user ID from query string or headers
    const url = new URL(request.url || "", `http://${request.headers.host}`);
    return url.searchParams.get("userId") || (request.headers["x-user-id"] as string) || null;
  }

  /**
   * Create a WAV file buffer from raw PCM data.
   */
  private createWavBuffer(pcmData: Buffer, sampleRate: number, channels: number): Buffer {
    const bitsPerSample = 16;
    const byteRate = (sampleRate * channels * bitsPerSample) / 8;
    const blockAlign = (channels * bitsPerSample) / 8;
    const dataSize = pcmData.length;
    const fileSize = 36 + dataSize;

    const header = Buffer.alloc(44);

    // RIFF header
    header.write("RIFF", 0);
    header.writeUInt32LE(fileSize, 4);
    header.write("WAVE", 8);

    // fmt sub-chunk
    header.write("fmt ", 12);
    header.writeUInt32LE(16, 16); // Sub-chunk size
    header.writeUInt16LE(1, 20); // Audio format (PCM)
    header.writeUInt16LE(channels, 22);
    header.writeUInt32LE(sampleRate, 24);
    header.writeUInt32LE(byteRate, 28);
    header.writeUInt16LE(blockAlign, 32);
    header.writeUInt16LE(bitsPerSample, 34);

    // data sub-chunk
    header.write("data", 36);
    header.writeUInt32LE(dataSize, 40);

    return Buffer.concat([header, pcmData]);
  }

  /**
   * Close the server.
   */
  close(): Promise<void> {
    return new Promise((resolve) => {
      this.wss.close(() => {
        console.log("[VoiceWS] Server closed");
        resolve();
      });
    });
  }

  /**
   * Get the number of active connections.
   */
  getConnectionCount(): number {
    return this.sessions.size;
  }
}
