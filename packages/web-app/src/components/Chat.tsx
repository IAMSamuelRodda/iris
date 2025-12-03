/**
 * Chat Component
 *
 * Main chat interface with text and voice input.
 */

import { useState, useRef, useEffect, useCallback } from "react";
import { Message, TypingIndicator } from "./Message";
import { streamChat, getVoiceStyles, type ChatMessage, type VoiceStyleId, type VoiceStyleOption } from "../api/agent";
import { VoiceClient, type VoiceState, getAvailableVoices, selectVoice } from "../api/voice";
import { TextChunker, type ChunkMode } from "../api/text-chunker";

// Generate a simple user ID (in production, use auth)
const getUserId = () => {
  let userId = localStorage.getItem("iris-user-id");
  if (!userId) {
    userId = `user-${Math.random().toString(36).slice(2, 11)}`;
    localStorage.setItem("iris-user-id", userId);
  }
  return userId;
};

// Get/set voice style preference
const getVoiceStylePreference = (): VoiceStyleId => {
  return (localStorage.getItem("iris-voice-style") as VoiceStyleId) || "normal";
};

const setVoiceStylePreference = (style: VoiceStyleId) => {
  localStorage.setItem("iris-voice-style", style);
};

// Get/set TTS chunk mode preference (sentence vs paragraph)
const getChunkModePreference = (): ChunkMode => {
  return (localStorage.getItem("iris-chunk-mode") as ChunkMode) || "sentence";
};

const setChunkModePreference = (mode: ChunkMode) => {
  localStorage.setItem("iris-chunk-mode", mode);
};

// Get/set TTS voice preference
const getTtsVoicePreference = (): string => {
  return localStorage.getItem("iris-tts-voice") || "Alexander";
};

const setTtsVoicePreference = (voice: string) => {
  localStorage.setItem("iris-tts-voice", voice);
};

export function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [currentTool, setCurrentTool] = useState<string | null>(null);
  const [voiceStyle, setVoiceStyle] = useState<VoiceStyleId>(getVoiceStylePreference);
  const [availableStyles, setAvailableStyles] = useState<VoiceStyleOption[]>([]);
  const [showStyleDropdown, setShowStyleDropdown] = useState(false);
  const [chunkMode, setChunkMode] = useState<ChunkMode>(getChunkModePreference);
  const [showChunkDropdown, setShowChunkDropdown] = useState(false);

  // TTS Voice selection state
  const [ttsVoices, setTtsVoices] = useState<string[]>([]);
  const [currentTtsVoice, setCurrentTtsVoice] = useState<string>(getTtsVoicePreference);
  const [showVoiceDropdown, setShowVoiceDropdown] = useState(false);
  const [voiceReady, setVoiceReady] = useState(false);
  const [voiceLoading, setVoiceLoading] = useState(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const voiceClientRef = useRef<VoiceClient | null>(null);
  const userId = useRef(getUserId());

  // Load available voice styles
  useEffect(() => {
    getVoiceStyles()
      .then(setAvailableStyles)
      .catch((err) => console.error("[Chat] Failed to load voice styles:", err));
  }, []);

  // Load TTS voices and check readiness on mount
  useEffect(() => {
    const initVoices = async () => {
      setVoiceLoading(true);
      try {
        const data = await getAvailableVoices();
        setTtsVoices(data.voices);
        setCurrentTtsVoice(data.current);
        setVoiceReady(true);
        console.log(`[Chat] Voice ready: ${data.current}, ${data.voices.length} voices available`);
      } catch (err) {
        console.error("[Chat] Failed to load TTS voices:", err);
        // Still allow usage but voice might be slow first time
        setVoiceReady(true);
      } finally {
        setVoiceLoading(false);
      }
    };
    initVoices();
  }, []);

  // Handle TTS voice change
  const handleTtsVoiceChange = async (voice: string) => {
    setShowVoiceDropdown(false);
    if (voice === currentTtsVoice) return;

    setVoiceReady(false);
    setVoiceLoading(true);
    console.log(`[Chat] Switching voice to ${voice}...`);

    try {
      const result = await selectVoice(voice);
      if (result.success) {
        setCurrentTtsVoice(voice);
        setTtsVoicePreference(voice);
        console.log(`[Chat] ${result.message}`);
      }
    } catch (err) {
      console.error("[Chat] Failed to change voice:", err);
    } finally {
      setVoiceReady(true);
      setVoiceLoading(false);
    }
  };

  // Handle voice style change
  const handleStyleChange = (styleId: VoiceStyleId) => {
    setVoiceStyle(styleId);
    setVoiceStylePreference(styleId);
    setShowStyleDropdown(false);
  };

  // Handle chunk mode change
  const handleChunkModeChange = (mode: ChunkMode) => {
    setChunkMode(mode);
    setChunkModePreference(mode);
    setShowChunkDropdown(false);
  };

  // Initialize voice client
  useEffect(() => {
    voiceClientRef.current = new VoiceClient({
      userId: userId.current,
      onStateChange: setVoiceState,
      onTranscription: (text) => {
        // When we get a transcription, send it as a chat message
        handleSend(text);
      },
      onSynthesisComplete: (text) => {
        // Log spoken text for troubleshooting
        console.log("[Chat] TTS playback complete:", text);
      },
      onError: (error) => {
        console.error("[Voice] Error:", error);
      },
    });

    return () => {
      voiceClientRef.current?.disconnect();
    };
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Escape key handler for audio interrupt
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        const client = voiceClientRef.current;
        if (client && (voiceState === "speaking" || voiceState === "recording" || voiceState === "processing")) {
          e.preventDefault();
          console.log("[Chat] Escape pressed - interrupting");
          client.interruptAll();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [voiceState]);

  // Stop audio handler
  const handleStopAudio = () => {
    voiceClientRef.current?.stopAudio();
  };

  // Send message
  const handleSend = useCallback(
    async (text?: string) => {
      const messageText = text || input.trim();
      if (!messageText || isStreaming) return;

      setInput("");
      setIsStreaming(true);
      setCurrentTool(null);

      // Add user message
      const userMessage: ChatMessage = {
        id: `msg-${Date.now()}-user`,
        role: "user",
        content: messageText,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // Create placeholder for assistant response
      const assistantId = `msg-${Date.now()}-assistant`;
      let assistantContent = "";

      // Create text chunker for streaming TTS (only in voice mode)
      const isVoiceMode = !!text && voiceClientRef.current?.isConnected();
      const chunker = isVoiceMode ? new TextChunker({ mode: chunkMode }) : null;
      const styleProps = availableStyles.find((s) => s.id === voiceStyle)?.voiceProperties;

      // Helper to send text to TTS
      const synthesizeChunk = (chunkText: string) => {
        if (isVoiceMode && chunkText.trim()) {
          console.log(`[Chat] TTS chunk (${chunkMode}):`, chunkText.slice(0, 50) + (chunkText.length > 50 ? "..." : ""));
          voiceClientRef.current?.synthesize(
            chunkText,
            styleProps?.exaggeration ?? 0.5,
            styleProps?.speechRate ?? 1.0
          );
        }
      };

      try {
        for await (const chunk of streamChat(userId.current, messageText, sessionId, voiceStyle)) {
          switch (chunk.type) {
            case "acknowledgment":
              // Quick acknowledgment for voice feedback - speak immediately
              if (isVoiceMode) {
                synthesizeChunk(chunk.content);
              }
              // Show acknowledgment in chat (will be replaced by full response)
              if (chunk.isInterim) {
                setMessages((prev) => [
                  ...prev,
                  {
                    id: `${assistantId}-ack`,
                    role: "assistant",
                    content: chunk.content,
                    timestamp: Date.now(),
                  },
                ]);
              }
              break;

            case "text":
              // Remove acknowledgment message when real content arrives
              setMessages((prev) => prev.filter((m) => m.id !== `${assistantId}-ack`));
              assistantContent += chunk.content;
              setMessages((prev) => {
                const existing = prev.find((m) => m.id === assistantId);
                if (existing) {
                  return prev.map((m) => (m.id === assistantId ? { ...m, content: assistantContent } : m));
                }
                return [
                  ...prev,
                  {
                    id: assistantId,
                    role: "assistant",
                    content: assistantContent,
                    timestamp: Date.now(),
                  },
                ];
              });

              // Feed text to chunker for streaming TTS
              if (chunker) {
                const completedChunks = chunker.add(chunk.content);
                for (const completedChunk of completedChunks) {
                  synthesizeChunk(completedChunk);
                }
              }
              break;

            case "tool_start":
              setCurrentTool(chunk.toolName || "tool");
              break;

            case "tool_end":
              setCurrentTool(null);
              break;

            case "system":
              if (chunk.sessionId) {
                setSessionId(chunk.sessionId);
              }
              break;

            case "done":
              if (chunk.sessionId) {
                setSessionId(chunk.sessionId);
              }
              // Flush remaining text to TTS
              if (chunker) {
                const remaining = chunker.flush();
                if (remaining) {
                  synthesizeChunk(remaining);
                }
              }
              break;

            case "error":
              console.error("[Chat] Error:", chunk.content);
              setMessages((prev) => [
                ...prev,
                {
                  id: `msg-${Date.now()}-error`,
                  role: "assistant",
                  content: `Error: ${chunk.content}`,
                  timestamp: Date.now(),
                },
              ]);
              break;
          }
        }
      } catch (error) {
        console.error("[Chat] Stream error:", error);
        setMessages((prev) => [
          ...prev,
          {
            id: `msg-${Date.now()}-error`,
            role: "assistant",
            content: `Connection error: ${error instanceof Error ? error.message : "Unknown error"}`,
            timestamp: Date.now(),
          },
        ]);
      } finally {
        setIsStreaming(false);
        setCurrentTool(null);
      }
    },
    [input, isStreaming, sessionId, voiceStyle, chunkMode, availableStyles]
  );

  // Handle key press
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Voice recording toggle
  // On first click: connect AND start recording (eliminates double-click on first use)
  const toggleRecording = async () => {
    const client = voiceClientRef.current;
    if (!client) return;

    try {
      if (voiceState === "idle" || voiceState === "ready") {
        // Connect if needed, then start recording
        if (!client.isConnected()) {
          await client.connect();
        }
        await client.startRecording();
      } else if (voiceState === "recording") {
        client.stopRecording();
      }
    } catch (error) {
      console.error("[Voice] Toggle error:", error);
    }
  };

  // Get voice button label
  const getVoiceButtonLabel = () => {
    switch (voiceState) {
      case "idle":
      case "ready":
        return "🎤";
      case "connecting":
        return "...";
      case "recording":
        return "Stop";
      case "processing":
        return "...";
      case "speaking":
        return "Playing";
      default:
        return "Voice";
    }
  };

  return (
    <div className="chat-container">
      <div className="messages">
        {messages.length === 0 && (
          <div className="message assistant">
            <div className="message-avatar">I</div>
            <div className="message-content">
              <p className="message-text">
                Hey Commander! IRIS here, your guy in the chair. What do you need?
              </p>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <Message key={message.id} message={message} />
        ))}

        {isStreaming && !messages.find((m) => m.role === "assistant" && m.content) && <TypingIndicator />}

        {currentTool && (
          <div className="tool-indicator" style={{ alignSelf: "flex-start", marginLeft: 48 }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83" />
            </svg>
            Using {currentTool}...
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="input-area">
        {/* Voice Style Selector */}
        <div className="style-selector" style={{ position: "relative" }}>
          <button
            className="btn btn-secondary style-btn"
            onClick={() => setShowStyleDropdown(!showStyleDropdown)}
            title={`Voice Style: ${availableStyles.find((s) => s.id === voiceStyle)?.name || voiceStyle}`}
            style={{
              padding: "8px 12px",
              fontSize: "12px",
              minWidth: "auto",
              background: "var(--bg-tertiary)",
              border: "1px solid var(--border-color)",
              borderRadius: "8px",
              cursor: "pointer",
            }}
          >
            {availableStyles.find((s) => s.id === voiceStyle)?.name || voiceStyle}
          </button>
          {showStyleDropdown && availableStyles.length > 0 && (
            <div
              className="style-dropdown"
              style={{
                position: "absolute",
                bottom: "100%",
                left: 0,
                marginBottom: "8px",
                background: "var(--bg-secondary)",
                border: "1px solid var(--border-color)",
                borderRadius: "8px",
                boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
                minWidth: "180px",
                zIndex: 100,
              }}
            >
              {availableStyles.map((style) => (
                <button
                  key={style.id}
                  onClick={() => handleStyleChange(style.id)}
                  style={{
                    display: "block",
                    width: "100%",
                    padding: "10px 14px",
                    textAlign: "left",
                    background: style.id === voiceStyle ? "var(--primary-color)" : "transparent",
                    border: "none",
                    color: "var(--text-primary)",
                    cursor: "pointer",
                    borderRadius: style.id === availableStyles[0]?.id ? "8px 8px 0 0" : style.id === availableStyles[availableStyles.length - 1]?.id ? "0 0 8px 8px" : "0",
                  }}
                >
                  <div style={{ fontWeight: 500 }}>{style.name}</div>
                  <div style={{ fontSize: "11px", opacity: 0.7, marginTop: "2px" }}>{style.description}</div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* TTS Chunk Mode Selector */}
        <div className="chunk-selector" style={{ position: "relative" }}>
          <button
            className="btn btn-secondary chunk-btn"
            onClick={() => setShowChunkDropdown(!showChunkDropdown)}
            title={`TTS Chunking: ${chunkMode === "sentence" ? "Sentence (faster)" : "Paragraph (natural)"}`}
            style={{
              padding: "8px 12px",
              fontSize: "12px",
              minWidth: "auto",
              background: "var(--bg-tertiary)",
              border: "1px solid var(--border-color)",
              borderRadius: "8px",
              cursor: "pointer",
            }}
          >
            {chunkMode === "sentence" ? "S" : "P"}
          </button>
          {showChunkDropdown && (
            <div
              className="chunk-dropdown"
              style={{
                position: "absolute",
                bottom: "100%",
                left: 0,
                marginBottom: "8px",
                background: "var(--bg-secondary)",
                border: "1px solid var(--border-color)",
                borderRadius: "8px",
                boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
                minWidth: "200px",
                zIndex: 100,
              }}
            >
              <button
                onClick={() => handleChunkModeChange("sentence")}
                style={{
                  display: "block",
                  width: "100%",
                  padding: "10px 14px",
                  textAlign: "left",
                  background: chunkMode === "sentence" ? "var(--primary-color)" : "transparent",
                  border: "none",
                  color: "var(--text-primary)",
                  cursor: "pointer",
                  borderRadius: "8px 8px 0 0",
                }}
              >
                <div style={{ fontWeight: 500 }}>Sentence</div>
                <div style={{ fontSize: "11px", opacity: 0.7, marginTop: "2px" }}>Faster first audio, choppier</div>
              </button>
              <button
                onClick={() => handleChunkModeChange("paragraph")}
                style={{
                  display: "block",
                  width: "100%",
                  padding: "10px 14px",
                  textAlign: "left",
                  background: chunkMode === "paragraph" ? "var(--primary-color)" : "transparent",
                  border: "none",
                  color: "var(--text-primary)",
                  cursor: "pointer",
                  borderRadius: "0 0 8px 8px",
                }}
              >
                <div style={{ fontWeight: 500 }}>Paragraph</div>
                <div style={{ fontSize: "11px", opacity: 0.7, marginTop: "2px" }}>More natural prosody</div>
              </button>
            </div>
          )}
        </div>

        {/* TTS Voice Selector */}
        <div className="voice-selector" style={{ position: "relative" }}>
          <button
            className="btn btn-secondary voice-select-btn"
            onClick={() => setShowVoiceDropdown(!showVoiceDropdown)}
            disabled={voiceLoading}
            title={voiceLoading ? "Loading voice..." : `Voice: ${currentTtsVoice}`}
            style={{
              padding: "8px 12px",
              fontSize: "12px",
              minWidth: "auto",
              background: voiceLoading ? "var(--bg-tertiary)" : "var(--bg-tertiary)",
              border: "1px solid var(--border-color)",
              borderRadius: "8px",
              cursor: voiceLoading ? "wait" : "pointer",
              opacity: voiceLoading ? 0.6 : 1,
            }}
          >
            {voiceLoading ? "..." : currentTtsVoice.slice(0, 3)}
          </button>
          {showVoiceDropdown && ttsVoices.length > 0 && (
            <div
              className="voice-dropdown"
              style={{
                position: "absolute",
                bottom: "100%",
                left: 0,
                marginBottom: "8px",
                background: "var(--bg-secondary)",
                border: "1px solid var(--border-color)",
                borderRadius: "8px",
                boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
                minWidth: "140px",
                maxHeight: "300px",
                overflowY: "auto",
                zIndex: 100,
              }}
            >
              {ttsVoices.map((voice, idx) => (
                <button
                  key={voice}
                  onClick={() => handleTtsVoiceChange(voice)}
                  style={{
                    display: "block",
                    width: "100%",
                    padding: "8px 14px",
                    textAlign: "left",
                    background: voice === currentTtsVoice ? "var(--primary-color)" : "transparent",
                    border: "none",
                    color: "var(--text-primary)",
                    cursor: "pointer",
                    borderRadius: idx === 0 ? "8px 8px 0 0" : idx === ttsVoices.length - 1 ? "0 0 8px 8px" : "0",
                    fontSize: "13px",
                  }}
                >
                  {voice}
                </button>
              ))}
            </div>
          )}
        </div>

        <textarea
          ref={inputRef}
          className="chat-input"
          placeholder="Type a message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyPress}
          rows={1}
          disabled={isStreaming}
        />

        {/* Voice/Stop button - shows stop when speaking, disabled when voice loading */}
        {voiceState === "speaking" ? (
          <button
            className="btn btn-danger stop-btn"
            onClick={handleStopAudio}
            title="Stop audio (Escape)"
            style={{
              background: "#dc3545",
              borderColor: "#dc3545",
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="6" width="12" height="12" rx="2" />
            </svg>
          </button>
        ) : (
          <button
            className={`btn btn-primary voice-btn ${voiceState === "recording" ? "recording" : ""}`}
            onClick={toggleRecording}
            disabled={isStreaming || voiceState === "processing" || !voiceReady}
            title={!voiceReady ? "Loading voice..." : getVoiceButtonLabel()}
            style={{
              opacity: !voiceReady ? 0.5 : 1,
              cursor: !voiceReady ? "wait" : "pointer",
            }}
          >
            {voiceState === "recording" ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <rect x="6" y="6" width="12" height="12" rx="2" />
              </svg>
            ) : !voiceReady ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ animation: "spin 1s linear infinite" }}>
                <circle cx="12" cy="12" r="10" opacity="0.3" />
                <path d="M12 2a10 10 0 0 1 10 10" />
              </svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="23" />
                <line x1="8" y1="23" x2="16" y2="23" />
              </svg>
            )}
          </button>
        )}

        <button className="btn btn-primary" onClick={() => handleSend()} disabled={!input.trim() || isStreaming}>
          {isStreaming ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 6v6l4 2" />
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          )}
        </button>
      </div>
    </div>
  );
}
