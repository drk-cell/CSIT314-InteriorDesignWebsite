import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  acceptQuote,
  answerQuoteRequest,
  ApiError,
  cancelQuoteRequest,
  counterQuoteRequest,
  declineQuote,
  getQuoteRequest,
  refuseQuoteRequest,
  reviseQuote,
} from '../api';
import { useAuth } from '../auth';
import { formatCents } from '../format';
import type { QuotePublic, QuoteRequestDetail } from '../types';

export default function QuoteDetail() {
  const { requestId } = useParams<{ requestId: string }>();
  const { account } = useAuth();
  const [request, setRequest] = useState<QuoteRequestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [total, setTotal] = useState('');
  const [validDays, setValidDays] = useState('14');
  const [gstIncluded, setGstIncluded] = useState(false);
  const [note, setNote] = useState('');
  const [target, setTarget] = useState('');
  const [counterNote, setCounterNote] = useState('');
  const [reason, setReason] = useState('');

  const load = useCallback(async () => {
    if (!requestId) return;
    setError(null);
    try {
      const data = await getQuoteRequest(requestId);
      setRequest(data);
      const current = data.quotes.find((entry) => entry.state === 'OFFERED');
      if (current) {
        setTotal((current.total_cents / 100).toString());
        setGstIncluded(current.gst_included);
      }
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : 'Unable to load the request.');
    } finally {
      setLoading(false);
    }
  }, [requestId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function run(action: () => Promise<unknown>, message: string) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await action();
      setNotice(message);
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : 'The action failed.');
    } finally {
      setBusy(false);
    }
  }

  function centsFromInput(value: string): number {
    return Math.round(Number(value) * 100);
  }

  function submitAnswer(event: FormEvent<HTMLFormElement>, reviseId?: string) {
    event.preventDefault();
    const amount = centsFromInput(total);
    if (!Number.isFinite(amount) || amount <= 0) {
      setError('Enter a total above zero.');
      return;
    }
    const body = {
      total_cents: amount,
      valid_days: Number(validDays),
      gst_included: gstIncluded,
      note,
    };
    if (reviseId) {
      void run(() => reviseQuote(reviseId, body), 'New version sent.');
    } else if (requestId) {
      void run(() => answerQuoteRequest(requestId, body), 'Quote sent.');
    }
  }

  if (loading) return <p className="page-state">Loading request…</p>;
  if (request === null) {
    return (
      <div className="stack">
        <p className="alert alert-error" role="alert">
          {error ?? 'The request was not found.'}
        </p>
        <Link className="button button-secondary" to="/quotes">
          Back to requests
        </Link>
      </div>
    );
  }

  const isDesigner = account?.role === 'DESIGNER';
  const offered: QuotePublic | undefined = request.quotes.find(
    (entry) => entry.state === 'OFFERED',
  );
  const isOpen = request.state === 'PENDING' || request.state === 'ANSWERED';

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <p className="project-eyebrow">{isDesigner ? 'Incoming request' : 'Your request'}</p>
          <h1>{request.title}</h1>
          <p className="muted">
            Budget {formatCents(request.budget_min_cents)} –{' '}
            {formatCents(request.budget_max_cents)}
            {request.target_cents !== null &&
              ` · target ${formatCents(request.target_cents)}`}
          </p>
        </div>
        <span className={`badge badge-${request.state.toLowerCase()}`}>{request.state}</span>
      </div>

      {error !== null && (
        <p className="alert alert-error" role="alert">
          {error}
        </p>
      )}
      {notice !== null && (
        <p className="alert alert-success" role="status">
          {notice}
        </p>
      )}

      <div className="detail-layout">
        <div className="stack">
          <section className="card">
            <h2>Scope</h2>
            <p className="muted">{request.scope}</p>
            {request.closed_reason !== '' && (
              <p className="hint">Closed: {request.closed_reason}</p>
            )}
          </section>

          <section className="card">
            <h2>Versions</h2>
            {request.quotes.length === 0 ? (
              <p className="muted">No quote yet.</p>
            ) : (
              <table className="table">
                <thead>
                  <tr>
                    <th>Version</th>
                    <th>Total</th>
                    <th>GST</th>
                    <th>Valid until</th>
                    <th>State</th>
                  </tr>
                </thead>
                <tbody>
                  {request.quotes.map((quote) => (
                    <tr key={quote.id}>
                      <td>v{quote.version}</td>
                      <td>{formatCents(quote.grand_total_cents)}</td>
                      <td>
                        {quote.gst_included ? 'included' : `+ ${formatCents(quote.gst_cents)}`}
                      </td>
                      <td>{quote.valid_until}</td>
                      <td>
                        <span className={`badge badge-${quote.state.toLowerCase()}`}>
                          {quote.state}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            {offered?.note !== undefined && offered.note !== '' && (
              <p className="hint">Note: {offered.note}</p>
            )}
          </section>

          {request.counters.length > 0 && (
            <section className="card">
              <h2>Target prices named</h2>
              <ul className="plain-list">
                {request.counters.map((entry) => (
                  <li key={entry.id}>
                    <strong>{formatCents(entry.target_cents)}</strong>
                    {entry.note !== '' && ` — ${entry.note}`}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>

        <aside className="card stack">
          <h2>{isDesigner ? 'Respond' : 'Decide'}</h2>

          {!isOpen && !(isDesigner && request.state === 'ANSWERED') && (
            <p className="muted">This request is closed.</p>
          )}

          {isDesigner && request.state === 'PENDING' && (
            <form className="form" onSubmit={(event) => submitAnswer(event)}>
              <div className="field">
                <label htmlFor="quote-total">Total (S$)</label>
                <input
                  id="quote-total"
                  type="number"
                  min="1"
                  step="0.01"
                  value={total}
                  onChange={(event) => setTotal(event.target.value)}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="quote-days">Valid for (days)</label>
                <input
                  id="quote-days"
                  type="number"
                  min="1"
                  max="90"
                  value={validDays}
                  onChange={(event) => setValidDays(event.target.value)}
                  required
                />
              </div>
              <label className="check">
                <input
                  type="checkbox"
                  checked={gstIncluded}
                  onChange={(event) => setGstIncluded(event.target.checked)}
                />
                The total already includes 9% GST
              </label>
              <div className="field">
                <label htmlFor="quote-note">Note</label>
                <textarea
                  id="quote-note"
                  rows={3}
                  maxLength={500}
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder="What the price covers"
                />
              </div>
              <button className="button" type="submit" disabled={busy}>
                {busy ? 'Sending…' : 'Send quote'}
              </button>
            </form>
          )}

          {isDesigner && request.state === 'ANSWERED' && offered !== undefined && (
            <form className="form" onSubmit={(event) => submitAnswer(event, offered.id)}>
              <p className="hint">
                Current version v{offered.version}. Sending a new version marks this one
                superseded. Three versions per request.
              </p>
              <div className="field">
                <label htmlFor="quote-total">New total (S$)</label>
                <input
                  id="quote-total"
                  type="number"
                  min="1"
                  step="0.01"
                  value={total}
                  onChange={(event) => setTotal(event.target.value)}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="quote-days">Valid for (days)</label>
                <input
                  id="quote-days"
                  type="number"
                  min="1"
                  max="90"
                  value={validDays}
                  onChange={(event) => setValidDays(event.target.value)}
                  required
                />
              </div>
              <label className="check">
                <input
                  type="checkbox"
                  checked={gstIncluded}
                  onChange={(event) => setGstIncluded(event.target.checked)}
                />
                The total already includes 9% GST
              </label>
              <div className="field">
                <label htmlFor="quote-note">Note</label>
                <textarea
                  id="quote-note"
                  rows={3}
                  maxLength={500}
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                />
              </div>
              <button className="button" type="submit" disabled={busy}>
                {busy ? 'Sending…' : 'Send new version'}
              </button>
            </form>
          )}

          {!isDesigner && offered !== undefined && isOpen && (
            <div className="stack">
              <p className="muted">
                Offered {formatCents(offered.grand_total_cents)}, valid until{' '}
                {offered.valid_until}.
              </p>
              <button
                className="button"
                type="button"
                disabled={busy}
                onClick={() => void run(() => acceptQuote(offered.id), 'Quote accepted.')}
              >
                Accept quote
              </button>
              <button
                className="button button-secondary"
                type="button"
                disabled={busy}
                onClick={() => void run(() => declineQuote(offered.id, reason), 'Quote declined.')}
              >
                Decline quote
              </button>
            </div>
          )}

          {!isDesigner && isOpen && (
            <form
              className="form"
              onSubmit={(event) => {
                event.preventDefault();
                const amount = centsFromInput(target);
                if (!Number.isFinite(amount) || amount <= 0) {
                  setError('Enter a target above zero.');
                  return;
                }
                void run(
                  () => counterQuoteRequest(request.id, amount, counterNote),
                  'Target price sent.',
                );
              }}
            >
              <div className="field">
                <label htmlFor="target-price">Name a target price (S$)</label>
                <input
                  id="target-price"
                  type="number"
                  min="1"
                  step="0.01"
                  value={target}
                  onChange={(event) => setTarget(event.target.value)}
                />
                <p className="hint">
                  The designer sees it and may revise. It does not bind either side.
                </p>
              </div>
              <div className="field">
                <label htmlFor="target-note">Why</label>
                <input
                  id="target-note"
                  value={counterNote}
                  onChange={(event) => setCounterNote(event.target.value)}
                  placeholder="Optional"
                />
              </div>
              <button className="button button-secondary" type="submit" disabled={busy}>
                Send target
              </button>
            </form>
          )}

          {!isDesigner && request.state === 'ANSWERED' && (
            <div className="field">
              <label htmlFor="decline-reason">Reason for declining</label>
              <input
                id="decline-reason"
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder="Optional"
              />
            </div>
          )}

          {request.state === 'PENDING' && isDesigner && (
            <button
              className="link-button"
              type="button"
              disabled={busy}
              onClick={() =>
                void run(
                  () => refuseQuoteRequest(request.id, reason),
                  'Request declined.',
                )
              }
            >
              Decline to quote
            </button>
          )}

          {!isDesigner && isOpen && (
            <button
              className="link-button"
              type="button"
              disabled={busy}
              onClick={() =>
                void run(() => cancelQuoteRequest(request.id, reason), 'Request cancelled.')
              }
            >
              Cancel request
            </button>
          )}

          <Link className="button button-secondary" to="/quotes">
            Back to requests
          </Link>
        </aside>
      </div>
    </div>
  );
}