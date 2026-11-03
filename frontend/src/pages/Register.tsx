import { useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { ApiError } from '../api';
import { useAuth } from '../auth';
import type { RegistrationRole } from '../types';

export default function Register() {
  const { register } = useAuth();
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<RegistrationRole>('CUSTOMER');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [created, setCreated] = useState(false);

  function handleRoleChange(event: ChangeEvent<HTMLSelectElement>) {
    const value = event.target.value;
    if (value === 'CUSTOMER' || value === 'DESIGNER') {
      setRole(value);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register({
        email: email.trim(),
        password,
        display_name: displayName.trim(),
        role,
      });
      setCreated(true);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : 'Unable to create the account. Try again.');
    } finally {
      setSubmitting(false);
    }
  }

  if (created) {
    return (
      <section className="card narrow">
        <h1>Account created</h1>
        <p className="alert alert-success" role="status">
          {role === 'DESIGNER'
            ? 'Your designer account is waiting for admin approval. You can sign in once it is active.'
            : 'Your account is ready. Sign in to open the dashboard.'}
        </p>
        <p className="muted">Registered email: {email.trim()}</p>
        <Link className="button" to="/login">
          Go to sign in
        </Link>
      </section>
    );
  }

  return (
    <section className="card narrow">
      <h1>Create account</h1>
      <p className="muted">Choose the role that matches how you will use the platform.</p>

      {error !== null && (
        <p className="alert alert-error" role="alert">
          {error}
        </p>
      )}

      <form className="form" onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="register-email">Email</label>
          <input
            id="register-email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>

        <div className="field">
          <label htmlFor="register-name">Display name</label>
          <input
            id="register-name"
            name="display_name"
            type="text"
            autoComplete="name"
            required
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
          />
        </div>

        <div className="field">
          <label htmlFor="register-password">Password</label>
          <input
            id="register-password"
            name="password"
            type="password"
            autoComplete="new-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>

        <div className="field">
          <label htmlFor="register-role">Role</label>
          <select id="register-role" name="role" value={role} onChange={handleRoleChange}>
            <option value="CUSTOMER">Customer</option>
            <option value="DESIGNER">Interior designer</option>
          </select>
          <p className="hint">Designer accounts need admin approval before the first sign-in.</p>
        </div>

        <button className="button" type="submit" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>

      <p className="muted form-foot">
        Already registered? <Link to="/login">Sign in</Link>.
      </p>
    </section>
  );
}