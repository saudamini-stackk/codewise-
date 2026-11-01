import React, { useRef, useState, useMemo, useEffect } from 'react';
import {
  IconCopy,
  IconCheck,
  IconClear,
  IconUpload,
  IconSparkles,
  IconPlay,
  IconTerminal,
  IconEye,
  IconX,
  IconRefresh,
  IconMoreHorizontal,
  IconAlertTriangle
} from './Icons';
import LanguageDropdown from './LanguageDropdown';
import HtmlPreviewModal from './HtmlPreviewModal';
import ResizableDivider from './ResizableDivider';
import {
  isRunnable,
  hasLocalRuntime,
  isPreviewable,
  isDataOrDocument,
  getLanguageFromFilename,
  getLanguageCapability
} from '../utils/languageCapabilities';
import {
  detectLanguageClient,
  isLanguageMismatch,
  LANGUAGE_DISPLAY_NAMES
} from '../utils/languageDetector';

const EXT_MAP = {
  '.py': 'python', '.pyw': 'python',
  '.js': 'javascript', '.mjs': 'javascript', '.cjs': 'javascript',
  '.ts': 'typescript', '.mts': 'typescript', '.cts': 'typescript',
  '.jsx': 'jsx', '.tsx': 'tsx',
  '.java': 'java',
  '.c': 'c', '.h': 'c',
  '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp', '.hpp': 'cpp', '.hxx': 'cpp',
  '.cs': 'csharp',
  '.go': 'go',
  '.rs': 'rust',
  '.php': 'php', '.phtml': 'php',
  '.rb': 'ruby',
  '.kt': 'kotlin', '.kts': 'kotlin',
  '.swift': 'swift',
  '.sh': 'bash', '.bash': 'bash', '.zsh': 'bash',
  '.html': 'html', '.htm': 'html',
  '.css': 'css',
  '.scss': 'scss', '.sass': 'scss',
  '.sql': 'sql',
  '.json': 'json',
  '.xml': 'xml', '.svg': 'xml',
  '.yaml': 'yaml', '.yml': 'yaml',
  '.md': 'markdown', '.markdown': 'markdown',
  '.toml': 'toml'
};

export default function CodeEditor({
  code,
  setCode,
  language,
  setLanguage,
  filename,
  setFilename,
  onAnalyze,
  isAnalyzing,
  onRun,
  isRunning,
  executionResult,
  onClearConsole,
  isConsoleOpen,
  setIsConsoleOpen,
  consoleHeight = 180,
  setConsoleHeight,
  stdinInput,
  setStdinInput,
  saveStatus = 'saved', // 'saved' | 'saving' | 'unsaved'
  versions = [],
  activeVersionNumber,
  onSelectVersion,
  onRestoreVersion
}) {
  const [copied, setCopied] = useState(false);
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [isOverflowOpen, setIsOverflowOpen] = useState(false);
  const textareaRef = useRef(null);
  const lineNumbersRef = useRef(null);
  const fileInputRef = useRef(null);
  const overflowRef = useRef(null);

  // Close overflow menu on outside click
  useEffect(() => {
    if (!isOverflowOpen) return;
    function handleClickOutside(event) {
      if (overflowRef.current && !overflowRef.current.contains(event.target)) {
        setIsOverflowOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOverflowOpen]);

  const lines = code.split('\n');
  const lineCount = Math.max(lines.length, 1);

  // Debounced Language Detection State
  const [detectionResult, setDetectionResult] = useState(() =>
    detectLanguageClient(code, filename)
  );

  // Recheck language when code or filename changes, debounced by 250ms so alerts do not repeatedly fire while typing
  useEffect(() => {
    const timer = setTimeout(() => {
      setDetectionResult(detectLanguageClient(code, filename));
    }, 250);

    return () => clearTimeout(timer);
  }, [code, filename]);

  const detectedLanguage = detectionResult.language;
  const detectedConfidence = detectionResult.confidence;

  // Track dismissed mismatch alert for the current mismatch pair
  const [dismissedMismatch, setDismissedMismatch] = useState(null);
  const currentMismatchKey = language && detectedLanguage ? `${language}:${detectedLanguage}` : null;
  const isDismissed = Boolean(dismissedMismatch && dismissedMismatch === currentMismatchKey);

  // Show mismatch banner only when a specific language is manually chosen,
  // detected language is confident, and they genuinely differ.
  const showMismatchBanner = useMemo(() => {
    if (language === 'auto') return false;
    if (!detectedLanguage) return false;
    if (detectedConfidence !== 'high' && detectedConfidence !== 'medium') return false;
    if (!isLanguageMismatch(language, detectedLanguage)) return false;
    if (isDismissed) return false;
    return true;
  }, [language, detectedLanguage, detectedConfidence, isDismissed]);

  const handleSwitchLanguage = () => {
    if (detectedLanguage) {
      setLanguage(detectedLanguage);
      setDismissedMismatch(null);
    }
  };

  const handleDismissMismatch = () => {
    if (currentMismatchKey) {
      setDismissedMismatch(currentMismatchKey);
    }
  };

  const detectedDisplayName = detectedLanguage
    ? (LANGUAGE_DISPLAY_NAMES[detectedLanguage] || detectedLanguage)
    : '';
  const currentDisplayName = LANGUAGE_DISPLAY_NAMES[language] || language;

  // The effective language currently in use
  const effectiveLanguage = language === 'auto' ? (detectedLanguage || 'python') : language;

  // Central Capability Registry for effective language
  const capability = useMemo(
    () => getLanguageCapability(effectiveLanguage),
    [effectiveLanguage]
  );
  const canRun = capability.canRun;
  const canPreview = capability.canPreview;
  const isRuntimeMissing = capability.isRuntimeMissing;

  const maxVersionNumber = useMemo(() => {
    if (!versions || versions.length === 0) return 1;
    return Math.max(...versions.map((v) => v.version_number));
  }, [versions]);

  const isInspectingOldVersion = activeVersionNumber && activeVersionNumber < maxVersionNumber;

  const handleScroll = () => {
    if (textareaRef.current && lineNumbersRef.current) {
      lineNumbersRef.current.scrollTop = textareaRef.current.scrollTop;
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const start = e.target.selectionStart;
      const end = e.target.selectionEnd;
      const newCode = code.substring(0, start) + '    ' + code.substring(end);
      setCode(newCode);
      setTimeout(() => {
        if (textareaRef.current) {
          textareaRef.current.selectionStart = textareaRef.current.selectionEnd = start + 4;
        }
      }, 0);
    }
  };

  const handleCopy = async () => {
    if (!code) return;
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy', err);
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 250000) {
      alert("File is too large! Please upload a file smaller than 250KB.");
      return;
    }

    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result;
      if (typeof content === 'string') {
        setCode(content);
        setFilename(file.name);

        const lower = file.name.toLowerCase();
        if (lower === 'dockerfile' || lower.startsWith('dockerfile.')) {
          setLanguage('dockerfile');
          return;
        }

        const lastDot = lower.lastIndexOf('.');
        if (lastDot !== -1) {
          const ext = lower.slice(lastDot);
          if (EXT_MAP[ext]) {
            setLanguage(EXT_MAP[ext]);
          } else {
            setLanguage('auto');
          }
        }
      }
    };
    reader.readAsText(file);
    e.target.value = '';
  };

  // Drag resizer for Console height
  const handleConsoleResize = (e) => {
    if (!setConsoleHeight) return;
    const windowH = window.innerHeight;
    const newH = windowH - e.clientY;
    const clamped = Math.max(80, Math.min(newH, 450));
    setConsoleHeight(clamped);
    try {
      localStorage.setItem('codewise_console_height', String(clamped));
    } catch {}
  };

  const handleConsoleReset = () => {
    if (setConsoleHeight) {
      setConsoleHeight(180);
      try {
        localStorage.removeItem('codewise_console_height');
      } catch {}
    }
  };

  return (
    <section className="editor-panel">
      {/* Editor Toolbar - Clean and strictly within editor panel */}
      <div className="editor-toolbar">
        <div className="toolbar-left">
          {/* 1. Language Dropdown */}
          <LanguageDropdown
            language={language}
            setLanguage={setLanguage}
            detectedLanguage={detectedLanguage}
            detectedInfo={detectionResult}
            hasCode={Boolean(code && code.trim())}
          />

          {/* Hidden File Input for Upload */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            style={{ display: 'none' }}
            accept=".py,.js,.jsx,.ts,.tsx,.java,.cpp,.cc,.c,.cs,.go,.rs,.php,.rb,.kt,.swift,.html,.css,.scss,.sql,.json,.xml,.yaml,.yml,.md,.sh,.toml,Dockerfile,.txt"
          />

          {/* Filename Pill with Text Truncation */}
          {filename && (
            <div className="file-pill-clean" title={filename}>
              <span className="file-pill-text">{filename}</span>
              <button
                className="file-pill-close"
                onClick={() => setFilename(null)}
                title="Remove file reference"
              >
                <IconX size={11} />
              </button>
            </div>
          )}

          {/* Autosave Status Pill */}
          <div className="autosave-pill" title={`Autosave: ${saveStatus}`}>
            {saveStatus === 'saving' && (
              <span className="save-saving">
                <span className="spin-dot">⟳</span> Saving...
              </span>
            )}
            {saveStatus === 'saved' && (
              <span className="save-saved">
                <span className="status-dot green">●</span> Saved
              </span>
            )}
            {saveStatus === 'unsaved' && (
              <span className="save-unsaved">
                <span className="status-dot yellow">○</span> Unsaved
              </span>
            )}
          </div>
        </div>

        <div className="toolbar-right">
          {/* HTML & CSS Preview Button (Visible only when format is previewable) */}
          {canPreview && (
            <button
              className="btn-tool-preview"
              onClick={() => setIsPreviewOpen(true)}
              disabled={!code.trim()}
              title="Open sandboxed HTML & CSS Live Preview"
            >
              <IconEye size={13} className="preview-icon-pink" />
              <span>Preview</span>
            </button>
          )}

          {/* Explanation Pill when language supports execution in principle but runtime is unavailable on host */}
          {isRuntimeMissing && (
            <div
              className="runtime-unavailable-pill"
              title={capability.unavailableReason}
              role="status"
              aria-label={capability.unavailableReason}
            >
              <IconAlertTriangle size={12} className="runtime-warn-icon" />
              <span>{capability.shortUnavailableMessage}</span>
            </div>
          )}

          {/* Run Code Button (Visible ONLY when execution runtime is genuinely available) */}
          {canRun && (
            <button
              className="btn-run-code"
              onClick={onRun}
              disabled={isRunning || !code.trim()}
              title="Run code in isolated sandbox"
            >
              <IconPlay size={13} className="run-icon-pink" />
              <span>{isRunning ? 'Running...' : 'Run Code'}</span>
            </button>
          )}

          {/* Primary Action: ANALYSE CODE (Always visible) */}
          <button
            className="btn-primary-pink"
            onClick={onAnalyze}
            disabled={isAnalyzing || !code.trim()}
            title="Analyze code logic, structure, and errors"
          >
            <IconSparkles size={13} />
            <span>{isAnalyzing ? 'Analysing...' : 'Analyse Code'}</span>
          </button>

          {/* Overflow Menu (...) for Secondary Actions (Upload, Copy, Clear) */}
          <div className="toolbar-overflow-wrapper" ref={overflowRef}>
            <button
              className={`btn-tool-clean ${isOverflowOpen ? 'active' : ''}`}
              onClick={() => setIsOverflowOpen(!isOverflowOpen)}
              title="More actions (Upload, Copy, Clear)"
              aria-label="More actions"
            >
              <IconMoreHorizontal size={14} />
            </button>

            {isOverflowOpen && (
              <div className="toolbar-overflow-menu">
                <button
                  className="overflow-menu-item"
                  onClick={() => {
                    setIsOverflowOpen(false);
                    fileInputRef.current?.click();
                  }}
                  title="Upload source file or document"
                >
                  <IconUpload size={13} />
                  <span>Upload File</span>
                </button>
                <button
                  className="overflow-menu-item"
                  onClick={() => {
                    setIsOverflowOpen(false);
                    handleCopy();
                  }}
                  disabled={!code.trim()}
                  title="Copy code to clipboard"
                >
                  {copied ? <IconCheck size={13} /> : <IconCopy size={13} />}
                  <span>{copied ? 'Copied' : 'Copy Code'}</span>
                </button>
                <div className="overflow-menu-divider" />
                <button
                  className="overflow-menu-item text-danger"
                  onClick={() => {
                    setIsOverflowOpen(false);
                    setCode('');
                    setFilename(null);
                  }}
                  disabled={!code.trim()}
                  title="Clear editor contents"
                >
                  <IconClear size={13} />
                  <span>Clear Editor</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Revision Selector (Shown when multiple revisions exist) */}
      {versions.length > 1 && (
        <div className="revision-bar">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>Revisions:</span>
            <div className="revision-tabs">
              {versions.map((v) => (
                <button
                  key={v.id}
                  className={`revision-tab ${v.version_number === activeVersionNumber ? 'active' : ''}`}
                  onClick={() => onSelectVersion(v)}
                  title={`Revision ${v.version_number} (${v.language})`}
                >
                  v{v.version_number}
                  <span className="rev-lang-tag">.{v.language}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Restore Button when inspecting an earlier revision */}
          {isInspectingOldVersion && onRestoreVersion && (
            <button
              className="btn-restore-version"
              onClick={() => onRestoreVersion(activeVersionNumber)}
              title={`Restore v${activeVersionNumber} as current latest version`}
            >
              <IconRefresh size={11} />
              <span>Restore v{activeVersionNumber}</span>
            </button>
          )}
        </div>
      )}

      {/* Language Mismatch Warning Banner */}
      {showMismatchBanner && (
        <div className="lang-mismatch-banner" role="alert">
          <div className="mismatch-left">
            <span className="mismatch-icon">⚡</span>
            <span className="mismatch-text">
              This code looks like <strong>{detectedDisplayName}</strong>, but <strong>{currentDisplayName}</strong> is selected. Switch to {detectedDisplayName}?
            </span>
          </div>
          <div className="mismatch-actions">
            <button
              type="button"
              className="btn-mismatch-switch"
              onClick={handleSwitchLanguage}
            >
              Switch to {detectedDisplayName}
            </button>
            <button
              type="button"
              className="btn-mismatch-dismiss"
              onClick={handleDismissMismatch}
              title="Dismiss warning"
              aria-label="Dismiss warning"
            >
              <IconX size={13} />
            </button>
          </div>
        </div>
      )}

      {/* Editor Body */}
      <div className="editor-body">
        <div className="editor-line-numbers" ref={lineNumbersRef}>
          {Array.from({ length: lineCount }, (_, i) => (
            <div key={i + 1}>{i + 1}</div>
          ))}
        </div>

        <textarea
          ref={textareaRef}
          className="editor-textarea"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          onScroll={handleScroll}
          onKeyDown={handleKeyDown}
          placeholder="// Paste source code, markup, or configuration here, then click 'Analyse Code'..."
          spellCheck="false"
        />
      </div>

      {/* Execution Console (Visible ONLY for runnable formats) */}
      {canRun && (
        isConsoleOpen ? (
          <>
            {/* Draggable Divider between Code Editor and Execution Console */}
            <ResizableDivider
              direction="vertical"
              onResize={handleConsoleResize}
              onReset={handleConsoleReset}
              title="Drag to resize console height, double-click to reset"
            />

            <div
              className="execution-console"
              style={{ height: `${consoleHeight}px`, flexShrink: 0 }}
            >
              {/* Console Header: Single-row layout with strict 1 to 6 element order */}
              <div className="console-header">
                {/* 1. Terminal Icon and Execution Console Label */}
                <div className="console-brand">
                  <IconTerminal size={14} className="console-terminal-icon" />
                  <span className="console-title">Execution Console</span>
                </div>

                {/* Status indicator when code is currently executing */}
                {isRunning && (
                  <span className="console-pill console-pill-running">
                    <span className="pulse-dot"></span>
                    Running...
                  </span>
                )}

                {/* 2 & 3. Execution Exit Status and Execution Duration */}
                {!isRunning && executionResult && (
                  <div className="console-status-group">
                    {/* 2. Execution Exit Status */}
                    <span
                      className={`console-pill ${
                        executionResult.exit_code === 0
                          ? 'console-pill-success'
                          : 'console-pill-error'
                      }`}
                      title={`Process exited with code ${executionResult.exit_code}`}
                    >
                      {executionResult.exit_code === 0 ? '✓' : '✕'} Exit: {executionResult.exit_code}
                    </span>

                    {/* 3. Execution Duration */}
                    <span
                      className="console-pill console-pill-muted"
                      title={`Execution duration: ${executionResult.execution_time_ms} ms`}
                    >
                      ⚡ {executionResult.execution_time_ms} ms
                    </span>

                    {executionResult.status === 'timeout' && (
                      <span className="console-pill console-pill-error" title="Process exceeded execution time limit">
                        Timeout (5s)
                      </span>
                    )}

                    {executionResult.status === 'runtime_missing' && (
                      <span className="console-pill console-pill-warn" title="Compiler/runtime not installed on host">
                        Runtime Missing
                      </span>
                    )}
                  </div>
                )}

                {/* 4. Optional STDIN Input (occupies available remaining space) */}
                <div className="console-stdin-wrapper">
                  <input
                    type="text"
                    className="console-stdin-input"
                    placeholder="stdin input (optional)..."
                    value={stdinInput || ''}
                    onChange={(e) => setStdinInput(e.target.value)}
                    title="Input to pass to standard input (stdin)"
                  />
                </div>

                {/* 5. Clear Button */}
                <button
                  className="btn-console-tool"
                  onClick={onClearConsole}
                  title="Clear console output"
                >
                  <IconClear size={12} />
                  <span>Clear</span>
                </button>

                {/* 6. Close or Collapse Button */}
                <button
                  className="btn-console-tool btn-console-close"
                  onClick={() => setIsConsoleOpen(false)}
                  title="Collapse console"
                  aria-label="Collapse console"
                >
                  <IconX size={12} />
                </button>
              </div>

              {/* Console Output Body */}
              <div className="console-output-body">
                {isRunning ? (
                  <div className="console-loading">
                    <span className="pulse-text">Executing {effectiveLanguage} in isolated sandbox...</span>
                  </div>
                ) : executionResult ? (
                  <>
                    {executionResult.stdout && (
                      <pre className="console-stdout">{executionResult.stdout}</pre>
                    )}
                    {executionResult.stderr && (
                      <pre className="console-stderr">{executionResult.stderr}</pre>
                    )}
                    {!executionResult.stdout && !executionResult.stderr && (
                      <div className="console-empty">Program finished with exit code 0 (no output).</div>
                    )}
                  </>
                ) : (
                  <div className="console-empty">Console ready. Click &quot;Run Code&quot; to execute.</div>
                )}
              </div>
            </div>
          </>
        ) : (
          /* Collapsed Console Toggle Bar */
          <div className="console-collapsed-bar" onClick={() => setIsConsoleOpen(true)}>
            <div className="console-collapsed-label">
              <IconTerminal size={13} className="console-terminal-icon" />
              <span>Console</span>
              {executionResult && (
                <span
                  className={`console-pill-tiny ${
                    executionResult.exit_code === 0 ? 'success' : 'error'
                  }`}
                >
                  Exit: {executionResult.exit_code}
                </span>
              )}
            </div>
            <span className="console-collapsed-hint">Click to expand</span>
          </div>
        )
      )}

      {/* HTML & CSS Live Preview Modal */}
      <HtmlPreviewModal
        isOpen={isPreviewOpen}
        onClose={() => setIsPreviewOpen(false)}
        code={code}
        language={effectiveLanguage}
      />
    </section>
  );
}
