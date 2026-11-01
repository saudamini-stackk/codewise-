import React, { useState } from 'react';
import {
  IconAlertCircle,
  IconAlertTriangle,
  IconInfo,
  IconCopy,
  IconCheck,
  IconCode
} from './Icons';

export default function DiagnosticsList({
  diagnostics = [],
  suggestedCode,
  explanationOfChanges,
  onApplySuggestedCode
}) {
  const [copiedFix, setCopiedFix] = useState(false);

  const handleCopyFix = async () => {
    if (!suggestedCode) return;
    try {
      await navigator.clipboard.writeText(suggestedCode);
      setCopiedFix(true);
      setTimeout(() => setCopiedFix(false), 2000);
    } catch (err) {
      console.error(err);
    }
  };

  const getSeverityIcon = (severity) => {
    if (severity === 'error') return <IconAlertCircle size={16} color="#ef4444" />;
    if (severity === 'warning') return <IconAlertTriangle size={16} color="#f59e0b" />;
    return <IconInfo size={16} color="var(--accent-lavender)" />;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Diagnostic Issues List */}
      <div>
        <div className="card-title">
          <IconAlertTriangle size={17} />
          <span>Diagnostic Findings ({diagnostics.length})</span>
        </div>

        {diagnostics.length === 0 ? (
          <div className="analysis-card" style={{ textAlign: 'center', padding: '24px', color: 'var(--success-text)' }}>
            <IconCheck size={28} style={{ margin: '0 auto 8px', color: '#10b981' }} />
            <div style={{ fontWeight: 600 }}>No Errors or Warnings Detected</div>
            <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              The code adheres to valid syntax and basic static analysis heuristics.
            </div>
          </div>
        ) : (
          diagnostics.map((diag, idx) => (
            <div key={diag.id || idx} className={`diagnostic-item ${diag.severity}`}>
              <div className="diag-header">
                <div className="diag-title-group">
                  {getSeverityIcon(diag.severity)}
                  <span className="diag-title">{diag.title}</span>
                  <span className={`diag-badge ${diag.severity}`}>{diag.severity}</span>
                </div>
                {diag.line_number && (
                  <span className="diag-line">Line {diag.line_number}</span>
                )}
              </div>

              <div className="diag-desc">{diag.explanation}</div>

              {diag.recommended_correction && (
                <div className="diag-fix">
                  <strong>Recommended Fix: </strong>
                  {diag.recommended_correction}
                </div>
              )}

              {diag.corrected_snippet && (
                <div style={{ marginTop: '4px' }}>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Snippet Example:</div>
                  <pre className="code-badge" style={{ display: 'block', padding: '8px', overflowX: 'auto', whiteSpace: 'pre' }}>
                    {diag.corrected_snippet}
                  </pre>
                </div>
              )}

              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', alignSelf: 'flex-end' }}>
                Detection source: {diag.detection_type === 'confirmed_parser' ? 'Confirmed Parser Diagnostic' : diag.detection_type === 'static_heuristic' ? 'Static Analysis Heuristic' : 'AI Inferred'}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Suggested Corrected Code Section */}
      {suggestedCode && (
        <div className="analysis-card" style={{ borderColor: 'rgba(139, 92, 246, 0.35)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <div className="card-title" style={{ margin: 0 }}>
              <IconCode size={17} />
              <span>Suggested Corrected Code</span>
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                className="btn-tool"
                onClick={handleCopyFix}
                title="Copy corrected code"
              >
                {copiedFix ? <IconCheck size={14} /> : <IconCopy size={14} />}
                <span>{copiedFix ? 'Copied' : 'Copy Code'}</span>
              </button>
              {onApplySuggestedCode && (
                <button
                  className="btn-tool"
                  onClick={() => onApplySuggestedCode(suggestedCode)}
                  style={{ color: 'var(--accent-lavender-light)', borderColor: 'var(--accent-border)' }}
                  title="Replace editor code with this corrected version"
                >
                  <span>Apply to Editor</span>
                </button>
              )}
            </div>
          </div>

          {explanationOfChanges && (
            <div style={{ marginBottom: '12px', fontSize: '0.84rem', color: 'var(--text-secondary)' }}>
              <div style={{ fontWeight: 600, color: 'var(--accent-lavender)', marginBottom: '4px' }}>What changed and why:</div>
              <div style={{ whiteSpace: 'pre-line' }}>{explanationOfChanges}</div>
            </div>
          )}

          <div style={{ position: 'relative' }}>
            <pre
              style={{
                backgroundColor: 'var(--bg-code)',
                border: '1px solid var(--accent-border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '14px',
                fontFamily: 'var(--font-mono)',
                fontSize: '0.84rem',
                color: '#e2e8f0',
                overflowX: 'auto',
                lineHeight: 1.6
              }}
            >
              {suggestedCode}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
