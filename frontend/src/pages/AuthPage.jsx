import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Crown, Shield } from 'lucide-react';
import { apiRequest } from '../lib/api';

export default function AuthPage({ mode, onSuccess }) {
  const isRegister = mode === 'register';
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    if (isRegister && password !== confirmPassword) {
      setError('Your passwords do not match.');
      return;
    }

    setSubmitting(true);
    try {
      const endpoint = isRegister ? '/api/auth/register' : '/api/auth/login';
      const result = await apiRequest(endpoint, {
        method: 'POST',
        body: JSON.stringify({ email, password, ...(isRegister ? { confirmPassword } : {}) }),
      });
      await onSuccess(result.user);
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="auth-screen">
      <section className="auth-panel">
        <div className="auth-brand"><span className="brand-mark"><Crown size={18} /></span><span>FOUNDERS-ONLY<small>PRIVATE OFFICE</small></span></div>
        <div className="auth-content">
          <div className="eyebrow">THE INNER CIRCLE</div>
          <h1>{isRegister ? 'Make your entrance.' : 'Welcome back.'}</h1>
          <p>{isRegister ? 'Your private office is waiting.' : 'Your empire awaits. Let us get to business.'}</p>
          <form className="auth-form" onSubmit={handleSubmit} noValidate>
            <label>Email<input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" /></label>
            <label>Password<input type="password" autoComplete={isRegister ? 'new-password' : 'current-password'} minLength={8} required value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 8 characters" /></label>
            {isRegister && <label>Confirm password<input type="password" autoComplete="new-password" required value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Enter your password again" /></label>}
            {error && <div className="auth-error" role="alert">{error}</div>}
            <button className="auth-submit" type="submit" disabled={submitting}>
              {submitting ? (isRegister ? 'Creating account...' : 'Signing in...') : (isRegister ? 'Create account' : 'Log in')}
              <ArrowRight size={15} />
            </button>
          </form>
          <div className="auth-switch">
            {isRegister ? <span>Already a member? <Link to="/login">Back to login</Link></span> : <span>New to the inner circle? <Link to="/register">Create account</Link></span>}
          </div>
        </div>
        <div className="auth-footer"><Shield size={13} /> Your private office is secured with encrypted sessions.</div>
      </section>
      <aside className="auth-aside">
        <div className="auth-emblem"><Crown size={32} /><span>F</span></div>
        <div><div className="eyebrow">FOUNDERS-ONLY / EST. 2019</div><h2>Reply like<br />a <em>billionaire.</em></h2><p>A private office for people building what comes next.</p></div>
        <small>DISCRETION IS THE BETTER PART OF VALOR.</small>
      </aside>
    </main>
  );
}
