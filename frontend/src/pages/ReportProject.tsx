import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ApiError, getProject, reportProject, reportReasons } from '../api';
import type { ProjectPublic } from '../types';

export default function ReportProject() {
  const { projectId } = useParams<{ projectId: string }>();
  const [project, setProject] = useState<ProjectPublic | null>(null);
  const [reasons, setReasons] = useState<string[]>([]);
  const [reason, setReason] = useState('');
  const [comments, setComments] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  useEffect(() => {
    if (projectId === undefined) return;
    let live = true;
    setLoading(true);
    setError(null);
    Promise.all([getProject(projectId), reportReasons()])
      .then(([found, list]) => {
        if (!live) return;
        setProject(found);
        setReasons(list);
      })
      .catch((caught: unknown) => {
        if (live) {
          setError(
            caught instanceof ApiError ? caught.detail : 'Unable to load the project.'
          );
        }
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, [projectId]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (projectId === undefined || reason === '') return;
    setSending(true);
    setError(null);
    try {
      await reportProject({ project_id: projectId, reason, comments });
      setSent(true);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : 'Unable to send the report.');
    } finally {
      setSending(false);
    }
  }

  if (loading) return <p className="page-state">Loading the project…</p>;

  if (sent) {
    return (
      <div className="stack">
        <section className="card narrow">
          <h1>Report sent</h1>
          <p>
            The administrator will review this report and decide what happens to the
            project.
          </p>
          <div className="actions">
            <Link className="button" to={`/projects/${projectId ?? ''}`}>
              Back to the project
            </Link>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="stack">
      <p>
        <Link to={`/projects/${projectId ?? ''}`}>Back to the project</Link>
      </p>

      <div className="page-head">
        <div>
          <h1>Report a project</h1>
          <p className="muted">
            {project === null
              ? 'Tell the administrator what is wrong.'
              : `Reporting “${project.title}”.`}
          </p>
        </div>
      </div>

      {error !== null && (
        <p className="alert alert-error" role="alert">
          {error}
        </p>
      )}

      <form className="card form" onSubmit={submit}>
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
            rows={4}
            maxLength={1000}
            value={comments}
            onChange={(event) => setComments(event.target.value)}
            placeholder="What is wrong with this project?"
          />
        </div>

        <div className="actions">
          <button className="button" type="submit" disabled={sending || reason === ''}>
            {sending ? 'Sending…' : 'Send report'}
          </button>
          <Link className="button button-secondary" to={`/projects/${projectId ?? ''}`}>
            Cancel
          </Link>
        </div>
      </form>
    </div>
  );
}
