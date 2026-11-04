
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, myProjects } from '../api';
import type { ProjectPublic } from '../types';

export default function MyProjects() {
  const [projects, setProjects] = useState<ProjectPublic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    myProjects()
      .then((data) => {
        if (active) setProjects(data);
      })
      .catch((caught: unknown) => {
        if (!active) return;
        setError(
          caught instanceof ApiError
            ? caught.detail
            : 'Unable to load projects.'
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return <p className="page-state">Loading projects...</p>;
  }

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>My Projects</h1>
          <p className="muted">
            View and edit your renovation projects.
          </p>
        </div>

        <Link className="button" to="/projects/new">
          Create New Project
        </Link>
      </div>

      {error && (
        <p className="alert alert-error" role="alert">
          {error}
        </p>
      )}

      {!error && projects.length === 0 && (
        <section className="card">
          <p>You have not created any projects yet.</p>
        </section>
      )}

      <section className="grid">
        {projects.map((project) => (
          <article className="card" key={project.id}>
            {project.images.length > 0 && (
              <img
                className="project-photo"
                src={project.images[0]}
                alt={project.title}
              />
            )}

            <h2>{project.title}</h2>

            <p className="muted">
              {project.category} — {project.style}
            </p>

            <p>
              Budget: S${project.budget_min.toLocaleString()}
              {' - '}
              S${project.budget_max.toLocaleString()}
            </p>

            <p>Status: {project.status}</p>

            <div className="actions">
              <Link
                className="button"
                to={`/projects/${project.id}/edit`}
              >
                Edit Project
              </Link>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
