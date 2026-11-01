import React, { useState } from 'react';
import {
  IconBook,
  IconCode,
  IconPlay,
  IconCopy,
  IconCheck,
  IconAlertTriangle,
  IconAlertCircle,
  IconInfo
} from './Icons';
import { api } from '../services/api';

export default function AnalysisView({
  analysis,
  isAnalyzing,
  onApplySuggestedCode,
  onClose,
  code,
  language
}) {
  // Explore further mode: null | 'linebyline' | 'dryrun' | 'complexity'
  const [activeExplore, setActiveExplore] = useState(null);
  const [copiedFix, setCopiedFix] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState(null);

  if (isAnalyzing) {
    return (
      <section className="results-panel">
        <div className="analysis-panel-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              Code Analysis
            </span>
            <span style={{ fontSize: '0.72rem', color: 'var(--accent-pink-soft)' }}>
              Analysing...
            </span>
          </div>
          {onClose && (
            <button
              className="btn-tool-clean"
              onClick={onClose}
              title="Close analysis panel"
              style={{ padding: '2px 8px', fontSize: '0.8rem', lineHeight: 1 }}
            >
              ✕
            </button>
          )}
        </div>
        <div className="empty-state" style={{ minHeight: '200px' }}>
          <div className="empty-title">Analysing Code...</div>
          <div className="empty-desc">
            Parsing syntax, evaluating structure, and formulating explanations.
          </div>
        </div>
      </section>
    );
  }

  if (!analysis) {
    return (
      <section className="results-panel">
        <div className="analysis-panel-header">
          <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            Code Analysis
          </span>
          {onClose && (
            <button
              className="btn-tool-clean"
              onClick={onClose}
              title="Close analysis panel"
              style={{ padding: '2px 8px', fontSize: '0.8rem', lineHeight: 1 }}
            >
              ✕
            </button>
          )}
        </div>
        <div className="empty-state" style={{ minHeight: '200px' }}>
          <div className="empty-title">Ready for Analysis</div>
          <div className="empty-desc">
            Click <strong>Analyse Code</strong> in the editor toolbar to generate detailed explanations.
          </div>
        </div>
      </section>
    );
  }

  const handleCopyFix = async (codeSnippet) => {
    if (!codeSnippet) return;
    try {
      await navigator.clipboard.writeText(codeSnippet);
      setCopiedFix(true);
      setTimeout(() => setCopiedFix(false), 2000);
    } catch (err) {
      console.error(err);
    }
  };

  const handleVerifySample = async () => {
    if (!analysis?.expected_io || !code) return;
    setIsVerifying(true);
    setVerifyResult(null);
    try {
      const res = await api.verifySample({
        code,
        language: language || 'python',
        sampleInput: analysis.expected_io.sample_input || '',
        expectedOutput: analysis.expected_io.sample_output || ''
      });
      setVerifyResult(res);
    } catch (err) {
      setVerifyResult({
        is_match: false,
        actual_output: '',
        expected_output: analysis.expected_io.sample_output || '',
        notes: `Verification error: ${err.message}`
      });
    } finally {
      setIsVerifying(false);
    }
  };

  const diagnostics = analysis.diagnostics || [];
  const hasIssues = diagnostics.length > 0;

  // Determine which exploration actions are genuinely meaningful for this code/document
  const hasLineByLine = Boolean(analysis?.line_by_line && analysis.line_by_line.length > 0);
  const hasDryRun = Boolean((analysis?.dry_run && analysis.dry_run.length > 0) || analysis?.loop_details);
  const hasComplexity = Boolean(
    analysis?.complexity &&
    analysis.complexity.time &&
    !analysis.complexity.time.startsWith('N/A') &&
    !analysis.complexity.time.toLowerCase().includes('not applicable')
  );

  // Format steps for "How it works"
  const workflowSteps = analysis.logic_workflow
    ? analysis.logic_workflow.split('\n').filter(s => s.trim())
    : [];

  const toggleExplore = (mode) => {
    setActiveExplore(activeExplore === mode ? null : mode);
  };

  return (
    <section className="results-panel">
      {/* Top Header with title, mode pill, and close button */}
      <div className="analysis-panel-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '0.02em' }}>
            Code Analysis
          </span>
          {analysis.mode && (
            <span className="code-inline" style={{ fontSize: '0.68rem', textTransform: 'uppercase', padding: '1px 5px' }}>
              {analysis.mode}
            </span>
          )}
        </div>
        {onClose && (
          <button
            className="btn-tool-clean"
            onClick={onClose}
            title="Close analysis panel"
            style={{ padding: '2px 8px', fontSize: '0.8rem', lineHeight: 1 }}
          >
            ✕
          </button>
        )}
      </div>

      {/* 1. OVERVIEW */}
      <div className="result-section">
        <div className="section-label">Overview</div>
        <div className="section-text">{analysis.overview}</div>

        {analysis.learning_takeaway && (
          <div className="takeaway-quote" style={{ marginTop: '6px' }}>
            {analysis.learning_takeaway}
          </div>
        )}
      </div>

      {/* 2. HOW IT WORKS */}
      <div className="result-section">
        <div className="section-label">How It Works</div>
        {workflowSteps.length > 0 ? (
          <div className="steps-list">
            {workflowSteps.map((step, idx) => {
              // Strip leading number if present (e.g. "1. ")
              const cleaned = step.replace(/^\d+\.\s*/, '').replace(/\*\*/g, '');
              return (
                <div key={idx} className="step-item">
                  <span className="step-num">{idx + 1}</span>
                  <span>{cleaned}</span>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="section-text">{analysis.logic_workflow}</div>
        )}
      </div>

      {/* 3. EXPECTED INPUTS AND OUTPUTS (CORE SECTION) */}
      <div className="result-section">
        <div className="section-label">Expected Inputs & Outputs</div>
        {analysis.expected_io ? (
          <div className="io-structured-card">
            <div className="io-grid-detailed">
              {/* Inputs Subcard */}
              <div className="io-subcard">
                <div className="io-subcard-title">
                  <span>Input Specification</span>
                  <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'none' }}>
                    {analysis.expected_io.input_source}
                  </span>
                </div>
                <div className="io-meta-row">
                  <div>
                    <span className="io-meta-label">Expected Type: </span>
                    <code className="code-inline" style={{ fontSize: '0.76rem' }}>{analysis.expected_io.input_type}</code>
                  </div>
                  <div>
                    <span className="io-meta-label">Format: </span>
                    <span>{analysis.expected_io.input_format}</span>
                  </div>
                  <div>
                    <span className="io-meta-label">Range / Bounds: </span>
                    <span>{analysis.expected_io.input_range}</span>
                  </div>
                </div>
                {analysis.expected_io.sample_input && (
                  <div>
                    <span className="io-meta-label" style={{ display: 'block', marginBottom: '3px' }}>
                      Representative Sample Input:
                    </span>
                    <div className="io-sample-box">{analysis.expected_io.sample_input}</div>
                  </div>
                )}
              </div>

              {/* Outputs Subcard */}
              <div className="io-subcard">
                <div className="io-subcard-title">
                  <span>Output Specification</span>
                  <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'none' }}>
                    {analysis.expected_io.output_mechanism}
                  </span>
                </div>
                <div className="io-meta-row">
                  <div>
                    <span className="io-meta-label">Output Type: </span>
                    <code className="code-inline" style={{ fontSize: '0.76rem' }}>{analysis.expected_io.output_type}</code>
                  </div>
                  <div>
                    <span className="io-meta-label">Delivery Mechanism: </span>
                    <span>{analysis.expected_io.output_mechanism}</span>
                  </div>
                </div>
                {analysis.expected_io.sample_output && (
                  <div>
                    <span className="io-meta-label" style={{ display: 'block', marginBottom: '3px' }}>
                      Expected Output for Sample:
                    </span>
                    <div className="io-sample-box">{analysis.expected_io.sample_output}</div>
                  </div>
                )}
              </div>
            </div>

            {/* Input-to-Output Mapping */}
            {analysis.expected_io.relationship && (
              <div className="io-relationship-box">
                <div style={{ fontWeight: 600, color: 'var(--accent-pink-soft)', marginBottom: '3px' }}>
                  Input-to-Output Relationship:
                </div>
                <div>{analysis.expected_io.relationship}</div>
                {analysis.expected_io.explanation && (
                  <div style={{ marginTop: '4px', color: 'var(--text-muted)', fontSize: '0.76rem' }}>
                    {analysis.expected_io.explanation}
                  </div>
                )}
              </div>
            )}

            {/* Execution Comparison Feature */}
            {analysis.expected_io.sample_input && code && (
              <div className="verify-sample-bar">
                <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                  <strong>Verify Algorithm:</strong> Run with sample input <code>{analysis.expected_io.sample_input}</code> to test live output match.
                </div>
                <button
                  className="verify-btn"
                  onClick={handleVerifySample}
                  disabled={isVerifying}
                  title="Execute code using the representative sample input"
                >
                  <IconPlay size={12} />
                  <span>{isVerifying ? 'Executing...' : 'Verify with Execution'}</span>
                </button>
              </div>
            )}

            {verifyResult && (
              <div className={`verify-result ${verifyResult.is_match ? 'match' : 'diff'}`}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontWeight: 600 }}>
                  <span>{verifyResult.is_match ? '✓ Execution Matches Expected Result' : '⚠ Execution Differs from Expected'}</span>
                  {verifyResult.execution_time_ms !== undefined && (
                    <span style={{ fontSize: '0.7rem' }}>{verifyResult.execution_time_ms}ms</span>
                  )}
                </div>
                <div>{verifyResult.notes}</div>
                {verifyResult.actual_output && (
                  <div style={{ marginTop: '4px' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Actual stdout:</span>
                    <pre className="io-sample-box" style={{ marginTop: '2px', padding: '4px 6px', fontSize: '0.75rem' }}>
                      {verifyResult.actual_output}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="io-grid">
            <div className="io-card">
              <span className="io-label">Inputs</span>
              <div className="io-text">{analysis.inputs || 'No external inputs required.'}</div>
            </div>
            <div className="io-card">
              <span className="io-label">Outputs</span>
              <div className="io-text">{analysis.outputs || 'No direct terminal output detected.'}</div>
            </div>
          </div>
        )}
      </div>

      {/* 4. ISSUES FOUND (Rendered ONLY if issues exist) */}
      {hasIssues && (
        <div className="result-section">
          <div className="section-label" style={{ color: 'var(--status-error-text)' }}>
            Issues Found ({diagnostics.length})
          </div>
          <div className="issues-container">
            {diagnostics.map((diag, idx) => (
              <div key={diag.id || idx} className="issue-item">
                <div className="issue-header">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span className={`issue-badge ${diag.severity}`}>
                      {diag.severity}
                    </span>
                    <span className="issue-title">{diag.title}</span>
                  </div>
                  {diag.line_number && (
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      Line {diag.line_number}
                    </span>
                  )}
                </div>

                <div className="issue-explanation">{diag.explanation}</div>

                {diag.recommended_correction && (
                  <div className="issue-fix">
                    <strong>Recommended Fix: </strong>
                    {diag.recommended_correction}
                  </div>
                )}
              </div>
            ))}

            {/* Suggested Corrected Code */}
            {analysis.suggested_code && (
              <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid rgba(239, 68, 68, 0.2)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    Suggested Corrected Code:
                  </span>
                  <div style={{ display: 'flex', gap: '6px' }}>
                    <button
                      className="btn-tool-clean"
                      onClick={() => handleCopyFix(analysis.suggested_code)}
                      title="Copy corrected code"
                    >
                      {copiedFix ? <IconCheck size={12} /> : <IconCopy size={12} />}
                      <span>{copiedFix ? 'Copied' : 'Copy'}</span>
                    </button>
                    {onApplySuggestedCode && (
                      <button
                        className="btn-tool-clean"
                        onClick={() => onApplySuggestedCode(analysis.suggested_code)}
                        style={{ color: 'var(--accent-pink-soft)', borderColor: 'var(--border-pink)' }}
                        title="Apply fix to editor"
                      >
                        Apply Fix
                      </button>
                    )}
                  </div>
                </div>

                <pre className="code-inline" style={{ display: 'block', padding: '8px 10px', overflowX: 'auto', whiteSpace: 'pre' }}>
                  {analysis.suggested_code}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 5. VIVA & EXAM PREPARATION */}
      {analysis.viva_questions && analysis.viva_questions.length > 0 && (
        <details className="details-collapsible" style={{ marginTop: '8px' }}>
          <summary>Academic Viva & Exam Preparation ({analysis.viva_questions.length})</summary>
          <div className="details-content" style={{ marginTop: '8px' }}>
            <div className="viva-list">
              {analysis.viva_questions.map((vq, idx) => (
                <div key={idx} className="viva-card">
                  <div className="viva-header">
                    <span className="viva-question">Q{idx + 1}: {vq.question}</span>
                    {vq.concept && <span className="viva-concept-pill">{vq.concept}</span>}
                  </div>
                  <div className="viva-answer">
                    <strong>Model Answer: </strong>{vq.answer}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </details>
      )}

      {/* 6. LIMITATIONS AND EDGE CASES */}
      {analysis.limitations?.length > 0 && (
        <details className="details-collapsible">
          <summary>Limitations & Edge Cases ({analysis.limitations.length})</summary>
          <div className="details-content">
            <ul style={{ paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '3px' }}>
              {analysis.limitations.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
        </details>
      )}

      {/* 7. EXPLORE FURTHER */}
      {(hasLineByLine || hasDryRun || hasComplexity) && (
        <div className="explore-further-container">
          <div className="section-label">Explore Further</div>
          <div className="explore-buttons-row">
            {hasLineByLine && (
              <button
                className={`btn-explore-clean ${activeExplore === 'linebyline' ? 'active' : ''}`}
                onClick={() => toggleExplore('linebyline')}
              >
                <IconBook size={13} />
                <span>Line-by-line explanation</span>
              </button>
            )}

            {hasDryRun && (
              <button
                className={`btn-explore-clean ${activeExplore === 'dryrun' ? 'active' : ''}`}
                onClick={() => toggleExplore('dryrun')}
              >
                <IconPlay size={13} />
                <span>Dry run</span>
              </button>
            )}

            {hasComplexity && (
              <button
                className={`btn-explore-clean ${activeExplore === 'complexity' ? 'active' : ''}`}
                onClick={() => toggleExplore('complexity')}
              >
                <IconCode size={13} />
                <span>Complexity analysis</span>
              </button>
            )}
          </div>

          {/* Action Drawer: Line-by-Line */}
          {activeExplore === 'linebyline' && (
            <div className="explore-drawer">
              <table className="table-minimal">
                <thead>
                  <tr>
                    <th style={{ width: '45px' }}>Line</th>
                    <th style={{ width: '38%' }}>Code</th>
                    <th>Explanation</th>
                  </tr>
                </thead>
                <tbody>
                  {analysis.line_by_line?.map((item) => (
                    <tr key={item.line_number}>
                      <td style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        #{item.line_number}
                      </td>
                      <td>
                        <code className="code-inline">{item.code_segment}</code>
                      </td>
                      <td style={{ color: 'var(--text-secondary)' }}>
                        {item.explanation}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Action Drawer: Dry Run */}
          {activeExplore === 'dryrun' && (
            <div className="explore-drawer">
              {analysis.dry_run?.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {analysis.dry_run.map((step) => (
                    <div
                      key={step.step}
                      style={{
                        padding: '8px 10px',
                        borderRadius: 'var(--radius-sm)',
                        backgroundColor: 'var(--bg-panel)',
                        border: '1px solid var(--border-subtle)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '4px'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                          Step {step.step}: {step.action}
                        </span>
                      </div>

                      {step.state && Object.keys(step.state).length > 0 && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '2px' }}>
                          {Object.entries(step.state).map(([k, v]) => (
                            <span key={k} className="code-inline" style={{ fontSize: '0.72rem' }}>
                              {k}: {v}
                            </span>
                          ))}
                        </div>
                      )}

                      {step.notes && (
                        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                          {step.notes}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  {analysis.logic_workflow}
                </div>
              )}
            </div>
          )}

          {/* Action Drawer: Complexity Analysis */}
          {activeExplore === 'complexity' && (
            <div className="explore-drawer">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '8px' }}>
                <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-panel)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Time Complexity</div>
                  <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--accent-pink-soft)', fontFamily: 'var(--font-mono)' }}>
                    {analysis.complexity?.time || 'O(1)'}
                  </div>
                </div>
                <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-panel)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Space Complexity</div>
                  <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--accent-pink-soft)', fontFamily: 'var(--font-mono)' }}>
                    {analysis.complexity?.space || 'O(1)'}
                  </div>
                </div>
              </div>
              {analysis.complexity?.explanation && (
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  {analysis.complexity.explanation}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
