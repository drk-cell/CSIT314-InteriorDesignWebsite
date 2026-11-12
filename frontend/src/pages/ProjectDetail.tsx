import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  ApiError,
  getProject,
  getShortlist,
  listCompanies,
  recordView,
  reportProject,
  reportReasons,
  saveProject,
  unsaveProject,
} from '../api';
import { useAuth } from '../auth';
import type { CompanyPublic, ProjectPublic } from '../types';

function formatBudget(value: number): string {
  return `S$${value.toLocaleString('en-SG')}`;
}

export default function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>();
  const { account } = useAuth();
  const [project, setProject] = useState<ProjectPublic | null>(null);
  const [companies, setCompanies] = useState<CompanyPublic[]>([]);
  const [active, setActive] = useState(0);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reportOpen, setReportOpen] = useState(false);
  const [reasons, setReasons] = useState<string[]>([]);
  const [reason, setReason] = useState('');
  const [comments, setComments] = useState('');
  const [reportBusy, setReportBusy] = useState(false);
  const [reportNotice, setReportNotice] = useState<string | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);
  const counted = useRef(false);

  useEffect(() => {
    if (!projectId) return;
    let live = true;
    setLoading(true);
    setError(null);

    getProject(projectId)
      .then((data) => {
        if (!live) return;
        setProject(data);
        setActive(0);
      })
      .catch((caught: unknown) => {
        if (!live) return;
        setError(caught instanceof ApiError ? caught.detail : 'Unable to load the project.');
      })
      .finally(() => {
        if (live) setLoading(false);
      });

    listCompanies()
      .then((rows) => {
        if (live) setCompanies(rows);
      })
      .catch(() => undefined);

    return () => {
      live = false;
    };
  }, [projectId]);

  useEffect(() => {
    if (account?.role !== 'CUSTOMER') return;
    getShortlist()
      .then((data) => setSaved(data.project_ids.includes(projectId ?? '')))
      .catch(() => undefined);
  }, [account?.role, projectId]);

  useEffect(() => {
    if (!projectId || counted.current) return;
    counted.current = true;
    recordView(projectId).catch(() => undefined);
  }, [projectId]);

  async function openReport() {
    setReportOpen(true);
    setReportError(null);
    if (reasons.length > 0) return;
    try {
      setReasons(await reportReasons());
    } catch {
      setReportError('Unable to load the reasons.');
    }
  }

  async function submitReport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!projectId || reason === '') return;
    setReportBusy(true);
    setReportError(null);
    try {
      await reportProject({ project_id: projectId, reason, comments });
      setReportNotice('Report sent. The administrator will review it.');
      setReportOpen(false);
      setReason('');
      setComments('');
    } catch (caught) {
      setReportError(
        caught instanceof ApiError ? caught.detail : 'Unable to send the report.'
      );
    } finally {
      setReportBusy(false);
    }
  }

  async function toggleSaved() {
    if (!projectId || busy) return;
    setBusy(true);
    setError(null);
    try {
      if (saved) {
        await unsaveProject(projectId);
        setSaved(false);
        setProject((current) =>
          current === null
            ? current
            : { ...current, shortlist_count: Math.max(0, current.shortlist_count - 1) },
        );
      } else {
        await saveProject(projectId);
        setSaved(true);
        setProject((current) =>
          current === null ? current : { ...current, shortlist_count: current.shortlist_count + 1 },
        );
      }
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : 'Unable to change the saved list.');
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <p className="page-state">Loading project…</p>;

  if (project === null) {
    return (
      <div className="stack">
        <p className="alert alert-error" role="alert">
          {error ?? 'The project was not found.'}
        </p>
        <Link className="button button-secondary" to="/search">
          Back to search
        </Link>
      </div>
    );
  }

  const image = project.images[active];

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <p className="project-eyebrow">
            {project.category} · {project.style}
          </p>
          <h1>{project.title}</h1>
          <p className="muted">
            {(() => {
              const name = companies.find((row) => row.id === project.company_id)?.name;
              return name !== undefined ? (
                <Link to={`/designers/${project.company_id}`}>{name}</Link>
              ) : (
                'Independent studio'
              );
            })()}
          </p>
        </div>
        {account?.role === 'CUSTOMER' && (
          <button
            className={saved ? 'button button-secondary' : 'button'}
            type="button"
            onClick={() => void toggleSaved()}
            disabled={busy}
          >
            {saved ? 'Saved — remove' : 'Save to shortlist'}
          </button>
        )}
      </div>

      {error !== null && (
        <p className="alert alert-error" role="alert">
          {error}
        </p>
      )}

      <div className="detail-layout">
        <div className="stack">
          {image !== undefined && (
            <img className="detail-photo" src={image} alt={project.title} />
          )}
          {project.images.length > 1 && (
            <div className="thumb-row">
              {project.images.map((url, index) => (
                <button
                  key={url}
                  type="button"
                  className={index === active ? 'thumb thumb-active' : 'thumb'}
                  onClick={() => setActive(index)}
                  aria-label={`Show photo ${index + 1}`}
                >
                  <img src={url} alt="" />
                </button>
              ))}
            </div>
          )}
        </div>

        <aside className="card stack">
          <div>
            <p className="field-label">Budget</p>
            <p className="detail-budget">
              {formatBudget(project.budget_min)} – {formatBudget(project.budget_max)}
            </p>
          </div>

          <p className="muted">{project.description || 'No description yet.'}</p>

          {project.tags.length > 0 && (
            <div>
              <p className="field-label">Tags</p>
              <div className="tag-list">
                {project.tags.map((tag) => (
                  <span className="tag-pill" key={tag}>
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          <dl className="facts">
            <div>
              <dt>Views</dt>
              <dd>{project.view_count}</dd>
            </div>
            <div>
              <dt>Saved by</dt>
              <dd>{project.shortlist_count}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>
                {project.status === 'CURRENT'
                  ? 'Current'
                  : project.status === 'TAKEN_DOWN'
                    ? 'Taken down'
                    : 'Past'}
              </dd>
            </div>
          </dl>

          <Link className="button button-secondary" to={`/designers/${project.company_id}`}>
            View designer
          </Link>

          {account?.role === 'CUSTOMER' && (
            <div className="stack">
              {reportNotice !== null && (
                <p className="alert alert-success" role="status">
                  {reportNotice}
                </p>
              )}
              {reportError !== null && (
                <p className="alert alert-error" role="alert">
                  {reportError}
                </p>
              )}
              {reportOpen ? (
                <form className="form" onSubmit={submitReport}>
                  <div className="field">
                    <label htmlFor="report-reason">Reason</label>
                    <select
                      id="report-reason"
                      required
                      value={reason}
                      onChange={(event) => setReason(event.target.value)}
                    >
                      <option value="">Choose a reason</option>
                      {reasons.map((entry) => (
                        <option key={entry} value={entry}>
                          {entry}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="report-comments">Comments (optional)</label>
                    <textarea
                      id="report-comments"
                      rows={3}
                      maxLength={1000}
                      value={comments}
                      onChange={(event) => setComments(event.target.value)}
                    />
                  </div>
                  <div className="actions">
                    <button
                      className="button"
                      type="submit"
                      disabled={reportBusy || reason === ''}
                    >
                      {reportBusy ? 'Sending…' : 'Send report'}
                    </button>
                    <button
                      className="button button-secondary"
                      type="button"
                      onClick={() => setReportOpen(false)}
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              ) : (
                <button
                  type="button"
                  className="link-button"
                  onClick={() => void openReport()}
                >
                  Report this project
                </button>
              )}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}