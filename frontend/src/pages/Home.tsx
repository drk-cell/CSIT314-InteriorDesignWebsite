import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, health } from '../api';
import { useAuth } from '../auth';
import type { HealthResponse } from '../types';

type HealthState = 'loading' | 'online' | 'offline';

function describeFailure(caught: unknown): string {
  if (!(caught instanceof ApiError)) {
    return 'Unable to reach the backend. Start the API server and reload.';
  }
  if (caught.status >= 500) {
    return `${caught.detail} The API server may be stopped or crashing.`;
  }
  return caught.detail;
}

export default function Home() {
  const { account } = useAuth();
  const [state, setState] = useState<HealthState>('loading');
  const [info, setInfo] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    health()
      .then((result) => {
        if (cancelled) return;
        setInfo(result);
        setState('online');
      })
      .catch((caught: unknown) => {
        if (cancelled) return;
        setError(describeFailure(caught));
        setState('offline');
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="stack">
      <section className="card hero">
        <p className="eyebrow">Interior design marketplace</p>
        <h1>Plan a room with a designer who fits the space.</h1>
        <p className="lede">
          Customers post a brief, compare designers, and follow the work in one place. Designers
          publish a profile and take on projects that match their style.
        </p>
        <div className="actions">
          {account === null ? (
            <>
              <Link className="button" to="/register">
                Create an account
              </Link>
              <Link className="button button-secondary" to="/login">
                Sign in
              </Link>
            </>
          ) : (
            <Link className="button" to="/dashboard">
              Open dashboard
            </Link>
          )}
        </div>
      </section>

      <section className="card" aria-labelledby="service-status">
        <h2 id="service-status">Service status</h2>
        {state === 'loading' && <p className="muted">Checking the backend…</p>}
        {state === 'online' && info !== null && (
          <dl className="facts">
            <div>
              <dt>Status</dt>
              <dd>
                <span className="badge badge-active">{info.status}</span>
              </dd>
            </div>
            <div>
              <dt>Version</dt>
              <dd>{info.version}</dd>
            </div>
            <div>
              <dt>Server time</dt>
              <dd className="mono">{info.time}</dd>
            </div>
          </dl>
        )}
        {state === 'offline' && (
          <p className="alert alert-error" role="alert">
            {error}
          </p>
        )}
      </section>

      <section className="grid">
        <article className="card">
          <h2>For customers</h2>
          <p className="muted">
            Describe the space, share measurements, and compare quotes from shortlisted designers.
          </p>
        </article>
        <article className="card">
          <h2>For designers</h2>
          <p className="muted">
            Keep a public profile, answer briefs, and manage commissions from a single dashboard.
          </p>
        </article>
      </section>
    </div>
  );
}