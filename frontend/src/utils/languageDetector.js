/**
 * Language Detector Utility for Codewise
 * High-accuracy multi-language heuristic pattern detection engine.
 * Accurately detects programming languages, distinguishes auto-detect from manual selection,
 * and identifies ambiguous/empty snippets without guessing.
 */

export const LANGUAGE_DISPLAY_NAMES = {
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

const EXTENSION_MAP = {
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
  toml: 'toml'
};

/**
 * Detect language from filename or extension
 */
export function detectLanguageFromFilename(filename) {
  if (!filename || typeof filename !== 'string') return null;
  const lower = filename.trim().toLowerCase();
  if (lower === 'dockerfile' || lower.startsWith('dockerfile.')) return 'dockerfile';
  const lastDot = lower.lastIndexOf('.');
  if (lastDot !== -1) {
    const ext = lower.slice(lastDot + 1);
    if (EXTENSION_MAP[ext]) return EXTENSION_MAP[ext];
  }
  return null;
}

/**
 * Detect programming language from source code contents
 * Returns: { language: string | null, confidence: 'high' | 'medium' | 'uncertain', message: string | null, name: string | null }
 */
export function detectLanguageClient(code, filename = null) {
  if (!code || typeof code !== 'string' || !code.trim()) {
    const fileExt = detectLanguageFromFilename(filename);
    if (fileExt) {
      return {
        language: fileExt,
        confidence: 'medium',
        message: null,
        name: LANGUAGE_DISPLAY_NAMES[fileExt] || fileExt
      };
    }
    return {
      language: null,
      confidence: 'uncertain',
      message: 'Enter more code to detect language',
      name: null
    };
  }

  const clean = code.trim();
  const lower = clean.toLowerCase();
  const lines = clean.split('\n');
  const firstLines = lines.slice(0, 20).join('\n');
  const lowerFirstLines = firstLines.toLowerCase();

  const scores = {};
  const addScore = (lang, points) => {
    scores[lang] = (scores[lang] || 0) + points;
  };

  // 1. Dockerfile
  if (/^\s*(FROM|RUN|WORKDIR|COPY|ADD|EXPOSE|ENTRYPOINT|CMD)\s+/m.test(firstLines)) {
    addScore('dockerfile', 110);
  }

  // 2. HTML
  if (
    /<!doctype\s+html/i.test(lowerFirstLines) ||
    /<html\b/i.test(lowerFirstLines) ||
    (/<body\b/i.test(lowerFirstLines) && /<div\b/i.test(lowerFirstLines))
  ) {
    addScore('html', 105);
  }

  // 3. XML
  if (
    /<\?xml\b/i.test(lowerFirstLines) ||
    (/<root\b/i.test(lowerFirstLines) && /<\/root>/i.test(clean)) ||
    (/<urlset\b/i.test(lowerFirstLines) && /<\/urlset>/i.test(clean))
  ) {
    addScore('xml', 100);
  }

  // 4. JSON
  if (
    (clean.startsWith('{') && clean.endsWith('}')) ||
    (clean.startsWith('[') && clean.endsWith(']'))
  ) {
    try {
      const parsed = JSON.parse(clean);
      if (typeof parsed === 'object' && parsed !== null && Object.keys(parsed).length > 0) {
        addScore('json', 95);
      }
    } catch {}
  }

  // 5. Bash / Shell
  if (/^#!\/(bin|usr\/bin)\/(bash|sh|env bash)/m.test(firstLines)) {
    addScore('bash', 120);
  } else if (
    /\b(echo\s+["']|export\s+[A-Za-z0-9_]+=)\b/.test(clean) &&
    !clean.includes(';') &&
    !clean.includes('{')
  ) {
    addScore('bash', 45);
  }

  // 6. SQL
  if (
    /^\s*(select\s+.+\s+from|insert\s+into\s+|update\s+.+\s+set|delete\s+from\s+|create\s+table\s+|alter\s+table\s+|drop\s+table\s+|with\s+[a-zA-Z0-9_]+\s+as\s*\()/i.test(
      clean
    )
  ) {
    addScore('sql', 110);
  }

  // 7. C++ & C
  const hasCppHeader = /#include\s*<(iostream|vector|string|map|set|algorithm|queue|stack|sstream|fstream|iomanip|cmath|climits|bits\/stdc\+\+\.h)>/i.test(
    clean
  );
  const hasCppStd = /\bstd::(cout|cin|endl|vector|string|map|set|pair|make_pair|make_shared|unique_ptr)\b/.test(
    clean
  );
  const hasCppCout = /\b(cout\s*<<|cin\s*>>|using\s+namespace\s+std;)\b/.test(clean);
  const hasCppTemplate = /\btemplate\s*<\s*(typename|class)\b/.test(clean);

  if (hasCppHeader) addScore('cpp', 110);
  if (hasCppStd) addScore('cpp', 95);
  if (hasCppCout) addScore('cpp', 90);
  if (hasCppTemplate) addScore('cpp', 80);

  const hasCHeader = /#include\s*<(stdio\.h|stdlib\.h|string\.h|stdbool\.h|unistd\.h|time\.h|errno\.h|pthread\.h)>/i.test(
    clean
  );
  const hasCPrintf = /\b(printf|scanf|fprintf\s*\(\s*stderr|sprintf)\s*\(/.test(clean);
  const hasCMalloc = /\b(malloc|free|calloc|realloc)\s*\(/.test(clean);

  if (hasCHeader) {
    if (hasCppHeader || hasCppStd || hasCppCout) {
      addScore('cpp', 40);
    } else {
      addScore('c', 95);
    }
  }
  if (hasCPrintf && !hasCppStd && !hasCppCout) {
    addScore('c', 85);
  }
  if (hasCMalloc && !hasCppStd && !hasCppCout) {
    addScore('c', 60);
  }
  if (
    /\bint\s+main\s*\(\s*(void|int\s+argc[^)]*)?\s*\)/.test(clean) &&
    (hasCHeader || hasCPrintf)
  ) {
    if (!hasCppHeader && !hasCppStd && !hasCppCout) {
      addScore('c', 45);
    }
  }

  // 8. Java
  if (
    /\bpublic\s+static\s+void\s+main\s*\(\s*String(\s*\[\]\s*|\s+)args\s*(\[\s*\]\s*)?\)/.test(
      clean
    )
  ) {
    addScore('java', 120);
  }
  if (/\bSystem\.(out|err)\.(println|print|printf)\s*\(/.test(clean)) {
    addScore('java', 100);
  }
  if (/\bpackage\s+[a-z0-9_.]+;/.test(clean)) {
    addScore('java', 85);
  }
  if (/\bimport\s+java(x)?\.[a-z0-9_.*]+;/.test(clean)) {
    addScore('java', 85);
  }
  if (
    /\bpublic\s+(final\s+)?class\s+[A-Za-z0-9_]+(\s+extends\s+[A-Za-z0-9_]+)?(\s+implements\s+[A-Za-z0-9_,\s]+)?\s*\{/.test(
      clean
    )
  ) {
    addScore('java', 85);
  }
  if (/@Override\b/.test(clean)) {
    addScore('java', 65);
  }
  if (
    /\b(private|protected|public)\s+(static\s+)?(final\s+)?(int|double|float|boolean|String|void|[A-Z]\w+)\s+[a-zA-Z0-9_]+\s*(\([^)]*\)|=)/.test(
      clean
    ) &&
    clean.includes(';')
  ) {
    addScore('java', 75);
  }
  if (
    /\bnew\s+(ArrayList|HashMap|HashSet|Scanner|StringBuilder)<[A-Za-z0-9_,\s]*>\s*\(/.test(
      clean
    )
  ) {
    addScore('java', 75);
  }

  // 9. Python
  if (/\bint\s*\(\s*input\s*\(/.test(clean)) {
    addScore('python', 105);
  }
  if (/\binput\s*\([^)]*\)/.test(clean)) {
    addScore('python', 80);
  }
  if (/\bdef\s+[a-zA-Z0-9_]+\s*\([^)]*\)\s*:/.test(clean)) {
    addScore('python', 95);
  }
  if (/\bclass\s+[a-zA-Z0-9_]+(\([^)]*\))?\s*:/.test(clean)) {
    addScore('python', 90);
  }
  if (/\belif\s+.*:/.test(clean)) {
    addScore('python', 90);
  }
  if (/\bif\s+__name__\s*==\s*['"]__main__['"]\s*:/.test(clean)) {
    addScore('python', 100);
  }
  if (
    /^\s*(import\s+[a-zA-Z0-9_]+|from\s+[a-zA-Z0-9_.]+\s+import\s+)/m.test(clean) &&
    !clean.includes("from '") &&
    !clean.includes('from "')
  ) {
    addScore('python', 85);
  }
  if (/\bfor\s+[a-zA-Z0-9_]+\s+in\s+range\s*\(/.test(clean)) {
    addScore('python', 90);
  }
  if (/\bself\.[a-zA-Z0-9_]+/.test(clean) || /\bdef\s+__init__\s*\(/.test(clean)) {
    addScore('python', 85);
  }
  if (/\bprint\s*\([^)]*\)/.test(clean)) {
    // Only if not Java/C/JS
    if (
      !clean.includes(';') &&
      !clean.includes('System.out') &&
      !clean.includes('console.log')
    ) {
      addScore('python', 60);
    }
  }
  if (
    /^\s*(if|for|while|try|except|finally|with)\s+.*:\s*$/m.test(clean) &&
    !clean.includes('{')
  ) {
    addScore('python', 55);
  }

  // 10. JavaScript & TypeScript
  if (/\bconsole\.(log|error|warn|info|debug)\s*\(/.test(clean)) {
    addScore('javascript', 95);
  }
  if (/\b(const|let)\s+[a-zA-Z0-9_$]+\s*=/.test(clean)) {
    addScore('javascript', 70);
  }
  if (
    /\b(const|let|var)\s+[a-zA-Z0-9_$]+\s*=\s*require\s*\(/.test(clean) ||
    /\bmodule\.exports\s*=/.test(clean)
  ) {
    addScore('javascript', 100);
  }
  if (/(\([^)]*\)|[a-zA-Z0-9_$]+)\s*=>\s*(\{|[^{;]+)/.test(clean)) {
    addScore('javascript', 80);
  }
  if (/\bfunction\s+[a-zA-Z0-9_$]*\s*\([^)]*\)\s*\{/.test(clean)) {
    addScore('javascript', 70);
  }
  if (
    /\bdocument\.(getElementById|querySelector|addEventListener)\b/.test(clean) ||
    /\bwindow\.(addEventListener|localStorage)\b/.test(clean)
  ) {
    addScore('javascript', 95);
  }
  if (/\b(===|!==)\b/.test(clean)) {
    addScore('javascript', 50);
  }
  if (
    /\b(interface\s+[A-Z]\w+\s*\{|type\s+[A-Z]\w+\s*=)/.test(clean) ||
    /:\s*(string|number|boolean|any)\[\]/.test(clean)
  ) {
    addScore('typescript', 90);
  }
  if (/\bimport\s+React\b/.test(clean) || /className=/.test(clean)) {
    addScore('jsx', 90);
  }

  // 11. C#
  if (/\busing\s+System(\.[A-Za-z0-9_]+)*;/.test(clean)) {
    addScore('csharp', 100);
  }
  if (/\bConsole\.(WriteLine|Write)\s*\(/.test(clean)) {
    addScore('csharp', 100);
  }
  if (/\bnamespace\s+[A-Za-z0-9_.]+/.test(clean)) {
    addScore('csharp', 90);
  }

  // 12. Go
  if (/\bpackage\s+(main|[a-z0-9_]+)\b/.test(clean)) {
    addScore('go', 95);
  }
  if (/\bfunc\s+main\s*\(\s*\)/.test(clean)) {
    addScore('go', 95);
  }
  if (/\bfmt\.(Println|Printf|Print)\s*\(/.test(clean)) {
    addScore('go', 95);
  }

  // 13. Rust
  if (/\bfn\s+main\s*\(\s*\)/.test(clean) || /\bpub\s+fn\s+/.test(clean)) {
    addScore('rust', 100);
  }
  if (/\blet\s+mut\s+/.test(clean)) {
    addScore('rust', 100);
  }
  if (/\b(println!|eprintln!)\s*\(/.test(clean)) {
    addScore('rust', 100);
  }
  if (/\buse\s+std::/.test(clean)) {
    addScore('rust', 90);
  }

  // 14. PHP
  if (/<\?php\b/.test(clean) || /\becho\s+\$[a-zA-Z_]/.test(clean)) {
    addScore('php', 110);
  }

  // 15. Ruby
  if (
    /\bdef\s+[a-zA-Z0-9_]+\b/.test(clean) &&
    /\bend\b/.test(clean) &&
    !clean.includes(':') &&
    !clean.includes(';')
  ) {
    addScore('ruby', 85);
  }
  if (/\bputs\s+/.test(clean) && !clean.includes(';')) {
    addScore('ruby', 60);
  }

  // 16. Kotlin
  if (/\bfun\s+main\s*\(/.test(clean) || /\bval\s+[a-zA-Z0-9_]+\s*:\s*[A-Z]/.test(clean)) {
    addScore('kotlin', 95);
  }

  // 17. Swift
  if (/\bimport\s+(UIKit|SwiftUI|Foundation)\b/.test(clean)) {
    addScore('swift', 100);
  }

  // 18. CSS / SCSS
  if (
    /(\.[a-zA-Z0-9_-]+|#[a-zA-Z0-9_-]+|\bbody|\bhtml)\s*\{[^}]*:[^}]*;[^}]*\}/i.test(clean)
  ) {
    if (clean.includes('$') || clean.includes('@mixin') || clean.includes('@include')) {
      addScore('scss', 95);
    } else {
      addScore('css', 85);
    }
  }

  // Sort scores descending
  const entries = Object.entries(scores).sort((a, b) => b[1] - a[1]);

  const CONFIDENCE_THRESHOLD = 30;

  if (entries.length === 0 || entries[0][1] < CONFIDENCE_THRESHOLD) {
    // If filename has an extension, fall back to it only if code is not empty
    const fileExt = detectLanguageFromFilename(filename);
    if (fileExt && clean.length > 0) {
      return {
        language: fileExt,
        confidence: 'medium',
        message: null,
        name: LANGUAGE_DISPLAY_NAMES[fileExt] || fileExt
      };
    }
    // Ambiguous snippet or insufficient code: do NOT guess!
    return {
      language: null,
      confidence: 'uncertain',
      message: 'Enter more code to detect language',
      name: null
    };
  }

  const topLang = entries[0][0];
  const topScore = entries[0][1];

  return {
    language: topLang,
    confidence: topScore >= 60 ? 'high' : 'medium',
    message: null,
    name: LANGUAGE_DISPLAY_NAMES[topLang] || topLang
  };
}

/**
 * Checks if there is a genuine mismatch between selected language and detected language.
 * Returns true only when a manual language is selected, detected language is confident,
 * and they differ.
 */
export function isLanguageMismatch(selectedLang, detectedLang) {
  if (!selectedLang || selectedLang === 'auto') return false;
  if (!detectedLang) return false;

  const sel = selectedLang.toLowerCase().trim();
  const det = detectedLang.toLowerCase().trim();

  if (sel === det) return false;

  // Group equivalent / closely-related variants
  if ((sel === 'javascript' && det === 'jsx') || (sel === 'jsx' && det === 'javascript')) return false;
  if ((sel === 'typescript' && det === 'tsx') || (sel === 'tsx' && det === 'typescript')) return false;
  if ((sel === 'css' && det === 'scss') || (sel === 'scss' && det === 'css')) return false;

  return true;
}
