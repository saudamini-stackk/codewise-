import React, { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import CodeEditor from './components/CodeEditor';
import AnalysisView from './components/AnalysisView';
import ChatAssistant from './components/ChatAssistant';
import AboutModal from './components/AboutModal';
import BackupModal from './components/BackupModal';
import ResizableDivider from './components/ResizableDivider';
import LoginPage from './components/LoginPage';
import { IconCode } from './components/Icons';
import { api } from './services/api';
import { getLanguageFromFilename, isRunnable, syncCapabilities } from './utils/languageCapabilities';

export default function App() {
  // Authentication State
  const [currentUser, setCurrentUser] = useState(null);
  const [isAuthChecking, setIsAuthChecking] = useState(true);

  // Session & Workspace State
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [currentThreadTitle, setCurrentThreadTitle] = useState('main.py');
  const [searchQuery, setSearchQuery] = useState('');

  // Code Editor State
  const [code, setCode] = useState('');
  const [language, setLanguage] = useState('python');
  const [filename, setFilename] = useState('main.py');

  // Autosave State
  const [saveStatus, setSaveStatus] = useState('saved'); // 'saved' | 'saving' | 'unsaved'
  const autosaveTimerRef = useRef(null);
  const lastSavedCodeRef = useRef('');

  // Default panel layout constants
  const DEFAULT_SIDEBAR_WIDTH = 250;
  const DEFAULT_EDITOR_RATIO = 50;
  const DEFAULT_CONSOLE_HEIGHT = 180;
  const DEFAULT_ASSISTANT_HEIGHT = 340;

  // Sidebar Collapsed State (synchronized with Explorer)
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // Resizable Panel Sizes (persisted in localStorage with validation & clamping)
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    try {
      const saved = localStorage.getItem('codewise_sidebar_width');
      const val = Number(saved);
      if (!isNaN(val) && val >= 180 && val <= 420) {
        return val;
      }
      return DEFAULT_SIDEBAR_WIDTH;
    } catch {
      return DEFAULT_SIDEBAR_WIDTH;
    }
  });

  const [editorRatio, setEditorRatio] = useState(() => {
    try {
      const saved = localStorage.getItem('codewise_editor_ratio');
      const val = Number(saved);
      if (!isNaN(val) && val >= 25 && val <= 75) {
        return val;
      }
      return DEFAULT_EDITOR_RATIO;
    } catch {
      return DEFAULT_EDITOR_RATIO;
    }
  });

  const [consoleHeight, setConsoleHeight] = useState(() => {
    try {
      const saved = localStorage.getItem('codewise_console_height');
      const val = Number(saved);
      if (!isNaN(val) && val >= 80 && val <= 450) {
        return val;
      }
      return DEFAULT_CONSOLE_HEIGHT;
    } catch {
      return DEFAULT_CONSOLE_HEIGHT;
    }
  });

  const [assistantHeight, setAssistantHeight] = useState(() => {
    try {
      const saved = localStorage.getItem('codewise_assistant_height');
      const val = Number(saved);
      if (!isNaN(val) && val >= 280 && val <= 800) {
        return val;
      }
      return DEFAULT_ASSISTANT_HEIGHT;
    } catch {
      return DEFAULT_ASSISTANT_HEIGHT;
    }
  });

  // Execution Console State
  const [isRunning, setIsRunning] = useState(false);
  const [executionResult, setExecutionResult] = useState(null);
  const [isConsoleOpen, setIsConsoleOpen] = useState(false);
  const [stdinInput, setStdinInput] = useState('');

  // Analysis & Version State
  const [analysis, setAnalysis] = useState(null);
  const [isAnalysisVisible, setIsAnalysisVisible] = useState(false);
  const [versions, setVersions] = useState([]);
  const [activeVersionNumber, setActiveVersionNumber] = useState(1);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // Chat State
  const [messages, setMessages] = useState([]);
  const [isSendingChat, setIsSendingChat] = useState(false);

  // System & Meta
  const [systemStatus, setSystemStatus] = useState(null);
  const [samples, setSamples] = useState([]);

  // Modals
  const [isAboutOpen, setIsAboutOpen] = useState(false);
  const [isBackupOpen, setIsBackupOpen] = useState(false);

  // Check authentication session on initial app load
  useEffect(() => {
    const token = localStorage.getItem('codewise_token');
    if (!token) {
      setIsAuthChecking(false);
      return;
    }

    api.getMe()
      .then((user) => {
        setCurrentUser(user);
      })
      .catch(() => {
        localStorage.removeItem('codewise_token');
        setCurrentUser(null);
      })
      .finally(() => {
        setIsAuthChecking(false);
      });
  }, []);

  // Listen for unauthorized events to smoothly redirect to login
  useEffect(() => {
    const handleUnauthorized = () => {
      setCurrentUser(null);
    };
    window.addEventListener('codewise_auth_unauthorized', handleUnauthorized);
    return () => window.removeEventListener('codewise_auth_unauthorized', handleUnauthorized);
  }, []);

  // Load workspace data whenever authenticated user is active
  useEffect(() => {
    if (!currentUser) return;

    async function init() {
      try {
        const [statusData, samplesData, sessionsData, capData] = await Promise.all([
          api.getSystemStatus(),
          api.getSamples(),
          api.listSessions(),
          api.getCapabilities().catch(() => null)
        ]);
        setSystemStatus(statusData);
        setSamples(samplesData);
        setSessions(sessionsData);
        if (capData) {
          syncCapabilities(capData);
        }

        if (sessionsData.length > 0) {
          loadSession(sessionsData[0].id);
        } else if (samplesData.length > 0) {
          loadSample(samplesData[0], true);
        } else {
          handleNewSession();
        }
      } catch (err) {
        console.error('Failed to initialize workspace data', err);
      }
    }
    init();
  }, [currentUser]);

  // Authentication Handlers
  const handleLoginSuccess = (user, token) => {
    setCurrentUser(user);
  };

  const handleLogout = async () => {
    try {
      await api.logout();
    } catch {
      // Ignore network error on logout
    } finally {
      localStorage.removeItem('codewise_token');
      setCurrentUser(null);
      setSessions([]);
      setCurrentSessionId(null);
      setCode('');
      setAnalysis(null);
      setIsAnalysisVisible(false);
      setVersions([]);
      setMessages([]);
      setExecutionResult(null);
    }
  };

  // Fetch / refresh sessions list
  const refreshSessions = async (query = searchQuery) => {
    try {
      const data = await api.listSessions(query);
      setSessions(data);
    } catch (err) {
      console.error('Failed to list sessions', err);
    }
  };

  const handleSearchChange = (q) => {
    setSearchQuery(q);
    refreshSessions(q);
  };

  // Load a file / session
  const loadSession = async (sessionId, keepAnalysisOpen = false) => {
    try {
      const sess = await api.getSession(sessionId);
      setCurrentSessionId(sess.id);
      setCurrentThreadTitle(sess.filename || sess.title);
      setFilename(sess.filename);
      setLanguage(sess.language || 'python');
      setVersions(sess.versions || []);
      setMessages(sess.messages || []);

      if (sess.versions && sess.versions.length > 0) {
        const latest = sess.versions[sess.versions.length - 1];
        setCode(latest.code);
        setLanguage(latest.language);
        setFilename(latest.filename);
        setActiveVersionNumber(latest.version_number);
        if (keepAnalysisOpen) {
          setAnalysis(latest.analysis);
          setIsAnalysisVisible(true);
        } else {
          setAnalysis(null);
          setIsAnalysisVisible(false);
        }
        setExecutionResult(latest.execution_result || null);
        lastSavedCodeRef.current = latest.code;
        setSaveStatus('saved');
      } else {
        if (!keepAnalysisOpen) {
          setAnalysis(null);
          setIsAnalysisVisible(false);
        }
      }
    } catch (err) {
      console.error('Failed to load file', err);
    }
  };

  // Code change with debounced autosave
  const handleCodeChange = (newCode) => {
    setCode(newCode);

    if (!currentSessionId) return;

    if (newCode !== lastSavedCodeRef.current) {
      setSaveStatus('unsaved');

      if (autosaveTimerRef.current) {
        clearTimeout(autosaveTimerRef.current);
      }

      autosaveTimerRef.current = setTimeout(async () => {
        try {
          setSaveStatus('saving');
          const savedVer = await api.saveFileVersion(currentSessionId, newCode, language, filename);
          lastSavedCodeRef.current = newCode;
          setSaveStatus('saved');

          setVersions((prev) => {
            const exists = prev.some((v) => v.id === savedVer.id);
            if (exists) {
              return prev.map((v) => (v.id === savedVer.id ? savedVer : v));
            } else {
              return [...prev, savedVer];
            }
          });
          setActiveVersionNumber(savedVer.version_number);
          refreshSessions();
        } catch (err) {
          console.error('Autosave failed:', err);
          setSaveStatus('unsaved');
        }
      }, 1500);
    }
  };

  // Switch between revisions
  const handleSelectVersion = (versionItem) => {
    setCode(versionItem.code);
    setLanguage(versionItem.language);
    setFilename(versionItem.filename);
    setActiveVersionNumber(versionItem.version_number);
    setAnalysis(null);
    setIsAnalysisVisible(false);
    setExecutionResult(versionItem.execution_result || null);
    lastSavedCodeRef.current = versionItem.code;
    setSaveStatus('saved');
  };

  // Restore earlier revision as a new latest revision
  const handleRestoreVersion = async (targetVersionNumber) => {
    if (!currentSessionId) return;
    try {
      const restored = await api.restoreFileVersion(currentSessionId, { version_number: targetVersionNumber });
      await refreshSessions();
      await loadSession(currentSessionId);
    } catch (err) {
      alert(`Failed to restore version: ${err.message}`);
    }
  };

  // Create a brand new file
  const handleCreateNewFile = async (newFilename) => {
    const lang = getLanguageFromFilename(newFilename);
    const runnable = isRunnable(lang);
    try {
      const created = await api.createFile({
        filename: newFilename,
        language: lang,
        code: '',
        is_runnable: runnable,
        title: newFilename
      });
      await refreshSessions();
      await loadSession(created.id);
    } catch (err) {
      alert(`Failed to create file: ${err.message}`);
    }
  };

  // Start new clean untitled session
  const handleNewSession = () => {
    handleCreateNewFile('main.py');
  };

  // Duplicate file
  const handleDuplicateSession = async (sessionId) => {
    try {
      const dup = await api.duplicateFile(sessionId);
      await refreshSessions();
      await loadSession(dup.id);
    } catch (err) {
      alert(`Failed to duplicate file: ${err.message}`);
    }
  };

  // Rename file
  const handleRenameSession = async (sessionId, newFilename) => {
    try {
      const lang = getLanguageFromFilename(newFilename);
      await api.renameFile(sessionId, newFilename, newFilename);
      if (sessionId === currentSessionId) {
        setCurrentThreadTitle(newFilename);
        setFilename(newFilename);
        setLanguage(lang);
      }
      refreshSessions();
    } catch (err) {
      alert(`Failed to rename: ${err.message}`);
    }
  };

  // Delete file
  const handleDeleteSession = async (sessionId) => {
    try {
      await api.deleteSession(sessionId);
      const remaining = sessions.filter((s) => s.id !== sessionId);
      setSessions(remaining);
      if (currentSessionId === sessionId) {
        if (remaining.length > 0) {
          loadSession(remaining[0].id);
        } else {
          handleNewSession();
        }
      }
    } catch (err) {
      alert(`Failed to delete file: ${err.message}`);
    }
  };

  // Run code safely in isolated sandbox
  const handleRunCode = async () => {
    if (!code.trim() || isRunning) return;
    setIsRunning(true);
    setIsConsoleOpen(true);
    try {
      let targetLang = language;
      if (targetLang === 'auto') {
        try {
          const det = await api.detectLanguage(code, filename);
          targetLang = det.detected_language || 'python';
        } catch {
          targetLang = 'python';
        }
      }
      const activeVer = versions.find((v) => v.version_number === activeVersionNumber);
      const res = await api.runCode(code, targetLang, stdinInput || '', currentSessionId, activeVer?.id);
      setExecutionResult(res);

      if (activeVer) {
        setVersions((prev) =>
          prev.map((v) =>
            v.id === activeVer.id ? { ...v, execution_result: res } : v
          )
        );
      }
    } catch (err) {
      setExecutionResult({
        stdout: '',
        stderr: `Execution error: ${err.message}`,
        exit_code: 1,
        execution_time_ms: 0,
        status: 'error'
      });
    } finally {
      setIsRunning(false);
    }
  };

  const handleClearConsole = () => {
    setExecutionResult(null);
  };

  // Load sample program
  const loadSample = (sample, isInitial = false) => {
    setCode(sample.code);
    setLanguage(sample.language);
    setFilename(sample.filename);
    lastSavedCodeRef.current = sample.code;
    setSaveStatus('saved');
    setAnalysis(null);
    setIsAnalysisVisible(false);
    setVersions([]);
    setActiveVersionNumber(1);
    setMessages([]);
    setCurrentSessionId(null);
    setCurrentThreadTitle(sample.title);
  };

  // Run code analysis
  const handleAnalyze = async () => {
    if (!code.trim() || isAnalyzing) return;
    setIsAnalyzing(true);
    setIsAnalysisVisible(true);
    setAnalysis(null);
    try {
      const activeVer = versions.find((v) => v.version_number === activeVersionNumber);
      const result = await api.analyzeCode({
        code,
        language,
        filename,
        session_id: currentSessionId,
        code_version_id: activeVer?.id
      });

      if (!currentSessionId && result.session_id) {
        await refreshSessions();
        await loadSession(result.session_id, true);
      } else {
        setAnalysis(result.analysis);
        setIsAnalysisVisible(true);
        if (currentSessionId) {
          await refreshSessions();
          try {
            const detail = await api.getSession(currentSessionId);
            if (detail && detail.versions) {
              setVersions(detail.versions);
              const matchingVer = detail.versions.find((v) => v.id === result.code_version_id);
              if (matchingVer) {
                setActiveVersionNumber(matchingVer.version_number);
              }
            }
          } catch (e) {
            console.error("Failed to refresh session versions:", e);
          }
        } else if (activeVer) {
          setVersions((prev) =>
            prev.map((v) =>
              v.id === activeVer.id ? { ...v, analysis: result.analysis } : v
            )
          );
        }
      }
    } catch (err) {
      alert(`Analysis error: ${err.message}`);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Send Chat message
  const handleSendMessage = async (text) => {
    if (!currentSessionId) {
      alert("Please create or analyse a file first to chat.");
      return;
    }
    setIsSendingChat(true);

    const tempUserMsg = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: text,
      created_at: new Date().toISOString()
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const activeVersion = versions.find((v) => v.version_number === activeVersionNumber);
      const assistantMsg = await api.sendChatMessage(
        currentSessionId,
        text,
        activeVersion?.id
      );
      setMessages((prev) => [...prev, assistantMsg]);
      refreshSessions();
    } catch (err) {
      alert(`Chat error: ${err.message}`);
      setMessages((prev) => prev.filter((m) => m.id !== tempUserMsg.id));
    } finally {
      setIsSendingChat(false);
    }
  };

  // Apply suggested code to editor
  const handleApplySuggestedCode = (suggestedCode) => {
    if (!suggestedCode) return;
    handleCodeChange(suggestedCode);
  };

  // Reset layout sizes to default
  const handleResetLayout = () => {
    setSidebarWidth(DEFAULT_SIDEBAR_WIDTH);
    setEditorRatio(DEFAULT_EDITOR_RATIO);
    setConsoleHeight(DEFAULT_CONSOLE_HEIGHT);
    setAssistantHeight(DEFAULT_ASSISTANT_HEIGHT);
    setIsSidebarCollapsed(false);
    setIsAnalysisVisible(false);
    setAnalysis(null);
    try {
      localStorage.removeItem('codewise_sidebar_width');
      localStorage.removeItem('codewise_editor_ratio');
      localStorage.removeItem('codewise_console_height');
      localStorage.removeItem('codewise_assistant_height');
    } catch {}
  };

  // Resizers
  const handleSidebarResize = (e) => {
    const newW = e.clientX;
    const clamped = Math.max(180, Math.min(newW, 420));
    setSidebarWidth(clamped);
    try {
      localStorage.setItem('codewise_sidebar_width', String(clamped));
    } catch {}
  };

  const handleSidebarReset = () => {
    setSidebarWidth(DEFAULT_SIDEBAR_WIDTH);
    try {
      localStorage.removeItem('codewise_sidebar_width');
    } catch {}
  };

  const handleEditorSplitResize = (e) => {
    const container = document.querySelector('.workspace-panels');
    if (!container) return;
    const rect = container.getBoundingClientRect();
    const offsetX = e.clientX - rect.left;
    const pct = (offsetX / rect.width) * 100;
    const clamped = Math.max(25, Math.min(pct, 75));
    setEditorRatio(clamped);
    try {
      localStorage.setItem('codewise_editor_ratio', String(clamped));
    } catch {}
  };

  const handleEditorSplitReset = () => {
    setEditorRatio(DEFAULT_EDITOR_RATIO);
    try {
      localStorage.removeItem('codewise_editor_ratio');
    } catch {}
  };

  if (isAuthChecking) {
    return (
      <div className="auth-loading-screen">
        <div className="auth-brand-logo" style={{ width: '48px', height: '48px' }}>
          <IconCode size={24} className="auth-brand-icon" />
        </div>
        <div style={{ fontSize: '0.86rem', color: 'var(--text-secondary)' }}>Loading codewise...</div>
      </div>
    );
  }

  if (!currentUser) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="app-container">
      {/* 1. File Explorer (Left Region) */}
      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={loadSession}
        onCreateNewFile={handleCreateNewFile}
        onRenameSession={handleRenameSession}
        onDeleteSession={handleDeleteSession}
        onDuplicateSession={handleDuplicateSession}
        searchQuery={searchQuery}
        onSearchChange={handleSearchChange}
        onResetLayout={handleResetLayout}
        onOpenAbout={() => setIsAboutOpen(true)}
        onOpenBackup={() => setIsBackupOpen(true)}
        collapsed={isSidebarCollapsed}
        setCollapsed={setIsSidebarCollapsed}
        width={sidebarWidth}
      />

      {/* Draggable Divider between Sidebar and Main Workspace */}
      {!isSidebarCollapsed && (
        <ResizableDivider
          direction="horizontal"
          onResize={handleSidebarResize}
          onReset={handleSidebarReset}
          title="Drag to resize File Explorer, double-click to reset"
        />
      )}

      {/* Main Workspace */}
      <div className="main-wrapper">
        {/* Top Header */}
        <Header
          currentThreadTitle={currentThreadTitle}
          systemStatus={systemStatus}
          samples={samples}
          currentUser={currentUser}
          onLogout={handleLogout}
          onLoadSample={loadSample}
          onNewThread={handleNewSession}
          onResetLayout={handleResetLayout}
          onOpenAbout={() => setIsAboutOpen(true)}
          onOpenBackup={() => setIsBackupOpen(true)}
        />

        {/* Resizable Panels: Code Editor (Center) & Analysis (Right) */}
        <div className="workspace-panels">
          <div
            className="editor-container"
            style={{
              width: isAnalysisVisible ? `calc(${editorRatio}% - 2px)` : '100%',
              flex: isAnalysisVisible ? undefined : 1,
              display: 'flex',
              flexDirection: 'column',
              minWidth: '280px',
              minHeight: 0
            }}
          >
            <CodeEditor
              code={code}
              setCode={handleCodeChange}
              language={language}
              setLanguage={setLanguage}
              filename={filename}
              setFilename={setFilename}
              onAnalyze={handleAnalyze}
              isAnalyzing={isAnalyzing}
              onRun={handleRunCode}
              isRunning={isRunning}
              executionResult={executionResult}
              onClearConsole={handleClearConsole}
              isConsoleOpen={isConsoleOpen}
              setIsConsoleOpen={setIsConsoleOpen}
              consoleHeight={consoleHeight}
              setConsoleHeight={setConsoleHeight}
              stdinInput={stdinInput}
              setStdinInput={setStdinInput}
              saveStatus={saveStatus}
              versions={versions}
              activeVersionNumber={activeVersionNumber}
              onSelectVersion={handleSelectVersion}
              onRestoreVersion={handleRestoreVersion}
            />
          </div>

          {/* Draggable Divider between Editor and Results */}
          {isAnalysisVisible && (
            <ResizableDivider
              direction="horizontal"
              onResize={handleEditorSplitResize}
              onReset={handleEditorSplitReset}
              title="Drag to resize editor & analysis panels, double-click to reset"
            />
          )}

          {isAnalysisVisible && (
            <div
              className="results-container"
              style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: '280px', minHeight: 0 }}
            >
              <AnalysisView
                analysis={analysis}
                isAnalyzing={isAnalyzing}
                onApplySuggestedCode={handleApplySuggestedCode}
                onClose={() => setIsAnalysisVisible(false)}
                code={code}
                language={language}
              />
            </div>
          )}
        </div>

        {/* Interactive Chat Assistant (with vertical resizer) */}
        <ChatAssistant
          messages={messages}
          onSendMessage={handleSendMessage}
          isSending={isSendingChat}
          currentSessionId={currentSessionId}
          assistantHeight={assistantHeight}
          setAssistantHeight={setAssistantHeight}
        />
      </div>

      {/* Modals */}
      <AboutModal
        isOpen={isAboutOpen}
        onClose={() => setIsAboutOpen(false)}
        systemStatus={systemStatus}
      />

      <BackupModal
        isOpen={isBackupOpen}
        onClose={() => setIsBackupOpen(false)}
        onRefreshSessions={refreshSessions}
      />
    </div>
  );
}
