import React, { useState, useMemo } from 'react';
import { IconX, IconEye } from './Icons';

export default function HtmlPreviewModal({ isOpen, onClose, code, language }) {
  const [viewport, setViewport] = useState('desktop'); // desktop, tablet, mobile
  const [extraCss, setExtraCss] = useState('');
  const [showCssDrawer, setShowCssDrawer] = useState(false);

  // Combine HTML and CSS safely into an isolated HTML document
  const previewDoc = useMemo(() => {
    if (!isOpen) return '';

    const lang = (language || 'html').toLowerCase();
    let htmlContent = '';
    let cssContent = '';

    if (lang === 'css' || lang === 'scss') {
      cssContent = code;
      // Default preview canvas for CSS
      htmlContent = `
        <div class="preview-container">
          <header class="preview-header">
            <h1>Previewing CSS Styles</h1>
            <p>Your custom style sheet is applied to this preview canvas.</p>
          </header>
          
          <main class="preview-main">
            <div class="card">
              <h2>Card Component</h2>
              <p>This is a sample card demonstrating box model, colors, and typography.</p>
              <button class="btn btn-primary">Primary Action</button>
              <button class="btn btn-secondary">Secondary</button>
            </div>

            <div class="form-group">
              <label>Sample Input</label>
              <input type="text" placeholder="Type here..." value="Sample text" />
            </div>
          </main>
        </div>
      `;
    } else {
      // HTML (or mixed)
      htmlContent = code;
      cssContent = extraCss;
    }

    // Wrap in standard isolated document with clean default resets
    return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    /* Default Canvas Isolation */
    html, body {
      margin: 0;
      padding: 0;
      min-height: 100%;
      background: #ffffff;
      color: #111111;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
  </style>
  <style id="custom-css">
    ${cssContent}
  </style>
</head>
<body>
  ${htmlContent}
</body>
</html>`;
  }, [isOpen, code, language, extraCss]);

  if (!isOpen) return null;

  const viewportWidths = {
    desktop: '100%',
    tablet: '768px',
    mobile: '375px'
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="preview-modal-dialog" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="preview-modal-header">
          <div className="preview-header-left">
            <IconEye size={16} className="preview-icon-pink" />
            <span className="preview-modal-title">HTML & CSS Live Preview</span>
            <span className="preview-badge-sandboxed">🛡️ Sandboxed Iframe</span>
          </div>

          <div className="preview-header-center">
            <div className="viewport-toggle-group">
              <button
                type="button"
                className={`viewport-btn ${viewport === 'desktop' ? 'active' : ''}`}
                onClick={() => setViewport('desktop')}
                title="Desktop (100% width)"
              >
                Desktop
              </button>
              <button
                type="button"
                className={`viewport-btn ${viewport === 'tablet' ? 'active' : ''}`}
                onClick={() => setViewport('tablet')}
                title="Tablet (768px width)"
              >
                Tablet (768px)
              </button>
              <button
                type="button"
                className={`viewport-btn ${viewport === 'mobile' ? 'active' : ''}`}
                onClick={() => setViewport('mobile')}
                title="Mobile (375px width)"
              >
                Mobile (375px)
              </button>
            </div>
          </div>

          <div className="preview-header-right">
            {language !== 'css' && language !== 'scss' && (
              <button
                type="button"
                className={`btn-toggle-css ${showCssDrawer ? 'active' : ''}`}
                onClick={() => setShowCssDrawer(!showCssDrawer)}
                title="Attach custom CSS to preview alongside HTML"
              >
                {showCssDrawer ? 'Hide CSS' : '+ Linked CSS'}
              </button>
            )}

            <button
              type="button"
              className="btn-modal-close"
              onClick={onClose}
              title="Close Preview"
            >
              <IconX size={15} />
            </button>
          </div>
        </div>

        {/* Optional Linked CSS Drawer */}
        {showCssDrawer && language !== 'css' && language !== 'scss' && (
          <div className="preview-css-drawer">
            <div className="css-drawer-header">
              <span>Linked CSS Stylesheet (Injected into preview &lt;head&gt;):</span>
              <button className="btn-clear-css" onClick={() => setExtraCss('')}>Clear</button>
            </div>
            <textarea
              className="css-drawer-textarea"
              placeholder="/* Paste or write additional CSS rules to preview with this HTML... */"
              value={extraCss}
              onChange={(e) => setExtraCss(e.target.value)}
              spellCheck="false"
            />
          </div>
        )}

        {/* Preview Container */}
        <div className="preview-canvas-wrapper">
          <div
            className="preview-viewport-frame"
            style={{ width: viewportWidths[viewport] }}
          >
            {/* Strictly Isolated Sandboxed Iframe (No allow-same-origin) */}
            <iframe
              className="preview-iframe"
              sandbox="allow-scripts"
              srcDoc={previewDoc}
              title="Codewise Isolated Web Preview"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
