import { useCallback, useEffect, useState } from 'react';
import {
  ApiError,
  adminApprove,
  adminListAccounts,
  adminSuspend,
  listProjectReports,
  resolveProjectReport,
} from '../api';
import { useAuth } from '../auth';
import type { AccountPublic, ProjectReportPublic, Status } from '../types';

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
  const [reports, setReports] = useState<ProjectReportPublic[]>([]);
  const [reportBusy, setReportBusy] = useState<string | null>(null);
  const [takeDown, setTakeDown] = useState<Record<string, boolean>>({});
  const [suspend, setSuspend] = useState<Record<string, boolean>>({});

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

  const loadReports = useCallback(async () => {
    try {
      setReports(await listProjectReports());
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : 'Unable to load reports.');
      setReports([]);
    }
  }, []);

  useEffect(() => {
    void load();
    void loadReports();
  }, [load, loadReports]);

  async function closeReport(reportId: string, take: boolean, susp: boolean) {
    setReportBusy(reportId);
    setError(null);
    try {
      await resolveProjectReport(reportId, {
        take_down: take,
        suspend_designer: susp,
      });
      await loadReports();
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : 'Unable to close the report.');
    } finally {
      setReportBusy(null);
    }
  }

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

      <section className="card">
        <div className="page-head">
          <div>
            <h2>Reported projects</h2>
            <p className="muted">
              Customers flagged these. Take the project down, suspend the designer, or
              dismiss the report.
            </p>
          </div>
          <button
            type="button"
            className="button button-secondary"
            onClick={() => void loadReports()}
          >
            Refresh reports
          </button>
        </div>

        {reports.length === 0 ? (
          <p className="page-state">No reports yet.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Project</th>
                <th scope="col">Reporter</th>
                <th scope="col">Reason</th>
                <th scope="col">Status</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((row) => (
                <tr key={row.id}>
                  <td>
                    <strong>{row.project_title}</strong>
                    <div className="muted">{row.designer_name}</div>
                    <div className="muted">{row.designer_email}</div>
                  </td>
                  <td>{row.customer_name}</td>
                  <td>
                    {row.reason}
                    {row.comments !== '' && (
                      <div className="muted">{row.comments}</div>
                    )}
                  </td>
                  <td>
                    <span className={`badge badge-${row.status.toLowerCase()}`}>
                      {row.status}
                    </span>
                  </td>
                  <td>
                    {row.status === 'OPEN' ? (
                      <div className="stack">
                        <label className="check-row">
                          <input
                            type="checkbox"
                            checked={takeDown[row.id] === true}
                            onChange={(event) =>
                              setTakeDown((current) => ({
                                ...current,
                                [row.id]: event.target.checked,
                              }))
                            }
                          />
                          Take down project
                        </label>
                        <label className="check-row">
                          <input
                            type="checkbox"
                            checked={suspend[row.id] === true}
                            onChange={(event) =>
                              setSuspend((current) => ({
                                ...current,
                                [row.id]: event.target.checked,
                              }))
                            }
                          />
                          Suspend designer
                        </label>
                        <div className="row-actions">
                          <button
                            type="button"
                            className="button"
                            disabled={reportBusy !== null}
                            onClick={() =>
                              void closeReport(
                                row.id,
                                takeDown[row.id] === true,
                                suspend[row.id] === true
                              )
                            }
                          >
                            {reportBusy === row.id ? 'Closing…' : 'Apply and close'}
                          </button>
                          <button
                            type="button"
                            className="button button-secondary"
                            disabled={reportBusy !== null}
                            onClick={() => void closeReport(row.id, false, false)}
                          >
                            Dismiss
                          </button>
                        </div>
                      </div>
                    ) : (
                      <span className="muted">Closed</span>
                    )}
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