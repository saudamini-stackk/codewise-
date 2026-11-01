import React from 'react';
import { IconBook, IconX } from './Icons';

export default function AboutModal({ isOpen, onClose, systemStatus }) {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <IconBook size={16} color="var(--accent-pink)" />
            <span className="modal-title">About codewise</span>
          </div>
          <button className="btn-icon-subtle" onClick={onClose}>
            <IconX size={14} />
          </button>
        </div>

        <div className="modal-body">
          <div style={{ marginBottom: '14px' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              codewise
            </h3>
            <div style={{ fontSize: '0.8rem', color: 'var(--accent-pink)', fontWeight: 500 }}>
              understand the code. master the logic.
            </div>
          </div>

          <p style={{ marginBottom: '14px', fontSize: '0.84rem', color: 'var(--text-secondary)' }}>
            <strong>codewise</strong> is an intelligent code explanation and learning assistant. It breaks down source code into structured mental models: plain-language overviews, execution workflows, inputs and outputs, edge cases, and computational complexity.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '14px' }}>
            <div style={{ background: 'var(--bg-panel)', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontWeight: 600, color: 'var(--accent-pink-soft)', marginBottom: '3px', fontSize: '0.8rem' }}>
                Dual-Engine Architecture
              </div>
              <ul style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', paddingLeft: '16px' }}>
                <li><strong>Local Static Analysis:</strong> Runs Python AST visitors, syntax validators, and static pattern matching without needing any internet connection, paid subscription, or API key.</li>
                <li><strong>AI Integration:</strong> Securely invokes configurable LLM endpoints (OpenAI / Gemini) via backend environment variables when configured.</li>
              </ul>
            </div>

            <div style={{ background: 'var(--bg-panel)', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontWeight: 600, color: 'var(--accent-pink-soft)', marginBottom: '3px', fontSize: '0.8rem' }}>
                Persistence & Portability
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                Saved conversation threads, revisions, and follow-up discussions persist in a local SQLite database at <code className="code-inline">{systemStatus?.database_path || 'data/codewise.db'}</code>.
              </div>
            </div>
          </div>

          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            Python Version: {systemStatus?.python_version || '3.14'} • Active Mode: {systemStatus?.active_mode || 'local'}
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn-tool-clean" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
