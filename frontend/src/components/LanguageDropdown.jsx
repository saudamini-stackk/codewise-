import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import {
  IconChevronDown,
  IconSearch,
  IconCheck,
  IconPlay,
  IconEye,
  IconX
} from './Icons';
import { getLanguageCapability } from '../utils/languageCapabilities';

export const ALL_LANGUAGES = [
  // Auto
  { id: 'auto', name: 'Auto Detect', category: 'auto', description: 'Automatically detects language from code content or file extension.' },

  // Programming Languages
  { id: 'python', name: 'Python', category: 'programming', ext: '.py', executable: true },
  { id: 'javascript', name: 'JavaScript', category: 'programming', ext: '.js', executable: true },
  { id: 'typescript', name: 'TypeScript', category: 'programming', ext: '.ts', executable: true },
  { id: 'java', name: 'Java', category: 'programming', ext: '.java', executable: false },
  { id: 'c', name: 'C', category: 'programming', ext: '.c', executable: true },
  { id: 'cpp', name: 'C++', category: 'programming', ext: '.cpp', executable: true },
  { id: 'csharp', name: 'C#', category: 'programming', ext: '.cs', executable: false },
  { id: 'go', name: 'Go', category: 'programming', ext: '.go', executable: false },
  { id: 'rust', name: 'Rust', category: 'programming', ext: '.rs', executable: false },
  { id: 'php', name: 'PHP', category: 'programming', ext: '.php', executable: false },
  { id: 'ruby', name: 'Ruby', category: 'programming', ext: '.rb', executable: true },
  { id: 'kotlin', name: 'Kotlin', category: 'programming', ext: '.kt', executable: false },
  { id: 'swift', name: 'Swift', category: 'programming', ext: '.swift', executable: false },
  { id: 'bash', name: 'Bash', category: 'programming', ext: '.sh', executable: true },

  // Web Technologies
  { id: 'html', name: 'HTML', category: 'web', ext: '.html', previewable: true },
  { id: 'css', name: 'CSS', category: 'web', ext: '.css', previewable: true },
  { id: 'scss', name: 'SCSS', category: 'web', ext: '.scss', previewable: true },
  { id: 'jsx', name: 'React JSX', category: 'web', ext: '.jsx', previewable: false },
  { id: 'tsx', name: 'React TSX', category: 'web', ext: '.tsx', previewable: false },

  // Data & Query Formats
  { id: 'sql', name: 'SQL', category: 'data', ext: '.sql', executable: false },
  { id: 'json', name: 'JSON', category: 'data', ext: '.json', executable: false },
  { id: 'xml', name: 'XML', category: 'data', ext: '.xml', executable: false },
  { id: 'yaml', name: 'YAML', category: 'data', ext: '.yaml', executable: false },

  // Configuration & Docs
  { id: 'markdown', name: 'Markdown', category: 'config', ext: '.md', executable: false },
  { id: 'toml', name: 'TOML', category: 'config', ext: '.toml', executable: false },
  { id: 'dockerfile', name: 'Dockerfile', category: 'config', ext: 'Dockerfile', executable: false }
];

const CATEGORY_LABELS = {
  programming: 'Programming Languages',
  web: 'Web Technologies',
  data: 'Data & Query Formats',
  config: 'Configuration & Docs'
};

export default function LanguageDropdown({
  language,
  setLanguage,
  detectedLanguage,
  detectedInfo,
  hasCode
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);

  const dropdownRef = useRef(null);
  const searchInputRef = useRef(null);
  const triggerBtnRef = useRef(null);
  const itemRefs = useRef([]);

  // Detected language tag info
  const detectedTag = useMemo(() => {
    if (detectedLanguage) {
      const match = ALL_LANGUAGES.find(l => l.id === detectedLanguage);
      const name = match ? match.name : (detectedInfo?.name || detectedLanguage);
      return { text: name, isUncertain: false };
    }
    if (hasCode) {
      return { text: 'more code needed', isUncertain: true };
    }
    return null;
  }, [detectedLanguage, detectedInfo, hasCode]);

  // Current selected language object
  const currentLang = useMemo(() => {
    return ALL_LANGUAGES.find(l => l.id === language) || ALL_LANGUAGES[0];
  }, [language]);

  // Scoring function for dynamic filtering
  const filterLanguages = useCallback((query) => {
    const q = query.toLowerCase().trim();
    if (!q) return ALL_LANGUAGES;

    const scored = [];
    for (const item of ALL_LANGUAGES) {
      const name = item.name.toLowerCase();
      const id = item.id.toLowerCase();
      const ext = (item.ext || '').toLowerCase().replace(/^\./, '');

      let score = 0;
      if (name === q || id === q || ext === q) {
        score = 100;
      } else if (name.startsWith(q)) {
        score = 85;
      } else if (id.startsWith(q)) {
        score = 80;
      } else if (ext.startsWith(q)) {
        score = 75;
      } else if (name.includes(' ' + q)) {
        // e.g. "React JSX" matches query "jsx"
        score = 65;
      } else if (q.length > 1 && name.includes(q)) {
        score = 50;
      } else if (q.length > 1 && id.includes(q)) {
        score = 45;
      } else if (q.length > 1 && ext.includes(q)) {
        score = 40;
      }

      if (score > 0) {
        scored.push({ item, score });
      }
    }

    scored.sort((a, b) => b.score - a.score || a.item.name.localeCompare(b.item.name));
    return scored.map(s => s.item);
  }, []);

  const filtered = useMemo(() => {
    return filterLanguages(search);
  }, [search, filterLanguages]);

  // Grouped languages when not searching
  const grouped = useMemo(() => {
    if (search.trim()) return null; // When searching, display flat prioritized list

    const groups = {};
    for (const item of ALL_LANGUAGES) {
      if (item.id === 'auto') continue;
      const cat = item.category || 'other';
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(item);
    }
    return groups;
  }, [search]);

  // Reset activeIndex when search query changes
  useEffect(() => {
    setActiveIndex(0);
  }, [search]);

  // Scroll active item into view
  useEffect(() => {
    if (isOpen && itemRefs.current[activeIndex]) {
      itemRefs.current[activeIndex].scrollIntoView({
        block: 'nearest',
        behavior: 'auto'
      });
    }
  }, [activeIndex, isOpen]);

  // Handle outside clicks and focus on opening
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
        setSearch('');
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      // Focus search input immediately upon opening
      const timer = setTimeout(() => {
        searchInputRef.current?.focus();
      }, 10);
      return () => {
        clearTimeout(timer);
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const handleSelect = useCallback((id) => {
    setLanguage(id);
    setIsOpen(false);
    setSearch('');
    triggerBtnRef.current?.focus();
  }, [setLanguage]);

  // Handle keyboard navigation inside search input
  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (filtered.length > 0) {
        setActiveIndex(prev => (prev + 1) % filtered.length);
      }
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (filtered.length > 0) {
        setActiveIndex(prev => (prev - 1 + filtered.length) % filtered.length);
      }
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filtered.length > 0 && filtered[activeIndex]) {
        handleSelect(filtered[activeIndex].id);
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      setIsOpen(false);
      setSearch('');
      triggerBtnRef.current?.focus();
    } else if (e.key === 'Tab') {
      setIsOpen(false);
      setSearch('');
    }
  };

  // Handle keyboard shortcut on the trigger button (opens and passes key)
  const handleTriggerKeyDown = (e) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp' || e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      setIsOpen(true);
    } else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
      e.preventDefault();
      setSearch(e.key);
      setIsOpen(true);
    }
  };

  const handleClearSearch = (e) => {
    e.stopPropagation();
    setSearch('');
    setActiveIndex(0);
    searchInputRef.current?.focus();
  };

  return (
    <div className="lang-dropdown-wrapper" ref={dropdownRef}>
      {/* Dropdown Trigger Button */}
      <button
        ref={triggerBtnRef}
        type="button"
        className={`lang-trigger-btn ${isOpen ? 'active' : ''}`}
        onClick={() => setIsOpen(prev => !prev)}
        onKeyDown={handleTriggerKeyDown}
        title="Select language or format"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls="lang-listbox"
        aria-label="Select language or format"
      >
        <span className="lang-trigger-text">
          {language === 'auto' ? (
            <>
              <span className="auto-sparkle">Auto</span>
              {detectedTag && (
                <span
                  className={`detected-tag ${detectedTag.isUncertain ? 'uncertain' : ''}`}
                  title={detectedTag.isUncertain ? 'Enter more code to detect language' : `Detected: ${detectedTag.text}`}
                >
                  ({detectedTag.text})
                </span>
              )}
            </>
          ) : (
            currentLang.name
          )}
        </span>
        <IconChevronDown size={12} className={`chevron-icon ${isOpen ? 'open' : ''}`} />
      </button>

      {/* Dropdown Menu Popover */}
      {isOpen && (
        <div
          className="lang-dropdown-menu"
          role="dialog"
          aria-label="Language selector menu"
        >
          {/* Search Box */}
          <div className="lang-search-box">
            <IconSearch size={13} className="lang-search-icon" aria-hidden="true" />
            <input
              ref={searchInputRef}
              type="text"
              className="lang-search-input"
              placeholder="Search language or format..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={handleKeyDown}
              role="searchbox"
              aria-label="Search language"
              aria-autocomplete="list"
              aria-controls="lang-listbox"
            />
            {search && (
              <button
                type="button"
                className="lang-search-clear"
                onClick={handleClearSearch}
                title="Clear search"
                aria-label="Clear search"
              >
                <IconX size={12} />
              </button>
            )}
          </div>

          <div
            id="lang-listbox"
            className="lang-list-scroll"
            role="listbox"
            aria-label="Supported languages"
          >
            {/* When searching: display prioritized flat list of matches */}
            {search.trim() ? (
              filtered.length > 0 ? (
                <div className="lang-search-results">
                  {filtered.map((item, index) => {
                    const isSelected = language === item.id;
                    const isFocused = index === activeIndex;
                    return (
                      <div
                        key={item.id}
                        ref={(el) => (itemRefs.current[index] = el)}
                        id={`lang-opt-${item.id}`}
                        role="option"
                        aria-selected={isSelected}
                        className={`lang-item ${isSelected ? 'selected' : ''} ${isFocused ? 'keyboard-active' : ''}`}
                        onClick={() => handleSelect(item.id)}
                        onMouseEnter={() => setActiveIndex(index)}
                      >
                        <div className="lang-item-left">
                          <span className="lang-item-name">{item.name}</span>
                          {item.ext && <span className="lang-ext">{item.ext}</span>}
                          {item.id === 'auto' && detectedTag && (
                            <span
                              className={`detected-tag ${detectedTag.isUncertain ? 'uncertain' : ''}`}
                              title={detectedTag.isUncertain ? 'Enter more code to detect language' : `Detected: ${detectedTag.text}`}
                            >
                              ({detectedTag.text})
                            </span>
                          )}
                        </div>

                        {(() => {
                          const cap = getLanguageCapability(item.id);
                          return (
                            <div className="lang-item-right">
                              {cap.canRun && (
                                <span className="lang-feature-pill exec" title="Working runtime available for execution">
                                  <IconPlay size={10} /> Run
                                </span>
                              )}
                              {cap.canPreview && (
                                <span className="lang-feature-pill prev" title="HTML/CSS Live Preview available">
                                  <IconEye size={10} /> Preview
                                </span>
                              )}
                              {cap.isRuntimeMissing && (
                                <span className="lang-feature-pill unavail" title={cap.unavailableReason}>
                                  No runtime
                                </span>
                              )}
                              {cap.kind === 'analysis_only' && (
                                <span className="lang-feature-pill analysis" title="Static code and logic analysis available">
                                  Analyse
                                </span>
                              )}
                              {isSelected && <IconCheck size={13} className="check-icon" />}
                            </div>
                          );
                        })()}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="lang-empty" role="status">
                  No matching languages found
                </div>
              )
            ) : (
              /* When not searching: display Auto-Detect + categorized groups */
              <>
                {/* Auto-Detect Option */}
                {(() => {
                  const autoItem = ALL_LANGUAGES[0];
                  const isSelected = language === 'auto';
                  const isFocused = activeIndex === 0;
                  return (
                    <div
                      ref={(el) => (itemRefs.current[0] = el)}
                      id="lang-opt-auto"
                      role="option"
                      aria-selected={isSelected}
                      className={`lang-item auto-item ${isSelected ? 'selected' : ''} ${isFocused ? 'keyboard-active' : ''}`}
                      onClick={() => handleSelect('auto')}
                      onMouseEnter={() => setActiveIndex(0)}
                    >
                      <div className="lang-item-left">
                        <span className="lang-item-name">Auto Detect</span>
                        {detectedTag && (
                          <span
                            className={`detected-tag ${detectedTag.isUncertain ? 'uncertain' : ''}`}
                            title={detectedTag.isUncertain ? 'Enter more code to detect language' : `Detected: ${detectedTag.text}`}
                          >
                            ({detectedTag.text})
                          </span>
                        )}
                      </div>
                      {isSelected && <IconCheck size={13} className="check-icon" />}
                    </div>
                  );
                })()}

                {/* Categorized Languages */}
                {Object.entries(grouped || {}).map(([catKey, items]) => (
                  <div key={catKey} className="lang-category-group">
                    <div className="lang-category-title">{CATEGORY_LABELS[catKey] || catKey}</div>
                    {items.map((item) => {
                      const overallIndex = filtered.findIndex((f) => f.id === item.id);
                      const isSelected = language === item.id;
                      const isFocused = overallIndex === activeIndex;
                      return (
                        <div
                          key={item.id}
                          ref={(el) => (itemRefs.current[overallIndex] = el)}
                          id={`lang-opt-${item.id}`}
                          role="option"
                          aria-selected={isSelected}
                          className={`lang-item ${isSelected ? 'selected' : ''} ${isFocused ? 'keyboard-active' : ''}`}
                          onClick={() => handleSelect(item.id)}
                          onMouseEnter={() => {
                            if (overallIndex !== -1) setActiveIndex(overallIndex);
                          }}
                        >
                          <div className="lang-item-left">
                            <span className="lang-item-name">{item.name}</span>
                            {item.ext && <span className="lang-ext">{item.ext}</span>}
                          </div>

                          {(() => {
                            const cap = getLanguageCapability(item.id);
                            return (
                              <div className="lang-item-right">
                                {cap.canRun && (
                                  <span className="lang-feature-pill exec" title="Working runtime available for execution">
                                    <IconPlay size={10} /> Run
                                  </span>
                                )}
                                {cap.canPreview && (
                                  <span className="lang-feature-pill prev" title="HTML/CSS Live Preview available">
                                    <IconEye size={10} /> Preview
                                  </span>
                                )}
                                {cap.isRuntimeMissing && (
                                  <span className="lang-feature-pill unavail" title={cap.unavailableReason}>
                                    No runtime
                                  </span>
                                )}
                                {cap.kind === 'analysis_only' && (
                                  <span className="lang-feature-pill analysis" title="Static code and logic analysis available">
                                    Analyse
                                  </span>
                                )}
                                {isSelected && <IconCheck size={13} className="check-icon" />}
                              </div>
                            );
                          })()}
                        </div>
                      );
                    })}
                  </div>
                ))}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
