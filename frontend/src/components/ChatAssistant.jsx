import React, { useState, useRef, useEffect } from 'react';
import {
  IconMessage,
  IconSend,
  IconChevronDown,
  IconChevronRight
} from './Icons';
import ResizableDivider from './ResizableDivider';

const SUGGESTIONS = [
  "Explain more simply",
  "Show a dry run",
  "How can I improve this?"
];

export default function ChatAssistant({
  messages = [],
  onSendMessage,
  isSending,
  currentSessionId,
  assistantHeight = 240,
  setAssistantHeight
}) {
  const [inputText, setInputText] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isExpanded) {
      scrollToBottom();
    }
  }, [messages, isExpanded]);

  const handleSend = () => {
    if (!inputText.trim() || isSending) return;
    onSendMessage(inputText.trim());
    setInputText('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleAssistantResize = (e) => {
    if (!setAssistantHeight) return;
    const windowH = window.innerHeight;
    const newH = windowH - e.clientY;
    const clamped = Math.max(120, Math.min(newH, 500));
    setAssistantHeight(clamped);
    try {
      localStorage.setItem('codewise_assistant_height', String(clamped));
    } catch {}
  };

  const handleAssistantReset = () => {
    if (setAssistantHeight) {
      setAssistantHeight(240);
      try {
        localStorage.removeItem('codewise_assistant_height');
      } catch {}
    }
  };

  return (
    <div
      className={`chat-drawer ${isExpanded ? 'expanded' : 'collapsed'}`}
      style={isExpanded ? { height: `${assistantHeight}px` } : {}}
    >
      {isExpanded && (
        <ResizableDivider
          direction="vertical"
          onResize={handleAssistantResize}
          onReset={handleAssistantReset}
          title="Drag to resize assistant height, double-click to reset"
        />
      )}

      {/* Drawer Header Toggle */}
      <div
        className="chat-header-bar"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="chat-header-left">
          <IconMessage size={14} color="var(--accent-pink)" />
          <span>Follow-up Learning Assistant</span>
          {messages.length > 0 && (
            <span className="chat-header-badge">{messages.length}</span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            {isExpanded ? 'Collapse' : 'Ask Question'}
          </span>
          <button className="btn-icon-subtle" style={{ pointerEvents: 'none' }}>
            {isExpanded ? <IconChevronDown size={14} /> : <IconChevronRight size={14} />}
          </button>
        </div>
      </div>

      {isExpanded && (
        <>
          {/* Exactly 3 Suggested Questions Initially */}
          <div className="chat-suggestions-minimal">
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Suggestions:</span>
            {SUGGESTIONS.map((s, idx) => (
              <button
                key={idx}
                className="btn-suggestion-clean"
                onClick={() => onSendMessage(s)}
                disabled={isSending || !currentSessionId}
              >
                {s}
              </button>
            ))}
          </div>

          {/* Conversation Messages */}
          <div className="chat-messages-area">
            {messages.length === 0 ? (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.78rem', margin: 'auto' }}>
                Ask any question about this code or choose a suggestion above.
              </div>
            ) : (
              messages.map((m) => (
                <div key={m.id} className={`chat-message-row ${m.role}`}>
                  <div className="chat-bubble" style={{ whiteSpace: 'pre-line' }}>
                    {m.content}
                  </div>
                  <div className="chat-time">
                    {m.role === 'user' ? 'You' : 'codewise Tutor'}
                  </div>
                </div>
              ))
            )}
            {isSending && (
              <div className="chat-message-row assistant">
                <div className="chat-bubble" style={{ color: 'var(--accent-pink)' }}>
                  Thinking...
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Chat Input Bar */}
          <div className="chat-input-bar">
            <input
              type="text"
              className="chat-input-clean"
              placeholder={currentSessionId ? "Ask a follow-up question..." : "Analyse code first to start chatting..."}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isSending || !currentSessionId}
            />
            <button
              className="btn-send-pink"
              onClick={handleSend}
              disabled={isSending || !inputText.trim() || !currentSessionId}
              title="Send question"
            >
              <IconSend size={13} />
            </button>
          </div>
        </>
      )}
    </div>
  );
}
