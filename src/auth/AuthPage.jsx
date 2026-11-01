import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Crown, Shield } from 'lucide-react';
import { apiRequest } from './api';

export default function AuthPage({ mode, onSuccess }) {
  const isRegister = mode === 'register';
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError('');
    if (isRegister && password !== confirmPassword) {
      setError('Your passwords do not match.');
      return;
    }
    setSubmitting(true);
    try {
      const { user } = await apiRequest(`/api/auth/${isRegister ? 'register' : 'login'}`, {
        method: 'POST', body: JSON.stringify({ email, password, ...(isRegister ? { confirmPassword } : {}) }),
      });
      await onSuccess(user);
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setSubmitting(false);
    }
  }

  return <main className="auth-screen"><div className="auth-panel"><div className="auth-brand"><span className="brand-mark"><Crown size={18}/></span><span>FOUNDERS-ONLY<small>PRIVATE OFFICE</small></span></div><div className="auth-content"><div className="eyebrow">THE INNER CIRCLE</div><h1>{isRegister ? 'Make your entrance.' : 'Welcome back.'}</h1><p className="auth-subtitle">{isRegister ? 'Your private office is waiting.' : 'Your empire awaits. Let us get to business.'}</p><form onSubmit={submit} className="auth-form" noValidate><label>Email<input type="email" name="email" autoComplete="email" required value={email} onChange={e=>setEmail(e.target.value)} placeholder="you@example.com"/></label><label>Password<input type="password" name="password" autoComplete={isRegister?'new-password':'current-password'} required minLength={8} value={password} onChange={e=>setPassword(e.target.value)} placeholder="At least 8 characters"/></label>{isRegister&&<label>Confirm password<input type="password" name="confirmPassword" autoComplete="new-password" required value={confirmPassword} onChange={e=>setConfirmPassword(e.target.value)} placeholder="Enter your password again"/></label>}{error&&<div className="auth-error" role="alert">{error}</div>}<button className="auth-submit" type="submit" disabled={submitting}>{submitting ? (isRegister ? 'Creating account...' : 'Signing in...') : (isRegister ? 'Create account' : 'Log in')}<ArrowRight size={15}/></button></form><div className="auth-switch">{isRegister?<span>Already a member? <Link to="/login">Back to login</Link></span>:<span>New to the inner circle? <Link to="/register">Create account</Link></span>}</div></div><div className="auth-footer"><Shield size={13}/> Your private office is secured with encrypted sessions.</div></div><aside className="auth-aside"><div className="auth-aside-mark"><Crown size={35}/><span>F</span></div><div><span className="eyebrow">FOUNDERS-ONLY / EST. 2019</span><h2>Reply like<br/>a <em>billionaire.</em></h2><p>A private office for people building what comes next.</p></div><span className="auth-aside-foot">DISCRETION IS THE BETTER PART OF VALOR.</span></aside></main>;
}
