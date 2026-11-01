import React, { useState, useRef } from 'react';
import { IconDownload, IconUpload, IconX } from './Icons';
import { api } from '../services/api';

export default function BackupModal({ isOpen, onClose, onRefreshSessions }) {
  const [isExporting, setIsExporting] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [statusMsg, setStatusMsg] = useState(null);
  const fileInputRef = useRef(null);

  if (!isOpen) return null;

  const handleExport = async () => {
    setIsExporting(true);
    setStatusMsg(null);
    try {
      const data = await api.exportAllSessions();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `codewise-backup-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setStatusMsg({ type: 'success', text: 'Backup downloaded successfully!' });
    } catch (err) {
      setStatusMsg({ type: 'error', text: `Export failed: ${err.message}` });
    } finally {
      setIsExporting(false);
    }
  };

  const handleImportFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsImporting(true);
    setStatusMsg(null);
    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      if (!parsed.data) {
        throw new Error('Invalid backup file format. Expected a codewise export JSON.');
      }
      const res = await api.importAllSessions(parsed.data);
      setStatusMsg({
        type: 'success',
        text: `Successfully imported ${res.imported_sessions_count} threads!`
      });
      onRefreshSessions();
    } catch (err) {
      setStatusMsg({ type: 'error', text: `Import failed: ${err.message}` });
    } finally {
      setIsImporting(false);
      e.target.value = '';
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <IconDownload size={16} color="var(--accent-pink)" />
            <span className="modal-title">Backup & Restore Threads</span>
          </div>
          <button className="btn-icon-subtle" onClick={onClose}>
            <IconX size={14} />
          </button>
        </div>

        <div className="modal-body">
          <p style={{ marginBottom: '14px', fontSize: '0.84rem', color: 'var(--text-secondary)' }}>
            Export all threads, revisions, and discussions to a portable JSON file or import a backup from another Mac.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '14px' }}>
            {/* Export Card */}
            <div style={{ background: 'var(--bg-panel)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.84rem' }}>
                Export
              </div>
              <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                Download all saved threads as JSON.
              </div>
              <button
                className="btn-primary-pink"
                onClick={handleExport}
                disabled={isExporting}
                style={{ marginTop: 'auto', justifyContent: 'center' }}
              >
                <IconDownload size={13} />
                <span>{isExporting ? 'Exporting...' : 'Download Backup'}</span>
              </button>
            </div>

            {/* Import Card */}
            <div style={{ background: 'var(--bg-panel)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.84rem' }}>
                Restore
              </div>
              <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                Import a previously saved backup file.
              </div>
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleImportFile}
                style={{ display: 'none' }}
                accept=".json"
              />
              <button
                className="btn-tool-clean"
                onClick={() => fileInputRef.current?.click()}
                disabled={isImporting}
                style={{ marginTop: 'auto', justifyContent: 'center' }}
              >
                <IconUpload size={13} />
                <span>{isImporting ? 'Importing...' : 'Upload JSON'}</span>
              </button>
            </div>
          </div>

          {statusMsg && (
            <div
              style={{
                padding: '8px 10px',
                borderRadius: 'var(--radius-sm)',
                fontSize: '0.78rem',
                backgroundColor: statusMsg.type === 'success' ? 'var(--status-success-bg)' : 'var(--status-error-bg)',
                border: `1px solid ${statusMsg.type === 'success' ? 'var(--status-success-border)' : 'var(--status-error-border)'}`,
                color: statusMsg.type === 'success' ? 'var(--status-success-text)' : 'var(--status-error-text)'
              }}
            >
              {statusMsg.text}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn-tool-clean" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
