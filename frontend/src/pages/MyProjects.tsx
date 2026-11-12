
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ApiError,
  deleteProject,
  myProjects,
  updateProject,
} from '../api';
import type { ProjectPublic, ProjectStatus } from '../types';

export default function MyProjects() {
  const [projects, setProjects] = useState<ProjectPublic[]>([]);

  // Filters
  const [searchName, setSearchName] = useState('');
  const [statusFilter, setStatusFilter] =
    useState<ProjectStatus | ''>('');

  // Page status
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Retrieve projects whenever the filters change.
  useEffect(() => {
    let active = true;

    const timer = setTimeout(() => {
      setLoading(true);
      setError(null);

      myProjects({
        name: searchName,
        status: statusFilter || undefined,
      })
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
    }, 250);

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [searchName, statusFilter]);

  // Delete one of the designer's projects.
  async function handleDelete(project: ProjectPublic) {
    const confirmed = window.confirm(
      `Are you sure you want to delete "${project.title}"? This cannot be undone.`
    );

    if (!confirmed) return;

    setBusyId(project.id);
    setError(null);
    setNotice(null);

    try {
      await deleteProject(project.id);

      // Remove the deleted project from the screen.
      setProjects((current) =>
        current.filter((item) => item.id !== project.id)
      );

      setNotice(`"${project.title}" was deleted successfully.`);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.detail
          : 'Unable to delete project.'
      );
    } finally {
      setBusyId(null);
    }
  }

  // Change a project's status between CURRENT and PAST.
  async function handleStatusChange(project: ProjectPublic) {
    const newStatus: ProjectStatus =
      project.status === 'CURRENT' ? 'PAST' : 'CURRENT';

    setBusyId(project.id);
    setError(null);
    setNotice(null);

    try {
      const updated = await updateProject(project.id, {
        status: newStatus,
      });

      setProjects((current) =>
        current
          .map((item) =>
            item.id === updated.id ? updated : item
          )
          .filter(
            (item) =>
              !statusFilter || item.status === statusFilter
          )
      );

      setNotice(`"${project.title}" is now ${newStatus.toLowerCase()}.`);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.detail
          : 'Unable to update project status.'
      );
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>My Projects</h1>
          <p className="muted">
            Search, filter and manage your renovation portfolio.
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

      {notice && (
        <p className="alert alert-success" role="status">
          {notice}
        </p>
      )}

      {/* Search and filter controls */}
      <section className="card">
        <div className="filter-form">
          <div className="field">
            <label htmlFor="project-search">
              Search by Project Title
            </label>
            <input
              id="project-search"
              type="search"
              placeholder="Search projects..."
              value={searchName}
              onChange={(event) =>
                setSearchName(event.target.value)
              }
            />
          </div>

          <div className="field">
            <label htmlFor="project-status">
              Project Status
            </label>
            <select
              id="project-status"
              value={statusFilter}
              onChange={(event) =>
                setStatusFilter(
                  event.target.value as ProjectStatus | ''
                )
              }
            >
              <option value="">All Statuses</option>
              <option value="CURRENT">Current</option>
              <option value="PAST">Past</option>
            </select>
          </div>

          <button
            type="button"
            className="button button-secondary"
            onClick={() => {
              setSearchName('');
              setStatusFilter('');
            }}
          >
            Clear Filters
          </button>
        </div>
      </section>

      {loading ? (
        <p className="page-state" role="status">
          Loading projects...
        </p>
      ) : !error && (
        <>
          <p className="muted">
            {projects.length} project
            {projects.length === 1 ? '' : 's'} found ·{' '}
            {projects.reduce((total, project) => total + project.view_count, 0)} views ·{' '}
            {projects.reduce((total, project) => total + project.shortlist_count, 0)} saves
          </p>

          {projects.length === 0 ? (
            <section className="card">
              <h2>No projects found</h2>
              <p className="muted">
                Try changing your filters or creating a new project.
              </p>
            </section>
          ) : (
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
                    Budget: S$
                    {project.budget_min.toLocaleString()}
                    {' – S$'}
                    {project.budget_max.toLocaleString()}
                  </p>

                  <p className="muted">
                    {project.view_count} view{project.view_count === 1 ? '' : 's'} ·{' '}
                    {project.shortlist_count} save{project.shortlist_count === 1 ? '' : 's'}
                  </p>

                  <p>
                    <span
                      className={
                        project.status === 'CURRENT'
                          ? 'badge badge-active'
                          : project.status === 'TAKEN_DOWN'
                            ? 'badge badge-suspended'
                            : 'badge'
                      }
                    >
                      {project.status === 'CURRENT'
                        ? 'Current'
                        : project.status === 'TAKEN_DOWN'
                          ? 'Taken down'
                          : 'Past'}
                    </span>
                  </p>

                  <div className="actions">
                    <Link
                      className="button"
                      to={`/projects/${project.id}/edit`}
                    >
                      Edit
                    </Link>

                    {project.status !== 'TAKEN_DOWN' && (
                      <button
                        type="button"
                        className="button button-secondary"
                        disabled={busyId !== null}
                        onClick={() =>
                          void handleStatusChange(project)
                        }
                      >
                        {project.status === 'CURRENT'
                          ? 'Mark as Past'
                          : 'Mark as Current'}
                      </button>
                    )}

                    <button
                      type="button"
                      className="button button-secondary"
                      disabled={busyId !== null}
                      onClick={() =>
                        void handleDelete(project)
                      }
                    >
                      {busyId === project.id
                        ? 'Processing...'
                        : 'Delete'}
                    </button>
                  </div>
                </article>
              ))}
            </section>
          )}
        </>
      )}
    </div>
  );
}
