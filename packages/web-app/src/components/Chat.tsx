/**
 * Chat Component
 *
 * Main chat interface with text and voice input.
 */

import { useState, useRef, useEffect, useCallback } from "react";
import { Message, TypingIndicator } from "./Message";
import { streamChat, type ChatMessage } from "../api/agent";
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

export function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [currentTool, setCurrentTool] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const voiceClientRef = useRef<VoiceClient | null>(null);
  const userId = useRef(getUserId());

  // Initialize voice client
  useEffect(() => {
    voiceClientRef.current = new VoiceClient({
      userId: userId.current,
      onStateChange: setVoiceState,
      onTranscription: (text) => {
        // When we get a transcription, send it as a chat message
        handleSend(text);
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
        for await (const chunk of streamChat(userId.current, messageText, sessionId)) {
          switch (chunk.type) {
            case "text":
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
    [input, isStreaming, sessionId]
  );

  // Handle key press
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Voice recording toggle
  const toggleRecording = async () => {
    const client = voiceClientRef.current;
    if (!client) return;

    try {
      if (voiceState === "idle") {
        await client.connect();
      } else if (voiceState === "ready") {
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
        return "Connect";
      case "connecting":
        return "...";
      case "ready":
        return "Speak";
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
                Hello, Commander! I'm IRIS, your AI companion for Star Atlas. How can I help you today?
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
