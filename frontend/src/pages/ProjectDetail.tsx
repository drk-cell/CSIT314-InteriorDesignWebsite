import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  ApiError,
  getProject,
  getShortlist,
  listCompanies,
  recordView,
  saveProject,
  unsaveProject,
} from '../api';
import { useAuth } from '../auth';
import type { ProjectPublic } from '../types';

function formatBudget(value: number): string {
  return `S$${value.toLocaleString('en-SG')}`;
}

export default function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>();
  const { account } = useAuth();
  const [project, setProject] = useState<ProjectPublic | null>(null);
  const [designer, setDesigner] = useState('');
  const [active, setActive] = useState(0);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
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
        if (!live) return;
        setDesigner(rows.find((row) => row.id === project?.company_id)?.name ?? '');
      })
      .catch(() => undefined);

    return () => {
      live = false;
    };
    // ``project`` is read for the designer name only; the fetch runs per id.
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
            {designer !== '' ? (
              <Link to={`/designers/${project.company_id}`}>{designer}</Link>
            ) : (
              'Independent studio'
            )}
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
              <dd>{project.status === 'CURRENT' ? 'Current' : 'Past'}</dd>
            </div>
          </dl>

          <Link className="button button-secondary" to={`/designers/${project.company_id}`}>
            View designer
          </Link>
        </aside>
      </div>
    </div>
  );
}