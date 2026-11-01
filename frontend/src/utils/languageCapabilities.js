/**
 * Central Language Capability Registry for Codewise
 * Controls execution, preview, and static analysis capabilities dynamically and honestly
 * across the entire application.
 */

export const LANGUAGE_NAMES = {
  python: 'Python',
  javascript: 'JavaScript',
  typescript: 'TypeScript',
  java: 'Java',
  c: 'C',
  cpp: 'C++',
  csharp: 'C#',
  go: 'Go',
  rust: 'Rust',
  php: 'PHP',
  ruby: 'Ruby',
  kotlin: 'Kotlin',
  swift: 'Swift',
  bash: 'Bash',
  html: 'HTML',
  css: 'CSS',
  scss: 'SCSS',
  jsx: 'React JSX',
  tsx: 'React TSX',
  sql: 'SQL',
  json: 'JSON',
  xml: 'XML',
  yaml: 'YAML',
  markdown: 'Markdown',
  toml: 'TOML',
  dockerfile: 'Dockerfile'
};

/**
 * All programming languages that support execution in principle.
 */
export const EXECUTABLE_PROGRAMMING_LANGUAGES = new Set([
  'python',
  'javascript',
  'typescript',
  'c',
  'cpp',
  'bash',
  'ruby',
  'java',
  'csharp',
  'go',
  'rust',
  'php',
  'kotlin',
  'swift'
]);

/**
 * Programming languages with working, verified local execution runtimes on this host.
 * (Python 3, Node.js for JS & TS, Clang/GCC for C & C++, GNU Bash, and Ruby).
 */
export const WORKING_RUNTIMES = new Set([
  'python',
  'javascript',
  'typescript',
  'c',
  'cpp',
  'bash',
  'ruby'
]);

/**
 * Formats that support live HTML/CSS sandboxed browser preview.
 */
export const PREVIEWABLE_FORMATS = new Set([
  'html',
  'css',
  'scss'
]);

/**
 * Formats that are strictly for data, configuration, documents, or static analysis.
 * These formats must NEVER display a 'Run Code' button or execution console.
 */
export const ANALYSIS_ONLY_FORMATS = new Set([
  'json',
  'yaml',
  'xml',
  'sql',
  'markdown',
  'dockerfile',
  'toml',
  'jsx',
  'tsx'
]);

/**
 * Detailed explanation messages when a programming language supports execution in principle
 * but its required runtime/compiler is unavailable on the host.
 */
export const MISSING_RUNTIME_REASONS = {
  java: {
    short: 'Java runtime unavailable',
    full: 'Java runtime unavailable: JDK (javac & java) is not installed on this host. Full static code analysis is available.'
  },
  csharp: {
    short: 'C# runtime unavailable',
    full: 'C# runtime unavailable: .NET SDK (dotnet) is not installed on this host. Full static code analysis is available.'
  },
  go: {
    short: 'Go runtime unavailable',
    full: 'Go runtime unavailable: Go compiler (go) is not installed on this host. Full static code analysis is available.'
  },
  rust: {
    short: 'Rust runtime unavailable',
    full: 'Rust runtime unavailable: Rust compiler (rustc) is not installed on this host. Full static code analysis is available.'
  },
  php: {
    short: 'PHP runtime unavailable',
    full: 'PHP runtime unavailable: PHP CLI interpreter is not installed on this host. Full static code analysis is available.'
  },
  kotlin: {
    short: 'Kotlin runtime unavailable',
    full: 'Kotlin runtime unavailable: Kotlin compiler (kotlinc) is not installed on this host. Full static code analysis is available.'
  },
  swift: {
    short: 'Swift runtime unavailable',
    full: 'Swift runtime unavailable: Apple CommandLineTools SDK mismatch. Full static code analysis is available.'
  }
};

export const EXTENSION_MAP = {
  py: 'python',
  pyw: 'python',
  js: 'javascript',
  mjs: 'javascript',
  cjs: 'javascript',
  ts: 'typescript',
  mts: 'typescript',
  java: 'java',
  c: 'c',
  h: 'c',
  cpp: 'cpp',
  cc: 'cpp',
  cxx: 'cpp',
  hpp: 'cpp',
  cs: 'csharp',
  go: 'go',
  rs: 'rust',
  php: 'php',
  rb: 'ruby',
  kt: 'kotlin',
  swift: 'swift',
  sh: 'bash',
  bash: 'bash',
  html: 'html',
  htm: 'html',
  css: 'css',
  scss: 'scss',
  jsx: 'jsx',
  tsx: 'tsx',
  sql: 'sql',
  json: 'json',
  xml: 'xml',
  yaml: 'yaml',
  yml: 'yaml',
  md: 'markdown',
  toml: 'toml',
  dockerfile: 'dockerfile'
};

export const DEFAULT_FILENAMES = {
  python: 'main.py',
  javascript: 'app.js',
  typescript: 'index.ts',
  java: 'Main.java',
  cpp: 'main.cpp',
  c: 'main.c',
  csharp: 'Program.cs',
  go: 'main.go',
  rust: 'main.rs',
  php: 'index.php',
  ruby: 'app.rb',
  kotlin: 'Main.kt',
  swift: 'main.swift',
  bash: 'script.sh',
  html: 'index.html',
  css: 'styles.css',
  scss: 'styles.scss',
  sql: 'query.sql',
  json: 'data.json',
  xml: 'document.xml',
  yaml: 'config.yaml',
  markdown: 'README.md',
  toml: 'config.toml',
  dockerfile: 'Dockerfile'
};

/**
 * Returns complete capability descriptor for any given language or format.
 * Immediately updates available UI actions.
 */
export function getLanguageCapability(language) {
  if (!language) {
    return {
      id: 'unknown',
      name: 'Unknown',
      kind: 'analysis_only',
      canRun: false,
      canAnalyze: true,
      canPreview: false,
      isProgrammingLanguage: false,
      isRuntimeMissing: false,
      shortUnavailableMessage: null,
      unavailableReason: null
    };
  }

  const lang = language.toLowerCase().trim();
  const displayName = LANGUAGE_NAMES[lang] || lang.toUpperCase();

  // 1. Programming Languages
  if (EXECUTABLE_PROGRAMMING_LANGUAGES.has(lang)) {
    const canRun = WORKING_RUNTIMES.has(lang);
    const missingInfo = MISSING_RUNTIME_REASONS[lang];

    return {
      id: lang,
      name: displayName,
      kind: 'executable',
      canRun,
      canAnalyze: true,
      canPreview: false,
      isProgrammingLanguage: true,
      isRuntimeMissing: !canRun,
      shortUnavailableMessage: !canRun ? (missingInfo?.short || `${displayName} runtime unavailable`) : null,
      unavailableReason: !canRun ? (missingInfo?.full || `${displayName} runtime is not installed on this host.`) : null
    };
  }

  // 2. Previewable Web Markup / Style Sheets
  if (PREVIEWABLE_FORMATS.has(lang)) {
    return {
      id: lang,
      name: displayName,
      kind: 'previewable',
      canRun: false,
      canAnalyze: true,
      canPreview: true,
      isProgrammingLanguage: false,
      isRuntimeMissing: false,
      shortUnavailableMessage: null,
      unavailableReason: null
    };
  }

  // 3. Analysis-Only Data, Config, Query, and Documentation Formats
  return {
    id: lang,
    name: displayName,
    kind: 'analysis_only',
    canRun: false,
    canAnalyze: true,
    canPreview: false,
    isProgrammingLanguage: false,
    isRuntimeMissing: false,
    shortUnavailableMessage: null,
    unavailableReason: null
  };
}

/**
 * Synchronizes working runtimes dynamically from the host system status API.
 */
export function syncCapabilities(capabilitiesData) {
  if (capabilitiesData?.executable_languages && Array.isArray(capabilitiesData.executable_languages)) {
    WORKING_RUNTIMES.clear();
    for (const lang of capabilitiesData.executable_languages) {
      WORKING_RUNTIMES.add(lang.toLowerCase());
    }
  }
}

/**
 * Checks whether the host environment genuinely supports running this language.
 */
export function hasLocalRuntime(language) {
  return getLanguageCapability(language).canRun;
}

/**
 * Checks whether format can be previewed in sandboxed HTML viewer.
 */
export function isPreviewable(language) {
  return getLanguageCapability(language).canPreview;
}

/**
 * Checks whether format is an analysis-only data/doc/config format.
 */
export function isDataOrDocument(language) {
  return getLanguageCapability(language).kind === 'analysis_only';
}

/**
 * Checks whether format is a programming language in principle.
 */
export function isRunnable(language) {
  return getLanguageCapability(language).isProgrammingLanguage;
}

/**
 * Infers language from a filename
 */
export function getLanguageFromFilename(filename) {
  if (!filename) return 'python';
  const lower = filename.toLowerCase();
  if (lower === 'dockerfile') return 'dockerfile';
  const parts = lower.split('.');
  if (parts.length > 1) {
    const ext = parts.pop();
    if (EXTENSION_MAP[ext]) {
      return EXTENSION_MAP[ext];
    }
  }
  return 'python';
}

/**
 * Returns default filename for language
 */
export function getDefaultFilename(language) {
  const lang = (language || 'python').toLowerCase();
  return DEFAULT_FILENAMES[lang] || `code.${lang}`;
}
