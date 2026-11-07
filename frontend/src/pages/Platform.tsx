import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import {
  ApiError,
  createCategory,
  getReport,
  listAllCategories,
  patchCategory,
} from '../api';
import type { CategoryPublic, Report } from '../types';

const PERIODS = ['daily', 'weekly', 'monthly'] as const;

export default function Platform() {
  const [categories, setCategories] = useState<CategoryPublic[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [period, setPeriod] = useState<(typeof PERIODS)[number]>('daily');
  const [buckets, setBuckets] = useState('14');
  const [newName, setNewName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadCategories = useCallback(async () => {
    try {
      setCategories(await listAllCategories());
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : 'Unable to load categories.');
    }
  }, []);

  const loadReport = useCallback(async (nextPeriod: string, nextBuckets: string) => {
    try {
      setReport(await getReport(nextPeriod, Number(nextBuckets)));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : 'Unable to load the report.');
    }
  }, []);

  useEffect(() => {
    void loadCategories();
  }, [loadCategories]);

  useEffect(() => {
    void loadReport(period, buckets);
  }, [loadReport, period, buckets]);

  async function addCategory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy || newName.trim() === '') return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await createCategory(newName.trim());
      setNewName('');
      setNotice('Category added.');
      await loadCategories();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : 'Unable to add the category.');
    } finally {
      setBusy(false);
    }
  }

  async function toggle(category: CategoryPublic) {
    setBusy(true);
    setError(null);
    try {
      await patchCategory(category.id, { active: !category.active });
      await loadCategories();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : 'Unable to change the category.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Platform management</h1>
          <p className="muted">Category upkeep and activity reports.</p>
        </div>
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

      <section className="card">
        <h2>Categories</h2>
        <form className="filter-bar" onSubmit={addCategory}>
          <div className="field">
            <label htmlFor="new-category">New category</label>
            <input
              id="new-category"
              value={newName}
              onChange={(event) => setNewName(event.target.value)}
              placeholder="e.g. Rooftop"
              maxLength={60}
            />
          </div>
          <div className="filter-actions">
            <button className="button" type="submit" disabled={busy}>
              Add
            </button>
          </div>
        </form>

        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>State</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {categories.map((category) => (
              <tr key={category.id}>
                <td>{category.name}</td>
                <td>
                  <span className={`badge badge-${category.active ? 'active' : 'suspended'}`}>
                    {category.active ? 'Active' : 'Archived'}
                  </span>
                </td>
                <td>
                  <button
                    className="link-button"
                    type="button"
                    onClick={() => void toggle(category)}
                    disabled={busy}
                  >
                    {category.active ? 'Archive' : 'Restore'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="card">
        <div className="page-head">
          <h2>Activity report</h2>
          <div className="toolbar">
            <div className="field">
              <label htmlFor="report-period">Period</label>
              <select
                id="report-period"
                value={period}
                onChange={(event) =>
                  setPeriod(event.target.value as (typeof PERIODS)[number])
                }
              >
                {PERIODS.map((entry) => (
                  <option key={entry} value={entry}>
                    {entry}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="report-buckets">Buckets</label>
              <select
                id="report-buckets"
                value={buckets}
                onChange={(event) => setBuckets(event.target.value)}
              >
                {['7', '14', '30'].map((entry) => (
                  <option key={entry} value={entry}>
                    {entry}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {report === null ? (
          <p className="muted">No report yet.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>{period === 'daily' ? 'Day' : period === 'weekly' ? 'Week' : 'Month'}</th>
                <th>Accounts</th>
                <th>Projects</th>
                <th>Requests</th>
                <th>Quotes</th>
              </tr>
            </thead>
            <tbody>
              {report.buckets.map((bucket) => (
                <tr key={bucket.label}>
                  <td>{bucket.label}</td>
                  <td>{bucket.accounts}</td>
                  <td>{bucket.projects}</td>
                  <td>{bucket.quote_requests}</td>
                  <td>{bucket.quotes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}