import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ApiError, listCompanies, submitQuoteRequest } from '../api';
import type { CompanyPublic } from '../types';

export default function RequestQuote() {
  const { companyId } = useParams<{ companyId: string }>();
  const navigate = useNavigate();
  const [company, setCompany] = useState<CompanyPublic | null>(null);
  const [title, setTitle] = useState('');
  const [scope, setScope] = useState('');
  const [budgetMin, setBudgetMin] = useState('20000');
  const [budgetMax, setBudgetMax] = useState('40000');
  const [target, setTarget] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    listCompanies()
      .then((rows) => {
        if (live) setCompany(rows.find((row) => row.id === companyId) ?? null);
      })
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, [companyId]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!companyId || busy) return;
    setBusy(true);
    setError(null);
    const toCents = (value: string) => Math.round(Number(value) * 100);
    try {
      const created = await submitQuoteRequest({
        company_id: companyId,
        title: title.trim(),
        scope: scope.trim(),
        budget_min_cents: toCents(budgetMin),
        budget_max_cents: toCents(budgetMax),
        target_cents: target.trim() === '' ? undefined : toCents(target),
      });
      navigate(`/quotes/${created.id}`);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : 'Unable to send the request.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Request a quote</h1>
          <p className="muted">
            {company === null ? 'Loading designer…' : `Sent to ${company.name}.`}
          </p>
        </div>
      </div>

      {error !== null && (
        <p className="alert alert-error" role="alert">
          {error}
        </p>
      )}

      <section className="card narrow">
        <form className="form" onSubmit={submit}>
          <div className="field">
            <label htmlFor="request-title">What do you need done?</label>
            <input
              id="request-title"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Kitchen renovation"
              maxLength={120}
              required
            />
          </div>

          <div className="field">
            <label htmlFor="request-scope">Scope</label>
            <textarea
              id="request-scope"
              rows={5}
              maxLength={2000}
              value={scope}
              onChange={(event) => setScope(event.target.value)}
              placeholder="Flat size, rooms, what you want changed, timeline."
              required
            />
          </div>

          <div className="field">
            <label htmlFor="request-min">Budget floor (S$)</label>
            <input
              id="request-min"
              type="number"
              min="0"
              step="100"
              value={budgetMin}
              onChange={(event) => setBudgetMin(event.target.value)}
              required
            />
          </div>

          <div className="field">
            <label htmlFor="request-max">Budget ceiling (S$)</label>
            <input
              id="request-max"
              type="number"
              min="0"
              step="100"
              value={budgetMax}
              onChange={(event) => setBudgetMax(event.target.value)}
              required
            />
          </div>

          <div className="field">
            <label htmlFor="request-target">Target price (S$), optional</label>
            <input
              id="request-target"
              type="number"
              min="0"
              step="100"
              value={target}
              onChange={(event) => setTarget(event.target.value)}
              placeholder="What you would like to pay"
            />
            <p className="hint">
              The designer sees this. It is a starting point for negotiation, not a
              binding offer.
            </p>
          </div>

          <div className="actions">
            <button className="button" type="submit" disabled={busy}>
              {busy ? 'Sending…' : 'Send request'}
            </button>
            <Link className="button button-secondary" to={`/designers/${companyId ?? ''}`}>
              Back to designer
            </Link>
          </div>
        </form>
      </section>
    </div>
  );
}