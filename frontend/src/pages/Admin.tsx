import { useCallback, useEffect, useState } from 'react';
import { ApiError, adminApprove, adminListAccounts, adminSuspend } from '../api';
import { useAuth } from '../auth';
import type { AccountPublic, Status } from '../types';

type Filter = Status | 'ALL';

const FILTERS: Filter[] = ['PENDING', 'ACTIVE', 'SUSPENDED', 'ALL'];

const LABELS: Record<Filter, string> = {
  PENDING: 'Pending',
  ACTIVE: 'Active',
  SUSPENDED: 'Suspended',
  ALL: 'All accounts',
};

function badgeClass(status: Status): string {
  return `badge badge-${status.toLowerCase()}`;
}

export default function Admin() {
  const { account } = useAuth();
  const [rows, setRows] = useState<AccountPublic[]>([]);
  const [filter, setFilter] = useState<Filter>('PENDING');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const next = await adminListAccounts(filter === 'ALL' ? undefined : filter);
      setRows(next);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : 'Unable to load accounts.');
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    void load();
  }, [load]);

  async function change(accountId: string, action: (id: string) => Promise<AccountPublic>) {
    setBusyId(accountId);
    setError(null);
    try {
      await action(accountId);
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : 'Unable to change the account.');
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Account administration</h1>
          <p className="muted">Approve designers and suspend accounts that break the rules.</p>
        </div>
      </div>

      {error !== null && (
        <p className="alert alert-error" role="alert">
          {error}
        </p>
      )}

      <section className="card">
        <div className="toolbar">
          <div className="field">
            <label htmlFor="admin-filter">Show</label>
            <select
              id="admin-filter"
              value={filter}
              onChange={(event) => setFilter(event.target.value as Filter)}
            >
              {FILTERS.map((option) => (
                <option key={option} value={option}>
                  {LABELS[option]}
                </option>
              ))}
            </select>
          </div>
          <button type="button" className="button button-secondary" onClick={() => void load()}>
            Refresh
          </button>
        </div>

        {loading ? (
          <p className="page-state" role="status">
            Loading accounts…
          </p>
        ) : rows.length === 0 ? (
          <p className="page-state">No accounts match this filter.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Account</th>
                <th scope="col">Role</th>
                <th scope="col">Status</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>
                    <strong>{row.display_name}</strong>
                    <div className="muted">{row.email}</div>
                  </td>
                  <td>{row.role}</td>
                  <td>
                    <span className={badgeClass(row.status)}>{row.status}</span>
                  </td>
                  <td>
                    <div className="row-actions">
                      {row.status !== 'ACTIVE' && (
                        <button
                          type="button"
                          className="button"
                          disabled={busyId !== null}
                          onClick={() => void change(row.id, adminApprove)}
                        >
                          {busyId === row.id ? 'Working…' : 'Approve'}
                        </button>
                      )}
                      {row.status !== 'SUSPENDED' && row.id !== account?.id && (
                        <button
                          type="button"
                          className="button button-secondary"
                          disabled={busyId !== null}
                          onClick={() => void change(row.id, adminSuspend)}
                        >
                          Suspend
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}