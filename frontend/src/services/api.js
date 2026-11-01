import { handleOfflineRequest } from './offlineFallback';

// In production, uses VITE_API_BASE_URL if set; in local dev, connects directly to FastAPI backend
const rawBaseUrl = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '');
const API_BASE = rawBaseUrl
  ? `${rawBaseUrl}/api`
  : (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'))
    ? 'http://127.0.0.1:8000/api'
    : '/api';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  let token = null;
  if (typeof window !== 'undefined') {
    const rawToken = localStorage.getItem('codewise_token');
    if (rawToken && typeof rawToken === 'string' && !rawToken.includes('\n') && !rawToken.includes('\r')) {
      token = rawToken.trim();
    }
  }

  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...(options.headers || {})
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers
    });

    const rawText = await response.text();
    let data = null;
    let isJson = false;
    try {
      if (rawText && !rawText.includes('<!DOCTYPE') && !rawText.includes('<html')) {
        data = JSON.parse(rawText);
        isJson = true;
      }
    } catch {}

    if (response.ok) {
      if (isJson && data !== null) {
        return data;
      }
      // If endpoint is run and body is not JSON (e.g. static CDN returning 200 index.html)
      if (endpoint === '/run') {
        return {
          stdout: '',
          stderr: 'Backend execution service is unreachable. Real code execution requires an active connection to the Codewise backend.',
          exit_code: 1,
          execution_time_ms: 0,
          status: 'backend_unavailable'
        };
      }
      if (endpoint.startsWith('/auth')) {
        throw new Error('Unexpected non-JSON response from authentication server. Please check your backend deployment.');
      }
      return handleOfflineRequest(endpoint, options);
    }

    // Differentiate HTTP error status codes
    const errorDetail = isJson && data ? (
      Array.isArray(data.detail)
        ? data.detail.map(d => d.msg || JSON.stringify(d)).join('; ')
        : (data.detail || data.message)
    ) : null;

    if (response.status === 400) {
      throw new Error(errorDetail || 'Bad request. Please verify submitted parameters.');
    }
    if (response.status === 401) {
      if (!endpoint.startsWith('/auth/login') && !endpoint.startsWith('/auth/register')) {
        if (typeof window !== 'undefined') {
          localStorage.removeItem('codewise_token');
          window.dispatchEvent(new CustomEvent('codewise_auth_unauthorized'));
        }
      }
      throw new Error(errorDetail || 'Invalid credentials or session expired.');
    }
    if (response.status === 403) {
      throw new Error(errorDetail || 'Access forbidden: You do not have permission to access or modify this resource.');
    }
    if (response.status === 404) {
      // If 404 on API endpoints, differentiate
      if (endpoint === '/run') {
        return {
          stdout: '',
          stderr: 'Execution endpoint not found on backend (HTTP 404).',
          exit_code: 1,
          execution_time_ms: 0,
          status: 'backend_unavailable'
        };
      }
      if (endpoint.startsWith('/auth')) {
        throw new Error(errorDetail || 'Authentication endpoint not found on backend.');
      }
      // Safe fallback for optional read endpoints
      return handleOfflineRequest(endpoint, options);
    }
    if (response.status === 422) {
      throw new Error(errorDetail || 'Data validation failed. Please check form inputs.');
    }
    if (response.status === 429) {
      throw new Error(errorDetail || 'Rate limit exceeded. Too many requests; please slow down.');
    }
    if (response.status >= 500) {
      if (endpoint === '/run') {
        return {
          stdout: '',
          stderr: `Backend execution error (HTTP ${response.status}): ${errorDetail || 'Internal server error'}`,
          exit_code: 1,
          execution_time_ms: 0,
          status: 'error'
        };
      }
      throw new Error(errorDetail || `Internal server error (HTTP ${response.status}). Please try again later.`);
    }

    throw new Error(errorDetail || `Request failed with HTTP status ${response.status}`);
  } catch (err) {
    // If it's already an explicit API business or HTTP error, rethrow it
    if (
      err.message &&
      !err.message.includes('fetch') &&
      !err.message.includes('Network') &&
      !err.message.includes('Failed to fetch') &&
      !err.message.includes('JSON') &&
      !err.message.includes('pattern')
    ) {
      throw err;
    }

    // Network / unreachable backend handling: NEVER simulate fake execution or fake auth
    if (endpoint === '/run') {
      return {
        stdout: '',
        stderr: 'Backend execution service is unreachable. Real code execution requires an active connection to the Codewise backend.',
        exit_code: 1,
        execution_time_ms: 0,
        status: 'backend_unavailable'
      };
    }
    if (endpoint === '/verify-sample') {
      let expectedOut = '';
      try {
        if (options.body) expectedOut = JSON.parse(options.body).expected_output || '';
      } catch {}
      return {
        is_match: false,
        actual_output: '',
        expected_output: expectedOut,
        exit_code: 1,
        execution_time_ms: 0,
        notes: 'Verification requires an active connection to the Codewise backend runtime.'
      };
    }
    if (endpoint.startsWith('/auth')) {
      throw new Error('Authentication server is unreachable. Please verify that the Codewise backend server is running and reachable.');
    }

    // Safe read-only fallback for offline exploration
    console.warn(`[codewise] Live API unreachable for ${endpoint}, using safe read-only fallback.`);
    return handleOfflineRequest(endpoint, options);
  }
}

export const api = {
  // Authentication
  login: (credentials) => request('/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials)
  }),

  register: (data) => request('/auth/register', {
    method: 'POST',
    body: JSON.stringify(data)
  }),

  getMe: () => request('/auth/me'),

  logout: () => request('/auth/logout', {
    method: 'POST'
  }),

  forgotPassword: (data) => request('/auth/forgot-password', {
    method: 'POST',
    body: JSON.stringify(data)
  }),

  getDemoCredentials: () => request('/auth/demo-credentials'),

  // Analysis
  analyzeCode: (payload) => request('/analyze', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),

  // Live Execution (with optional session and version persistence)
  runCode: (code, language, inputData = '', sessionId = null, codeVersionId = null) => request('/run', {
    method: 'POST',
    body: JSON.stringify({
      code,
      language,
      input_data: inputData,
      session_id: sessionId,
      code_version_id: codeVersionId
    })
  }),

  // Verify Sample Execution Comparison
  verifySample: ({ code, language, sampleInput, expectedOutput }) => request('/verify-sample', {
    method: 'POST',
    body: JSON.stringify({
      code,
      language,
      sample_input: sampleInput,
      expected_output: expectedOutput
    })
  }),

  // Language Detection & Registry
  getLanguages: () => request('/languages'),
  getCapabilities: () => request('/capabilities'),
  detectLanguage: (code, filename = null) => request('/detect-language', {
    method: 'POST',
    body: JSON.stringify({ code, filename })
  }),

  // Sessions / File Explorer
  listSessions: (query = '', category = 'all') => {
    const params = new URLSearchParams();
    if (query) params.append('q', query);
    if (category && category !== 'all') params.append('category', category);
    const qs = params.toString() ? `?${params.toString()}` : '';
    return request(`/sessions${qs}`);
  },

  getSession: (sessionId) => request(`/sessions/${sessionId}`),

  createFile: (payload) => request('/sessions', {
    method: 'POST',
    body: JSON.stringify(payload)
  }),

  createSession: (title) => request('/sessions', {
    method: 'POST',
    body: JSON.stringify({ title })
  }),

  renameFile: (sessionId, filename, title = null) => request(`/sessions/${sessionId}`, {
    method: 'PATCH',
    body: JSON.stringify({ filename, title })
  }),

  updateSession: (sessionId, title) => request(`/sessions/${sessionId}`, {
    method: 'PATCH',
    body: JSON.stringify({ title })
  }),

  deleteSession: (sessionId) => request(`/sessions/${sessionId}`, {
    method: 'DELETE'
  }),

  saveFileVersion: (sessionId, code, language = null, filename = null) => request(`/sessions/${sessionId}/versions`, {
    method: 'POST',
    body: JSON.stringify({ code, language, filename })
  }),

  restoreFileVersion: (sessionId, target) => request(`/sessions/${sessionId}/restore`, {
    method: 'POST',
    body: JSON.stringify(target)
  }),

  duplicateFile: (sessionId) => request(`/sessions/${sessionId}/duplicate`, {
    method: 'POST'
  }),

  getSessionVersion: (sessionId, versionId) => request(`/sessions/${sessionId}/versions/${versionId}`),

  // Chat
  sendChatMessage: (sessionId, message, codeVersionId = null) => request(`/sessions/${sessionId}/chat`, {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, message, code_version_id: codeVersionId })
  }),

  // Samples
  getSamples: () => request('/samples'),

  // System
  getSystemStatus: () => request('/system/status'),

  // Practice Test Assessment
  generatePracticeTest: (code, language = 'python', sessionId = null) => request('/practice/generate', {
    method: 'POST',
    body: JSON.stringify({ code, language, session_id: sessionId })
  }),

  submitPracticeAnswers: (testId, answers) => request('/practice/evaluate', {
    method: 'POST',
    body: JSON.stringify({ test_id: testId, answers })
  }),

  getPracticeHistory: (sessionId = null) => request(
    `/practice/history${sessionId ? `?session_id=${sessionId}` : ''}`
  ),

  // Backup & Restore
  exportAllSessions: () => request('/sessions/export/all'),
  importAllSessions: (data) => request('/sessions/import/all', {
    method: 'POST',
    body: JSON.stringify({ data })
  })
};
