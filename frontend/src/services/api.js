// In local development, connect directly to FastAPI backend to avoid proxy socket bottlenecks
const API_BASE = (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'))
  ? 'http://127.0.0.1:8000/api'
  : '/api';

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const token = typeof window !== 'undefined' ? localStorage.getItem('codewise_token') : null;
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...(options.headers || {})
  };

  const response = await fetch(url, {
    ...options,
    headers
  });

  if (!response.ok) {
    let errorDetail = 'Request failed';
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errJson.message || errorDetail;
    } catch {
      errorDetail = response.statusText || errorDetail;
    }

    // If 401 and not an authentication attempt, notify app of expired session
    if (response.status === 401 && !endpoint.startsWith('/auth/login') && !endpoint.startsWith('/auth/register')) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('codewise_token');
        window.dispatchEvent(new CustomEvent('codewise_auth_unauthorized'));
      }
    }

    throw new Error(errorDetail);
  }

  return response.json();
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

  // Backup & Restore
  exportAllSessions: () => request('/sessions/export/all'),
  importAllSessions: (data) => request('/sessions/import/all', {
    method: 'POST',
    body: JSON.stringify({ data })
  })
};
