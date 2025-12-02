/**
 * Chat Message Component
 */

import type { ChatMessage } from "../api/agent";

interface MessageProps {
  message: ChatMessage;
}

export function Message({ message }: MessageProps) {
  const isUser = message.role === "user";
  const time = new Date(message.timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className={`message ${isUser ? "user" : "assistant"}`}>
      <div className="message-avatar">{isUser ? "You" : "I"}</div>
      <div className="message-content">
        {message.toolName && (
          <div className="tool-indicator">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83" />
            </svg>
            {message.toolName}
          </div>
        )}
        <p className="message-text">{message.content}</p>
        <div className="message-meta">{time}</div>
      </div>
    </div>
  );
}

/**
 * Typing Indicator Component
 */
export function TypingIndicator() {
  return (
    <div className="message assistant">
      <div className="message-avatar">I</div>
      <div className="message-content">
        <div className="typing-indicator">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    </div>
  );
}
