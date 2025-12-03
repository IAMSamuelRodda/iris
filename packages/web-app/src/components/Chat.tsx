/**
 * Chat Component
 *
 * Main chat interface with text and voice input.
 */

import { useState, useRef, useEffect, useCallback } from "react";
import { Message, TypingIndicator } from "./Message";
import { streamChat, getVoiceStyles, type ChatMessage, type VoiceStyleId, type VoiceStyleOption } from "../api/agent";
import { VoiceClient, type VoiceState } from "../api/voice";

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

  // Handle voice style change
  const handleStyleChange = (styleId: VoiceStyleId) => {
    setVoiceStyle(styleId);
    setVoiceStylePreference(styleId);
    setShowStyleDropdown(false);
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

      try {
        for await (const chunk of streamChat(userId.current, messageText, sessionId, voiceStyle)) {
          switch (chunk.type) {
            case "acknowledgment":
              // Quick acknowledgment for voice feedback
              // In voice mode, speak immediately; in text mode, show briefly
              if (text && voiceClientRef.current?.isConnected()) {
                const styleProps = availableStyles.find((s) => s.id === voiceStyle)?.voiceProperties;
                voiceClientRef.current.synthesize(
                  chunk.content,
                  styleProps?.exaggeration ?? 0.5,
                  styleProps?.speechRate ?? 1.0
                );
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
              // Trigger TTS for voice responses with voice style properties
              if (text && assistantContent && voiceClientRef.current?.isConnected()) {
                const styleProps = availableStyles.find((s) => s.id === voiceStyle)?.voiceProperties;
                voiceClientRef.current.synthesize(
                  assistantContent,
                  styleProps?.exaggeration ?? 0.5,
                  styleProps?.speechRate ?? 1.0
                );
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
    [input, isStreaming, sessionId, voiceStyle]
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

        <button
          className={`btn btn-primary voice-btn ${voiceState === "recording" ? "recording" : ""}`}
          onClick={toggleRecording}
          disabled={isStreaming || voiceState === "processing" || voiceState === "speaking"}
          title={getVoiceButtonLabel()}
        >
          {voiceState === "recording" ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="6" width="12" height="12" rx="2" />
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
