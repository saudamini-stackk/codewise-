import React, { useState, useRef, useEffect } from 'react';
import {
  IconMessage,
  IconSend,
  IconChevronDown,
  IconChevronRight,
  IconMaximize,
  IconMinimize
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
  assistantHeight = 340,
  setAssistantHeight
}) {
  const [inputText, setInputText] = useState('');
  const [isExpanded, setIsExpanded] = useState(true);
  const [isMaximized, setIsMaximized] = useState(false);
  const [expandedMessages, setExpandedMessages] = useState({});
  const messagesEndRef = useRef(null);

  const toggleMessageExpand = (msgId) => {
    setExpandedMessages(prev => ({
      ...prev,
      [msgId]: !prev[msgId]
    }));
  };

  const renderFormattedContent = (content, msgId) => {
    if (!content) return null;
    const isMsgExpanded = !!expandedMessages[msgId];
    const lines = content.split('\n');
    const isLong = lines.length > 8;

    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', userSelect: 'text', lineHeight: '1.6' }}>
          {content}
        </div>
        {isLong && (
          <button
            type="button"
            className="btn-suggestion-clean"
            onClick={(e) => {
              e.stopPropagation();
              toggleMessageExpand(msgId);
              if (!isMaximized) setIsMaximized(true);
            }}
            style={{ alignSelf: 'flex-start', marginTop: '4px', fontSize: '0.68rem', padding: '2px 8px' }}
          >
            {isMaximized ? 'Maximize Active View' : 'Expand Chat Panel'}
          </button>
        )}
      </div>
    );
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isExpanded) {
      scrollToBottom();
    }
  }, [messages, isExpanded, isMaximized]);

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
    setIsMaximized(false);
    const windowH = window.innerHeight;
    const newH = windowH - e.clientY;
    const clamped = Math.max(260, Math.min(newH, Math.floor(windowH * 0.85)));
    setAssistantHeight(clamped);
    try {
      localStorage.setItem('codewise_assistant_height', String(clamped));
    } catch {}
  };

  const handleAssistantReset = () => {
    if (setAssistantHeight) {
      setAssistantHeight(360);
      setIsMaximized(false);
      try {
        localStorage.setItem('codewise_assistant_height', '360');
      } catch {}
    }
  };

  // Determine effective height
  const currentH = isMaximized
    ? Math.min(680, Math.floor(window.innerHeight * 0.75))
    : Math.max(280, Number(assistantHeight) || 340);

  return (
    <div
      className={`chat-drawer ${isExpanded ? 'expanded' : 'collapsed'} ${isMaximized ? 'maximized' : ''}`}
      style={isExpanded ? { height: `${currentH}px` } : {}}
    >
      {isExpanded && (
        <ResizableDivider
          direction="vertical"
          onResize={handleAssistantResize}
          onReset={handleAssistantReset}
          title="Drag up to expand assistant, double-click to reset"
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

        <div
          style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
          onClick={(e) => e.stopPropagation()}
        >
          {isExpanded && (
            <button
              type="button"
              className="btn-icon-subtle"
              onClick={() => setIsMaximized(!isMaximized)}
              title={isMaximized ? "Restore normal size" : "Expand full height"}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                fontSize: '0.72rem',
                color: isMaximized ? 'var(--accent-pink)' : 'var(--text-secondary)',
                backgroundColor: 'rgba(255, 255, 255, 0.04)',
                padding: '3px 8px',
                borderRadius: '6px'
              }}
            >
              {isMaximized ? <IconMinimize size={13} /> : <IconMaximize size={13} />}
              <span>{isMaximized ? 'Restore' : 'Expand'}</span>
            </button>
          )}

          <button
            type="button"
            className="btn-icon-subtle"
            onClick={() => setIsExpanded(!isExpanded)}
            title={isExpanded ? "Collapse assistant" : "Open assistant"}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '0.72rem',
              color: 'var(--text-muted)'
            }}
          >
            <span>{isExpanded ? 'Collapse' : 'Ask Question'}</span>
            {isExpanded ? <IconChevronDown size={14} /> : <IconChevronRight size={14} />}
          </button>
        </div>
      </div>

      {isExpanded && (
        <>
          {/* Suggestions */}
          <div className="chat-suggestions-minimal">
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Suggestions:</span>
            {SUGGESTIONS.map((s, idx) => (
              <button
                key={idx}
                type="button"
                className="btn-suggestion-clean"
                onClick={() => onSendMessage(s)}
                disabled={isSending || !currentSessionId}
              >
                {s}
              </button>
            ))}
            <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <button
                type="button"
                className="btn-suggestion-clean"
                onClick={() => setIsMaximized(!isMaximized)}
                title={isMaximized ? "Restore default height" : "Expand chat view"}
                style={{ color: isMaximized ? 'var(--accent-pink)' : 'var(--text-muted)', fontSize: '0.7rem' }}
              >
                {isMaximized ? 'Restore View' : 'Expand View'}
              </button>
            </div>
          </div>

          {/* Conversation Messages */}
          <div className="chat-messages-area" style={{ flex: '1 1 0%', minHeight: '160px', overflowY: 'auto', WebkitOverflowScrolling: 'touch', scrollBehavior: 'smooth' }}>
            {messages.length === 0 ? (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.78rem', margin: 'auto' }}>
                Ask any question about this code or choose a suggestion above.
              </div>
            ) : (
              messages.map((m) => (
                <div key={m.id} className={`chat-message-row ${m.role}`}>
                  <div className="chat-bubble">
                    {renderFormattedContent(m.content, m.id)}
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
              type="button"
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
