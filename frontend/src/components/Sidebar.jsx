import React, { useState } from 'react';
import {
  IconCode,
  IconPlus,
  IconSearch,
  IconTrash,
  IconEdit,
  IconChevronLeft,
  IconChevronRight,
  IconChevronDown,
  IconFileCode,
  IconFileText,
  IconDuplicate,
  IconRefresh
} from './Icons';
import { isRunnable, getLanguageFromFilename } from '../utils/languageCapabilities';

function formatTimestamp(isoString) {
  if (!isoString) return '';
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export default function Sidebar({
  sessions = [],
  currentSessionId,
  onSelectSession,
  onCreateNewFile,
  onRenameSession,
  onDeleteSession,
  onDuplicateSession,
  searchQuery,
  onSearchChange,
  onResetLayout,
  onOpenAbout,
  onOpenBackup,
  collapsed: propCollapsed,
  setCollapsed: propSetCollapsed,
  width = 250
}) {
  const [internalCollapsed, setInternalCollapsed] = useState(false);
  const collapsed = propCollapsed !== undefined ? propCollapsed : internalCollapsed;
  const setCollapsed = propSetCollapsed || setInternalCollapsed;
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editFilename, setEditFilename] = useState('');
  const [deleteConfirmId, setDeleteConfirmId] = useState(null);
  const [isDocsExpanded, setIsDocsExpanded] = useState(true);
  const [showNewFileInput, setShowNewFileInput] = useState(false);
  const [newFileName, setNewFileName] = useState('');

  // Partition sessions into runnable source files and non-runnable documents
  const filtered = sessions.filter((s) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    const fname = (s.filename || '').toLowerCase();
    const title = (s.title || '').toLowerCase();
    const lang = (s.language || '').toLowerCase();
    return fname.includes(q) || title.includes(q) || lang.includes(q);
  });

  const sourceFiles = filtered.filter((s) => s.is_runnable !== false);
  const documentFiles = filtered.filter((s) => s.is_runnable === false);

  const handleStartRename = (e, session) => {
    e.stopPropagation();
    setEditingSessionId(session.id);
    setEditFilename(session.filename || session.title);
  };

  const handleSaveRename = (e, sessionId) => {
    e.stopPropagation();
    if (editFilename.trim()) {
      onRenameSession(sessionId, editFilename.trim());
    }
    setEditingSessionId(null);
  };

  const handleDeleteClick = (e, sessionId) => {
    e.stopPropagation();
    setDeleteConfirmId(sessionId);
  };

  const handleConfirmDelete = (e, sessionId) => {
    e.stopPropagation();
    onDeleteSession(sessionId);
    setDeleteConfirmId(null);
  };

  const handleDuplicateClick = (e, sessionId) => {
    e.stopPropagation();
    if (onDuplicateSession) {
      onDuplicateSession(sessionId);
    }
  };

  const handleCreateFileSubmit = (e) => {
    e.preventDefault();
    const trimmed = newFileName.trim();
    if (trimmed) {
      onCreateNewFile(trimmed);
      setNewFileName('');
      setShowNewFileInput(false);
    }
  };

  const renderFileItem = (session) => {
    const isActive = session.id === currentSessionId;
    const isEditing = session.id === editingSessionId;
    const isDeleting = session.id === deleteConfirmId;
    const displayName = session.filename || session.title || 'untitled';
    const ext = displayName.includes('.') ? displayName.split('.').pop() : (session.language || 'code');

    return (
      <div
        key={session.id}
        className={`session-item ${isActive ? 'active' : ''}`}
        onClick={() => onSelectSession(session.id)}
        title={`${displayName} (v${session.version_count || 1})`}
      >
        {!collapsed ? (
          isEditing ? (
            <div style={{ display: 'flex', gap: '4px', width: '100%' }} onClick={(e) => e.stopPropagation()}>
              <input
                type="text"
                value={editFilename}
                onChange={(e) => setEditFilename(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSaveRename(e, session.id);
                  if (e.key === 'Escape') setEditingSessionId(null);
                }}
                autoFocus
                style={{
                  flex: 1,
                  backgroundColor: 'var(--bg-input)',
                  border: '1px solid var(--accent-pink)',
                  color: 'var(--text-primary)',
                  borderRadius: '4px',
                  padding: '2px 6px',
                  fontSize: '0.78rem',
                  outline: 'none'
                }}
              />
              <button
                className="btn-icon-subtle"
                onClick={(e) => handleSaveRename(e, session.id)}
                style={{ color: 'var(--accent-pink)' }}
                title="Save filename"
              >
                ✓
              </button>
            </div>
          ) : isDeleting ? (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                width: '100%',
                fontSize: '0.74rem',
                color: 'var(--status-error-text)'
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <span>Delete file?</span>
              <div style={{ display: 'flex', gap: '4px' }}>
                <button
                  onClick={(e) => handleConfirmDelete(e, session.id)}
                  style={{
                    background: 'var(--status-error-bg)',
                    border: '1px solid var(--status-error-border)',
                    color: 'var(--status-error-text)',
                    borderRadius: '4px',
                    padding: '1px 6px',
                    fontSize: '0.68rem',
                    cursor: 'pointer'
                  }}
                >
                  Yes
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setDeleteConfirmId(null);
                  }}
                  style={{
                    background: 'var(--bg-panel)',
                    border: '1px solid var(--border-subtle)',
                    color: 'var(--text-secondary)',
                    borderRadius: '4px',
                    padding: '1px 6px',
                    fontSize: '0.68rem',
                    cursor: 'pointer'
                  }}
                >
                  No
                </button>
              </div>
            </div>
          ) : (
            <>
              <div className="session-info">
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span className="file-ext-badge">.{ext}</span>
                  <div className="session-title" title={displayName}>{displayName}</div>
                </div>
                <div className="session-meta">
                  {session.version_count > 1 ? (
                    <span className="badge-version">v{session.version_count}</span>
                  ) : (
                    <span className="badge-version">v1</span>
                  )}
                  <span>{formatTimestamp(session.updated_at)}</span>
                </div>
              </div>

              <div className="session-actions">
                <button
                  className="btn-icon-subtle"
                  onClick={(e) => handleDuplicateClick(e, session.id)}
                  title="Duplicate file"
                >
                  <IconDuplicate size={12} />
                </button>
                <button
                  className="btn-icon-subtle"
                  onClick={(e) => handleStartRename(e, session)}
                  title="Rename file"
                >
                  <IconEdit size={12} />
                </button>
                <button
                  className="btn-icon-subtle"
                  onClick={(e) => handleDeleteClick(e, session.id)}
                  title="Delete file"
                >
                  <IconTrash size={12} />
                </button>
              </div>
            </>
          )
        ) : (
          <div style={{ margin: '0 auto' }} title={displayName}>
            <IconFileCode size={14} color={isActive ? "var(--accent-pink)" : "var(--text-muted)"} />
          </div>
        )}
      </div>
    );
  };

  return (
    <aside
      className={`sidebar ${collapsed ? 'collapsed' : ''}`}
      style={{ width: collapsed ? '56px' : `${width}px` }}
    >
      {/* Brand Header */}
      <div className="sidebar-header">
        <div className="brand-wrapper">
          <div className="brand-icon">
            <IconCode size={16} />
          </div>
          {!collapsed && (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span className="brand-name">codewise</span>
              <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', letterSpacing: '0.02em' }}>EXPLORER</span>
            </div>
          )}
        </div>
        <button
          className="btn-icon-subtle"
          onClick={() => setCollapsed(!collapsed)}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <IconChevronRight size={14} /> : <IconChevronLeft size={14} />}
        </button>
      </div>

      {/* Action / Search Area */}
      {!collapsed && (
        <div className="sidebar-actions">
          <button
            className="btn-new-thread"
            onClick={() => setShowNewFileInput(!showNewFileInput)}
            title="Create a new file"
          >
            <IconPlus size={14} />
            <span>New File</span>
          </button>

          {showNewFileInput && (
            <form onSubmit={handleCreateFileSubmit} style={{ marginBottom: '6px' }}>
              <div style={{ display: 'flex', gap: '4px' }}>
                <input
                  type="text"
                  placeholder="e.g. script.py, app.js, index.html"
                  value={newFileName}
                  onChange={(e) => setNewFileName(e.target.value)}
                  autoFocus
                  style={{
                    flex: 1,
                    backgroundColor: 'var(--bg-input)',
                    border: '1px solid var(--accent-pink)',
                    color: 'var(--text-primary)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '4px 8px',
                    fontSize: '0.78rem',
                    outline: 'none'
                  }}
                />
                <button
                  type="submit"
                  style={{
                    backgroundColor: 'var(--accent-pink)',
                    color: '#000',
                    border: 'none',
                    borderRadius: 'var(--radius-sm)',
                    padding: '0 8px',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  Create
                </button>
              </div>
            </form>
          )}

          <div className="search-bar">
            <span className="search-icon">
              <IconSearch size={13} />
            </span>
            <input
              type="text"
              className="search-input"
              placeholder="Search files..."
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
            />
          </div>
        </div>
      )}

      {/* Explorer Tree Section */}
      <div className="sidebar-list">
        {/* 1. Source Files (Runnable) */}
        {!collapsed && (
          <div className="explorer-section-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <IconFileCode size={12} color="var(--accent-pink)" />
              <span className="explorer-section-title">Source Files</span>
            </div>
            <span className="explorer-badge-count">{sourceFiles.length}</span>
          </div>
        )}

        {sourceFiles.length === 0 ? (
          !collapsed && (
            <div style={{ padding: '8px 12px', color: 'var(--text-muted)', fontSize: '0.75rem', fontStyle: 'italic' }}>
              No runnable files found
            </div>
          )
        ) : (
          sourceFiles.map(renderFileItem)
        )}

        {/* 2. Documents & Data (Non-runnable / legacy) */}
        {documentFiles.length > 0 && (
          <>
            {!collapsed && (
              <div
                className="explorer-section-header"
                style={{ marginTop: '12px', cursor: 'pointer' }}
                onClick={() => setIsDocsExpanded(!isDocsExpanded)}
                title="Toggle documents and data"
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <IconFileText size={12} color="var(--text-secondary)" />
                  <span className="explorer-section-title">Documents & Data</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span className="explorer-badge-count">{documentFiles.length}</span>
                  <span style={{ transform: isDocsExpanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }}>
                    <IconChevronDown size={12} />
                  </span>
                </div>
              </div>
            )}

            {isDocsExpanded && documentFiles.map(renderFileItem)}
          </>
        )}
      </div>

      {/* Subtle Sidebar Footer */}
      {!collapsed && (
        <div className="sidebar-footer">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>{sessions.length} {sessions.length === 1 ? 'file' : 'files'}</span>
            <button
              onClick={onResetLayout}
              className="btn-icon-subtle"
              title="Reset layout to default sizes"
              style={{ padding: '2px 4px', fontSize: '0.68rem', display: 'flex', alignItems: 'center', gap: '3px' }}
            >
              <IconRefresh size={10} />
              <span>Reset Layout</span>
            </button>
          </div>
          <button
            onClick={onOpenAbout}
            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '0.72rem' }}
          >
            codewise v2.0
          </button>
        </div>
      )}
    </aside>
  );
}
