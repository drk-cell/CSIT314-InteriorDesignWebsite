import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, listQuoteRequests } from '../api';
import { useAuth } from '../auth';
import { formatCents } from '../format';
import type { QuoteRequestPublic } from '../types';

export default function Quotes() {
  const { account } = useAuth();
  const [requests, setRequests] = useState<QuoteRequestPublic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    listQuoteRequests()
      .then((data) => {
        if (live) setRequests(data);
      })
      .catch((caught: unknown) => {
        if (live) {
          setError(caught instanceof ApiError ? caught.detail : 'Unable to load requests.');
        }
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, []);

  const isDesigner = account?.role === 'DESIGNER';

  if (loading) return <p className="page-state">Loading requests…</p>;

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>{isDesigner ? 'Quote inbox' : 'My quote requests'}</h1>
          <p className="muted">
            {isDesigner
              ? 'Requests customers sent to your company.'
              : 'Requests you sent to designers.'}
          </p>
        </div>
        {!isDesigner && (
          <Link className="button" to="/designers">
            Request a quote
          </Link>
        )}
      </div>

      {error !== null && (
        <p className="alert alert-error" role="alert">
          {error}
        </p>
      )}

      {requests.length === 0 ? (
        <section className="card empty-state">
          <h2>No requests yet</h2>
          <p className="muted">
            {isDesigner
              ? 'When a customer asks for a price, it appears here.'
              : 'Open a designer profile and press Request a quote.'}
          </p>
        </section>
      ) : (
        <section className="card">
          <table className="table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Budget</th>
                <th>State</th>
                <th>Sent</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {requests.map((request) => (
                <tr key={request.id}>
                  <td>
                    <Link to={`/quotes/${request.id}`}>{request.title}</Link>
                  </td>
                  <td>
                    {formatCents(request.budget_min_cents)} –{' '}
                    {formatCents(request.budget_max_cents)}
                  </td>
                  <td>
                    <span className={`badge badge-${request.state.toLowerCase()}`}>
                      {request.state}
                    </span>
                  </td>
                  <td>{new Date(request.created_at).toLocaleDateString('en-SG')}</td>
                  <td>
                    <Link className="button button-secondary" to={`/quotes/${request.id}`}>
                      Open
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}