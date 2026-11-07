import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, getShortlist, unsaveProject } from '../api';
import type { ProjectPublic } from '../types';

function formatBudget(value: number): string {
  return `S$${value.toLocaleString('en-SG')}`;
}

export default function Saved() {
  const [items, setItems] = useState<ProjectPublic[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    getShortlist()
      .then((data) => {
        if (live) setItems(data.items);
      })
      .catch((caught: unknown) => {
        if (live) {
          setError(caught instanceof ApiError ? caught.detail : 'Unable to load saved projects.');
        }
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, []);

  async function remove(project: ProjectPublic) {
    setBusy(project.id);
    setError(null);
    try {
      await unsaveProject(project.id);
      setItems((current) => current.filter((entry) => entry.id !== project.id));
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : 'Unable to remove the project.');
    } finally {
      setBusy(null);
    }
  }

  if (loading) return <p className="page-state">Loading saved projects…</p>;

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Saved projects</h1>
          <p className="muted">Shortlisted work, ready to compare.</p>
        </div>
      </div>

      {error !== null && (
        <p className="alert alert-error" role="alert">
          {error}
        </p>
      )}

      {items.length === 0 ? (
        <section className="card empty-state">
          <h2>Nothing saved yet</h2>
          <p className="muted">Open a project from the search page and save it here.</p>
          <Link className="button button-secondary" to="/search">
            Find a project
          </Link>
        </section>
      ) : (
        <section className="grid">
          {items.map((project) => (
            <article className="card project-card" key={project.id}>
              {project.images.length > 0 && (
                <img className="project-photo" src={project.images[0]} alt={project.title} />
              )}
              <div className="project-body">
                <p className="project-eyebrow">
                  {project.category} · {project.style}
                </p>
                <h2>
                  <Link to={`/projects/${project.id}`}>{project.title}</Link>
                </h2>
                <p className="project-budget">
                  {formatBudget(project.budget_min)} – {formatBudget(project.budget_max)}
                </p>
                <div className="actions">
                  <button
                    className="button button-secondary"
                    type="button"
                    onClick={() => void remove(project)}
                    disabled={busy === project.id}
                  >
                    {busy === project.id ? 'Removing…' : 'Remove'}
                  </button>
                </div>
              </div>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}