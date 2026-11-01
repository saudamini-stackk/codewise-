import React, { useState } from 'react';
import { IconBook, IconDownload, IconPlus, IconCode, IconRefresh, IconLogout, IconUser } from './Icons';

export default function Header({
  currentThreadTitle,
  systemStatus,
  samples,
  currentUser,
  onLogout,
  onLoadSample,
  onNewThread,
  onResetLayout,
  onOpenAbout,
  onOpenBackup
}) {
  const [showSamples, setShowSamples] = useState(false);
  const isAi = systemStatus?.active_mode === 'ai';

  return (
    <header className="top-header">
      {/* Current File / Thread Title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: 0 }}>
        <div className="header-thread-title" title={currentThreadTitle || "Untitled File"}>
          {currentThreadTitle || "Untitled File"}
        </div>
      </div>

      {/* Minimal Header Actions */}
      <div className="header-right">
        {/* Reset Layout Action */}
        {onResetLayout && (
          <button
            className="btn-header"
            onClick={onResetLayout}
            title="Reset workspace panels to default layout"
          >
            <IconRefresh size={12} />
            <span>Reset Layout</span>
          </button>
        )}

        {/* Sample selector */}
        {samples?.length > 0 && (
          <div style={{ position: 'relative' }}>
            <button
              className="btn-header"
              onClick={() => setShowSamples(!showSamples)}
              title="Load sample demonstration code"
            >
              <IconCode size={13} />
              <span>Samples</span>
            </button>

            {showSamples && (
              <div
                style={{
                  position: 'absolute',
                  top: '100%',
                  right: 0,
                  marginTop: '4px',
                  width: '260px',
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
                  padding: '4px',
                  zIndex: 40
                }}
              >
                <div style={{ padding: '6px 8px', fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
                  Demo Programs
                </div>
                {samples.map((s) => (
                  <div
                    key={s.id}
                    onClick={() => {
                      onLoadSample(s);
                      setShowSamples(false);
                    }}
                    style={{
                      padding: '6px 8px',
                      borderRadius: 'var(--radius-sm)',
                      cursor: 'pointer',
                      fontSize: '0.8rem',
                      color: 'var(--text-primary)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '2px',
                      transition: 'background-color 0.12s'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--bg-panel-hover)'}
                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                  >
                    <div style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{s.title}</div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{s.filename}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Compact Backup */}
        <button className="btn-header" onClick={onOpenBackup} title="Backup or Restore SQLite Data">
          <IconDownload size={13} />
          <span>Backup</span>
        </button>

        {/* Small About */}
        <button className="btn-header" onClick={onOpenAbout} title="About codewise">
          <IconBook size={13} />
          <span>About</span>
        </button>

        {/* Subtle Mode indicator */}
        <div className="mode-indicator" title={`Execution Mode: ${systemStatus?.active_mode || 'local'}`}>
          <span className="mode-dot-pink" />
          <span>{isAi ? 'AI Powered' : 'Local Engine'}</span>
        </div>

        {/* User Profile & Logout */}
        {currentUser && (
          <div className="header-user-badge" title={`Signed in as ${currentUser.name} (${currentUser.email})`}>
            <div className="header-user-avatar">
              {(currentUser.name || 'U').charAt(0).toUpperCase()}
            </div>
            <span className="header-user-name">{currentUser.name || currentUser.email}</span>
            {onLogout && (
              <button
                className="btn-header-logout"
                onClick={onLogout}
                title="Sign out of codewise"
              >
                <IconLogout size={12} />
                <span>Logout</span>
              </button>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
