import React, { useState, useEffect } from 'react';
import {
  IconCode,
  IconEye,
  IconEyeOff,
  IconLock,
  IconUser,
  IconKey,
  IconCheck,
  IconCopy,
  IconArrowRight,
  IconChevronDown,
  IconShield
} from './Icons';
import { api } from '../services/api';

export default function LoginPage({ onLoginSuccess }) {
  // Modes: 'login' | 'register' | 'forgot'
  const [mode, setMode] = useState('login');

  // Form Fields
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [recoveryKey, setRecoveryKey] = useState('');
  const [rememberMe, setRememberMe] = useState(true);

  // UI States
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [generalError, setGeneralError] = useState('');
  const [fieldErrors, setFieldErrors] = useState({});
  const [successMessage, setSuccessMessage] = useState('');

  // Demo Credentials Card
  const [demoCreds, setDemoCreds] = useState({
    email: 'demo@codewise.dev',
    password: 'DemoUser2026!',
    recovery_key: 'CW-DEMO-2026-RECOVER'
  });
  const [isDemoCardOpen, setIsDemoCardOpen] = useState(false);
  const [copiedKey, setCopiedKey] = useState(false);

  // New Registration Recovery Key Modal/Banner
  const [registeredRecoveryKey, setRegisteredRecoveryKey] = useState('');
  const [savedUserToken, setSavedUserToken] = useState(null);
  const [savedUserData, setSavedUserData] = useState(null);

  // Fetch demo credentials on mount
  useEffect(() => {
    let mounted = true;
    api.getDemoCredentials()
      .then((data) => {
        if (mounted && data) {
          setDemoCreds(data);
        }
      })
      .catch(() => {});
    return () => { mounted = false; };
  }, []);

  // Clear errors when switching modes
  const handleSwitchMode = (newMode) => {
    setMode(newMode);
    setGeneralError('');
    setFieldErrors({});
    setSuccessMessage('');
    setPassword('');
    setConfirmPassword('');
    setRecoveryKey('');
    setRegisteredRecoveryKey('');
  };

  // Quick-fill demo account
  const handleUseDemoAccount = () => {
    setEmail(demoCreds.email);
    setPassword(demoCreds.password);
    setGeneralError('');
    setFieldErrors({});
    setIsDemoCardOpen(true);
  };

  // Password strength calculation
  const getPasswordStrength = (pwd) => {
    if (!pwd) return { score: 0, label: '', color: 'transparent' };
    let score = 0;
    if (pwd.length >= 8) score += 1;
    if (/[a-zA-Z]/.test(pwd)) score += 1;
    if (/[0-9]/.test(pwd)) score += 1;
    if (/[^a-zA-Z0-9]/.test(pwd)) score += 1;

    if (score <= 1) return { score, label: 'Weak', color: '#EF4444' };
    if (score === 2) return { score, label: 'Fair', color: '#F59E0B' };
    if (score === 3) return { score, label: 'Good', color: '#3B82F6' };
    return { score, label: 'Strong', color: '#10B981' };
  };

  const pwdStrength = getPasswordStrength(password);

  // Handle Login Submission
  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setGeneralError('');
    const errors = {};

    const cleanEmail = email.trim();
    if (!cleanEmail) {
      errors.email = 'Email address is required.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail)) {
      errors.email = 'Please enter a valid email address.';
    }

    if (!password) {
      errors.password = 'Password is required.';
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    setIsLoading(true);
    setFieldErrors({});
    try {
      const res = await api.login({
        email: cleanEmail,
        password,
        remember_me: rememberMe
      });

      if (res.token) {
        localStorage.setItem('codewise_token', res.token);
        if (onLoginSuccess) {
          onLoginSuccess(res.user, res.token);
        }
      }
    } catch (err) {
      setGeneralError(err.message || 'Invalid email or password.');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle Registration Submission
  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setGeneralError('');
    const errors = {};

    const cleanName = name.trim();
    const cleanEmail = email.trim();

    if (!cleanName || cleanName.length < 2) {
      errors.name = 'Name must be at least 2 characters.';
    }

    if (!cleanEmail) {
      errors.email = 'Email address is required.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(cleanEmail)) {
      errors.email = 'Please enter a valid email address.';
    }

    if (!password) {
      errors.password = 'Password is required.';
    } else if (password.length < 8) {
      errors.password = 'Password must be at least 8 characters.';
    } else if (!/[a-zA-Z]/.test(password) || !/[0-9]/.test(password)) {
      errors.password = 'Password must include both letters and numbers.';
    }

    if (password !== confirmPassword) {
      errors.confirmPassword = 'Passwords do not match.';
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    setIsLoading(true);
    setFieldErrors({});
    try {
      const res = await api.register({
        name: cleanName,
        email: cleanEmail,
        password,
        confirm_password: confirmPassword
      });

      if (res.token) {
        localStorage.setItem('codewise_token', res.token);
        if (onLoginSuccess) {
          onLoginSuccess(res.user, res.token);
        }
      } else if (res.recovery_key) {
        setRegisteredRecoveryKey(res.recovery_key);
        setSavedUserToken(res.token);
        setSavedUserData(res.user);
      }
    } catch (err) {
      setGeneralError(err.message || 'Registration failed.');
    } finally {
      setIsLoading(false);
    }
  };

  // Confirm saved recovery key after registration
  const handleProceedAfterRegistration = () => {
    if (savedUserToken) {
      localStorage.setItem('codewise_token', savedUserToken);
      if (onLoginSuccess) {
        onLoginSuccess(savedUserData, savedUserToken);
      }
    }
  };

  // Handle Forgot Password Submission
  const handleForgotSubmit = async (e) => {
    e.preventDefault();
    setGeneralError('');
    setSuccessMessage('');
    const errors = {};

    const cleanEmail = email.trim();
    const cleanKey = recoveryKey.trim();

    if (!cleanEmail) {
      errors.email = 'Account email is required.';
    }

    if (!cleanKey) {
      errors.recoveryKey = 'Security Recovery Key is required.';
    }

    if (!password) {
      errors.password = 'New password is required.';
    } else if (password.length < 8) {
      errors.password = 'Password must be at least 8 characters.';
    } else if (!/[a-zA-Z]/.test(password) || !/[0-9]/.test(password)) {
      errors.password = 'Password must include both letters and numbers.';
    }

    if (password !== confirmPassword) {
      errors.confirmPassword = 'New passwords do not match.';
    }

    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    setIsLoading(true);
    setFieldErrors({});
    try {
      const res = await api.forgotPassword({
        email: cleanEmail,
        recovery_key: cleanKey,
        new_password: password,
        confirm_password: confirmPassword
      });

      setSuccessMessage(res.message || 'Password reset successfully. You can now sign in.');
      setPassword('');
      setConfirmPassword('');
      setRecoveryKey('');
      setTimeout(() => {
        setMode('login');
        setGeneralError('');
      }, 2000);
    } catch (err) {
      setGeneralError(err.message || 'Failed to reset password.');
    } finally {
      setIsLoading(false);
    }
  };

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedKey(true);
      setTimeout(() => setCopiedKey(false), 2000);
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="auth-page-wrapper">
      <div className="auth-container">
        {/* Left Region: Brand & Authentication Form */}
        <div className="auth-form-column">
          <div className="auth-form-card">
            {/* Header Brand */}
            <div className="auth-brand-block">
              <div className="auth-brand-logo">
                <IconCode size={22} className="auth-brand-icon" />
              </div>
              <div>
                <h1 className="auth-brand-title">codewise</h1>
                <p className="auth-brand-tagline">understand the code. master the logic.</p>
              </div>
            </div>

            {/* Post-Registration Recovery Key Showcase */}
            {registeredRecoveryKey ? (
              <div className="recovery-notice-card">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                  <IconShield size={18} color="var(--accent-pink)" />
                  <span style={{ fontWeight: 600, fontSize: '0.92rem', color: 'var(--text-primary)' }}>
                    Save Your Security Recovery Key
                  </span>
                </div>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '14px' }}>
                  Codewise operates locally on your machine with zero external email tracking. If you ever forget your password, this key is the only way to reset it.
                </p>

                <div className="recovery-key-display">
                  <span className="recovery-key-code">{registeredRecoveryKey}</span>
                  <button
                    type="button"
                    onClick={() => copyToClipboard(registeredRecoveryKey)}
                    className="btn-copy-clean"
                    title="Copy Recovery Key"
                  >
                    {copiedKey ? <IconCheck size={14} color="#10B981" /> : <IconCopy size={14} />}
                    <span>{copiedKey ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>

                <button
                  type="button"
                  className="btn-auth-primary"
                  onClick={handleProceedAfterRegistration}
                  style={{ marginTop: '16px', width: '100%' }}
                >
                  <span>Continue to Workspace</span>
                  <IconArrowRight size={15} />
                </button>
              </div>
            ) : (
              <>
                {/* Form Mode Header */}
                <div className="auth-header-text">
                  <h2 className="auth-heading">
                    {mode === 'login' && 'Sign In'}
                    {mode === 'register' && 'Create Account'}
                    {mode === 'forgot' && 'Reset Password'}
                  </h2>
                  <p className="auth-subheading">
                    {mode === 'login' && 'Enter your credentials to access your code workspaces.'}
                    {mode === 'register' && 'Sign up to analyze logic, run code, and track revisions.'}
                    {mode === 'forgot' && 'Use your Security Recovery Key to restore account access.'}
                  </p>
                </div>

                {/* Error Banner */}
                {generalError && (
                  <div className="auth-alert-error" role="alert">
                    <span>{generalError}</span>
                  </div>
                )}

                {/* Success Banner */}
                {successMessage && (
                  <div className="auth-alert-success" role="alert">
                    <span>{successMessage}</span>
                  </div>
                )}

                {/* 1. LOGIN FORM */}
                {mode === 'login' && (
                  <form onSubmit={handleLoginSubmit} noValidate className="auth-form">
                    <div className="auth-field-group">
                      <label className="auth-label" htmlFor="login-email">
                        Email Address
                      </label>
                      <input
                        id="login-email"
                        type="email"
                        className={`auth-input ${fieldErrors.email ? 'input-error' : ''}`}
                        placeholder="developer@example.com"
                        value={email}
                        onChange={(e) => {
                          setEmail(e.target.value);
                          if (fieldErrors.email) setFieldErrors({ ...fieldErrors, email: '' });
                        }}
                        autoComplete="email"
                        disabled={isLoading}
                      />
                      {fieldErrors.email && (
                        <span className="auth-field-error">{fieldErrors.email}</span>
                      )}
                    </div>

                    <div className="auth-field-group">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <label className="auth-label" htmlFor="login-password">
                          Password
                        </label>
                        <button
                          type="button"
                          className="auth-link-subtle"
                          onClick={() => handleSwitchMode('forgot')}
                          disabled={isLoading}
                        >
                          Forgot password?
                        </button>
                      </div>
                      <div className="password-input-wrapper">
                        <input
                          id="login-password"
                          type={showPassword ? 'text' : 'password'}
                          className={`auth-input ${fieldErrors.password ? 'input-error' : ''}`}
                          placeholder="••••••••"
                          value={password}
                          onChange={(e) => {
                            setPassword(e.target.value);
                            if (fieldErrors.password) setFieldErrors({ ...fieldErrors, password: '' });
                          }}
                          autoComplete="current-password"
                          disabled={isLoading}
                        />
                        <button
                          type="button"
                          className="btn-toggle-pwd"
                          onClick={() => setShowPassword(!showPassword)}
                          title={showPassword ? 'Hide password' : 'Show password'}
                          tabIndex={-1}
                        >
                          {showPassword ? <IconEyeOff size={15} /> : <IconEye size={15} />}
                        </button>
                      </div>
                      {fieldErrors.password && (
                        <span className="auth-field-error">{fieldErrors.password}</span>
                      )}
                    </div>

                    <div className="auth-row-options">
                      <label className="auth-checkbox-label">
                        <input
                          type="checkbox"
                          className="auth-checkbox"
                          checked={rememberMe}
                          onChange={(e) => setRememberMe(e.target.checked)}
                          disabled={isLoading}
                        />
                        <span>Remember me on this Mac</span>
                      </label>
                    </div>

                    <button
                      type="submit"
                      className="btn-auth-primary"
                      disabled={isLoading}
                    >
                      {isLoading ? (
                        <span className="btn-spinner-label">Signing In...</span>
                      ) : (
                        <>
                          <span>Sign In</span>
                          <IconArrowRight size={15} />
                        </>
                      )}
                    </button>

                    <div className="auth-switch-mode">
                      <span>Don't have an account?</span>
                      <button
                        type="button"
                        className="auth-link-bold"
                        onClick={() => handleSwitchMode('register')}
                        disabled={isLoading}
                      >
                        Create an account
                      </button>
                    </div>

                    {/* Preconfigured Demo Account Section */}
                    <div className="demo-credentials-box">
                      <div
                        className="demo-credentials-header"
                        onClick={() => setIsDemoCardOpen(!isDemoCardOpen)}
                        title="Click to toggle demo credentials"
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <IconKey size={14} color="var(--accent-pink)" />
                          <span style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                            Preconfigured Demo Account
                          </span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                            {isDemoCardOpen ? 'Collapse' : 'Details'}
                          </span>
                          <span style={{ transform: isDemoCardOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s' }}>
                            <IconChevronDown size={12} />
                          </span>
                        </div>
                      </div>

                      {isDemoCardOpen && (
                        <div className="demo-credentials-body">
                          <div className="demo-cred-row">
                            <span className="demo-cred-label">Email:</span>
                            <code className="demo-cred-value">{demoCreds.email}</code>
                          </div>
                          <div className="demo-cred-row">
                            <span className="demo-cred-label">Password:</span>
                            <code className="demo-cred-value">{demoCreds.password}</code>
                          </div>
                          <div className="demo-cred-row">
                            <span className="demo-cred-label">Recovery Key:</span>
                            <code className="demo-cred-value">{demoCreds.recovery_key}</code>
                          </div>
                        </div>
                      )}

                      <div style={{ padding: '8px 12px 10px 12px' }}>
                        <button
                          type="button"
                          className="btn-demo-quickfill"
                          onClick={handleUseDemoAccount}
                          disabled={isLoading}
                        >
                          Fill Demo Credentials
                        </button>
                      </div>
                    </div>
                  </form>
                )}

                {/* 2. REGISTRATION FORM */}
                {mode === 'register' && (
                  <form onSubmit={handleRegisterSubmit} noValidate className="auth-form">
                    <div className="auth-field-group">
                      <label className="auth-label" htmlFor="register-name">
                        Full Name
                      </label>
                      <input
                        id="register-name"
                        type="text"
                        className={`auth-input ${fieldErrors.name ? 'input-error' : ''}`}
                        placeholder="Alex Turing"
                        value={name}
                        onChange={(e) => {
                          setName(e.target.value);
                          if (fieldErrors.name) setFieldErrors({ ...fieldErrors, name: '' });
                        }}
                        disabled={isLoading}
                      />
                      {fieldErrors.name && (
                        <span className="auth-field-error">{fieldErrors.name}</span>
                      )}
                    </div>

                    <div className="auth-field-group">
                      <label className="auth-label" htmlFor="register-email">
                        Email Address
                      </label>
                      <input
                        id="register-email"
                        type="email"
                        className={`auth-input ${fieldErrors.email ? 'input-error' : ''}`}
                        placeholder="alex@university.edu"
                        value={email}
                        onChange={(e) => {
                          setEmail(e.target.value);
                          if (fieldErrors.email) setFieldErrors({ ...fieldErrors, email: '' });
                        }}
                        autoComplete="email"
                        disabled={isLoading}
                      />
                      {fieldErrors.email && (
                        <span className="auth-field-error">{fieldErrors.email}</span>
                      )}
                    </div>

                    <div className="auth-field-group">
                      <label className="auth-label" htmlFor="register-password">
                        Password
                      </label>
                      <div className="password-input-wrapper">
                        <input
                          id="register-password"
                          type={showPassword ? 'text' : 'password'}
                          className={`auth-input ${fieldErrors.password ? 'input-error' : ''}`}
                          placeholder="At least 8 characters with letters & numbers"
                          value={password}
                          onChange={(e) => {
                            setPassword(e.target.value);
                            if (fieldErrors.password) setFieldErrors({ ...fieldErrors, password: '' });
                          }}
                          autoComplete="new-password"
                          disabled={isLoading}
                        />
                        <button
                          type="button"
                          className="btn-toggle-pwd"
                          onClick={() => setShowPassword(!showPassword)}
                          tabIndex={-1}
                        >
                          {showPassword ? <IconEyeOff size={15} /> : <IconEye size={15} />}
                        </button>
                      </div>

                      {/* Password strength bar */}
                      {password && (
                        <div className="pwd-strength-container">
                          <div className="pwd-strength-bar-bg">
                            <div
                              className="pwd-strength-bar-fill"
                              style={{
                                width: `${(pwdStrength.score / 4) * 100}%`,
                                backgroundColor: pwdStrength.color
                              }}
                            />
                          </div>
                          <span className="pwd-strength-text" style={{ color: pwdStrength.color }}>
                            {pwdStrength.label}
                          </span>
                        </div>
                      )}

                      {fieldErrors.password && (
                        <span className="auth-field-error">{fieldErrors.password}</span>
                      )}
                    </div>

                    <div className="auth-field-group">
                      <label className="auth-label" htmlFor="register-confirm-password">
                        Confirm Password
                      </label>
                      <div className="password-input-wrapper">
                        <input
                          id="register-confirm-password"
                          type={showConfirmPassword ? 'text' : 'password'}
                          className={`auth-input ${fieldErrors.confirmPassword ? 'input-error' : ''}`}
                          placeholder="Re-enter password"
                          value={confirmPassword}
                          onChange={(e) => {
                            setConfirmPassword(e.target.value);
                            if (fieldErrors.confirmPassword) setFieldErrors({ ...fieldErrors, confirmPassword: '' });
                          }}
                          autoComplete="new-password"
                          disabled={isLoading}
                        />
                        <button
                          type="button"
                          className="btn-toggle-pwd"
                          onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                          tabIndex={-1}
                        >
                          {showConfirmPassword ? <IconEyeOff size={15} /> : <IconEye size={15} />}
                        </button>
                      </div>
                      {fieldErrors.confirmPassword && (
                        <span className="auth-field-error">{fieldErrors.confirmPassword}</span>
                      )}
                    </div>

                    <button
                      type="submit"
                      className="btn-auth-primary"
                      disabled={isLoading}
                    >
                      {isLoading ? (
                        <span className="btn-spinner-label">Creating Account...</span>
                      ) : (
                        <>
                          <span>Create Account</span>
                          <IconArrowRight size={15} />
                        </>
                      )}
                    </button>

                    <div className="auth-switch-mode">
                      <span>Already have an account?</span>
                      <button
                        type="button"
                        className="auth-link-bold"
                        onClick={() => handleSwitchMode('login')}
                        disabled={isLoading}
                      >
                        Sign in
                      </button>
                    </div>
                  </form>
                )}

                {/* 3. FORGOT PASSWORD FORM */}
                {mode === 'forgot' && (
                  <form onSubmit={handleForgotSubmit} noValidate className="auth-form">
                    <div className="auth-field-group">
                      <label className="auth-label" htmlFor="forgot-email">
                        Account Email
                      </label>
                      <input
                        id="forgot-email"
                        type="email"
                        className={`auth-input ${fieldErrors.email ? 'input-error' : ''}`}
                        placeholder="developer@example.com"
                        value={email}
                        onChange={(e) => {
                          setEmail(e.target.value);
                          if (fieldErrors.email) setFieldErrors({ ...fieldErrors, email: '' });
                        }}
                        disabled={isLoading}
                      />
                      {fieldErrors.email && (
                        <span className="auth-field-error">{fieldErrors.email}</span>
                      )}
                    </div>

                    <div className="auth-field-group">
                      <label className="auth-label" htmlFor="forgot-recovery-key">
                        Security Recovery Key
                      </label>
                      <input
                        id="forgot-recovery-key"
                        type="text"
                        className={`auth-input ${fieldErrors.recoveryKey ? 'input-error' : ''}`}
                        placeholder="e.g. CW-XXXX-XXXX"
                        value={recoveryKey}
                        onChange={(e) => {
                          setRecoveryKey(e.target.value);
                          if (fieldErrors.recoveryKey) setFieldErrors({ ...fieldErrors, recoveryKey: '' });
                        }}
                        disabled={isLoading}
                      />
                      <span className="auth-helper-note">
                        Key generated during registration (or demo key: {demoCreds.recovery_key}).
                      </span>
                      {fieldErrors.recoveryKey && (
                        <span className="auth-field-error">{fieldErrors.recoveryKey}</span>
                      )}
                    </div>

                    <div className="auth-field-group">
                      <label className="auth-label" htmlFor="forgot-password">
                        New Password
                      </label>
                      <div className="password-input-wrapper">
                        <input
                          id="forgot-password"
                          type={showPassword ? 'text' : 'password'}
                          className={`auth-input ${fieldErrors.password ? 'input-error' : ''}`}
                          placeholder="At least 8 characters with letters & numbers"
                          value={password}
                          onChange={(e) => {
                            setPassword(e.target.value);
                            if (fieldErrors.password) setFieldErrors({ ...fieldErrors, password: '' });
                          }}
                          disabled={isLoading}
                        />
                        <button
                          type="button"
                          className="btn-toggle-pwd"
                          onClick={() => setShowPassword(!showPassword)}
                          tabIndex={-1}
                        >
                          {showPassword ? <IconEyeOff size={15} /> : <IconEye size={15} />}
                        </button>
                      </div>
                      {fieldErrors.password && (
                        <span className="auth-field-error">{fieldErrors.password}</span>
                      )}
                    </div>

                    <div className="auth-field-group">
                      <label className="auth-label" htmlFor="forgot-confirm-password">
                        Confirm New Password
                      </label>
                      <div className="password-input-wrapper">
                        <input
                          id="forgot-confirm-password"
                          type={showConfirmPassword ? 'text' : 'password'}
                          className={`auth-input ${fieldErrors.confirmPassword ? 'input-error' : ''}`}
                          placeholder="Re-enter new password"
                          value={confirmPassword}
                          onChange={(e) => {
                            setConfirmPassword(e.target.value);
                            if (fieldErrors.confirmPassword) setFieldErrors({ ...fieldErrors, confirmPassword: '' });
                          }}
                          disabled={isLoading}
                        />
                        <button
                          type="button"
                          className="btn-toggle-pwd"
                          onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                          tabIndex={-1}
                        >
                          {showConfirmPassword ? <IconEyeOff size={15} /> : <IconEye size={15} />}
                        </button>
                      </div>
                      {fieldErrors.confirmPassword && (
                        <span className="auth-field-error">{fieldErrors.confirmPassword}</span>
                      )}
                    </div>

                    <button
                      type="submit"
                      className="btn-auth-primary"
                      disabled={isLoading}
                    >
                      {isLoading ? (
                        <span className="btn-spinner-label">Resetting Password...</span>
                      ) : (
                        <>
                          <span>Reset Password</span>
                          <IconArrowRight size={15} />
                        </>
                      )}
                    </button>

                    <div className="auth-switch-mode">
                      <span>Remembered your password?</span>
                      <button
                        type="button"
                        className="auth-link-bold"
                        onClick={() => handleSwitchMode('login')}
                        disabled={isLoading}
                      >
                        Back to sign in
                      </button>
                    </div>
                  </form>
                )}
              </>
            )}
          </div>
        </div>

        {/* Right Region: Code-Editor-Inspired Visual Showcase */}
        <div className="auth-visual-column">
          <div className="auth-visual-card">
            {/* Mock Editor Window Header */}
            <div className="mock-editor-topbar">
              <div className="mock-editor-dots">
                <span className="mock-dot dot-red" />
                <span className="mock-dot dot-yellow" />
                <span className="mock-dot dot-green" />
              </div>
              <div className="mock-editor-tabs">
                <div className="mock-tab active">
                  <span className="mock-tab-icon">py</span>
                  <span className="mock-tab-title">binary_search.py</span>
                </div>
                <div className="mock-tab">
                  <span className="mock-tab-icon">py</span>
                  <span className="mock-tab-title">analysis_engine.py</span>
                </div>
              </div>
            </div>

            {/* Mock Code Area */}
            <div className="mock-code-editor">
              <div className="mock-code-lines">
                <div className="mock-code-line"><span className="ln">1</span><span className="c-kw">def</span> <span className="c-fn">binary_search</span>(arr: <span className="c-tp">list</span>[<span className="c-tp">int</span>], target: <span className="c-tp">int</span>) -&gt; <span className="c-tp">int</span>:</div>
                <div className="mock-code-line"><span className="ln">2</span>    <span className="c-cm"># Divide-and-conquer on sorted sequence</span></div>
                <div className="mock-code-line"><span className="ln">3</span>    low, high = <span className="c-num">0</span>, <span className="c-fn">len</span>(arr) - <span className="c-num">1</span></div>
                <div className="mock-code-line"><span className="ln">4</span></div>
                <div className="mock-code-line"><span className="ln">5</span>    <span className="c-kw">while</span> low &lt;= high:</div>
                <div className="mock-code-line"><span className="ln">6</span>        mid = (low + high) // <span className="c-num">2</span></div>
                <div className="mock-code-line highlighted"><span className="ln">7</span>        <span className="c-kw">if</span> arr[mid] == target:</div>
                <div className="mock-code-line highlighted"><span className="ln">8</span>            <span className="c-kw">return</span> mid</div>
                <div className="mock-code-line"><span className="ln">9</span>        <span className="c-kw">elif</span> arr[mid] &lt; target:</div>
                <div className="mock-code-line"><span className="ln">10</span>            low = mid + <span className="c-num">1</span></div>
                <div className="mock-code-line"><span className="ln">11</span>        <span className="c-kw">else</span>:</div>
                <div className="mock-code-line"><span className="ln">12</span>            high = mid - <span className="c-num">1</span></div>
                <div className="mock-code-line"><span className="ln">13</span></div>
                <div className="mock-code-line"><span className="ln">14</span>    <span className="c-kw">return</span> -<span className="c-num">1</span></div>
              </div>
            </div>

            {/* Authentic Logic Analysis Overlay Card */}
            <div className="mock-analysis-badge">
              <div className="mock-badge-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span className="analysis-pulse-dot" />
                  <span style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    Logic Explanation
                  </span>
                </div>
                <span className="code-inline" style={{ fontSize: '0.65rem' }}>O(log n) Time</span>
              </div>
              <p className="mock-badge-text">
                Repeatedly halves the search space. At each step, compares target with middle element to narrow bounds.
              </p>
              <div className="mock-badge-tags">
                <span className="mock-pill">Sorted Array</span>
                <span className="mock-pill">Zero Extra Space O(1)</span>
                <span className="mock-pill verified">Guaranteed Termination</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
