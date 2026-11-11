
import { useEffect, useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  ApiError,
  createProject,
  getProject,
  updateProject,
  getCatalogue,
  suggestTagsFromUpload,
  uploadImage,
} from '../api';
import type { Catalogue, ProjectInput } from '../types';

const MAX_IMAGES = 8;

interface QueueItem {
  key: string;
  url: string;
  tags: string[];
}

function splitTags(value: string): string[] {
  return value
    .split(',')
    .map((entry) => entry.trim())
    .filter(Boolean);
}

function mergeTags(current: string[], extra: string[]): string[] {
  const seen = new Set(current.map((tag) => tag.toLowerCase()));
  const out = [...current];
  for (const tag of extra) {
    const key = tag.toLowerCase();
    if (!seen.has(key)) {
      seen.add(key);
      out.push(tag);
    }
  }
  return out;
}

export default function ProjectEditor() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const editing = projectId !== undefined;

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('');
  const [style, setStyle] = useState('');
  const [budgetMin, setBudgetMin] = useState('0');
  const [budgetMax, setBudgetMax] = useState('0');
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [tags, setTags] = useState('');
  const [uploading, setUploading] = useState(false);

  const [catalogue, setCatalogue] = useState<Catalogue | null>(null);
  const [loading, setLoading] = useState(editing);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Load the available categories and styles.
  useEffect(() => {
    let active = true;

    getCatalogue()
      .then((data) => {
        if (active) setCatalogue(data);
      })
      .catch(() => {
        if (active) setError('Unable to load project categories.');
      });

    return () => {
      active = false;
    };
  }, []);

  // Load an existing project when editing.
  useEffect(() => {
    if (!projectId) {
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);

    getProject(projectId)
      .then((project) => {
        if (!active) return;
        setTitle(project.title);
        setDescription(project.description);
        setCategory(project.category);
        setStyle(project.style);
        setBudgetMin(String(project.budget_min));
        setBudgetMax(String(project.budget_max));
        setQueue(project.images.map((url) => ({ key: url, url, tags: [] })));
        setTags(project.tags.join(', '));
      })
      .catch((caught: unknown) => {
        if (!active) return;
        setError(
          caught instanceof ApiError
            ? caught.detail
            : 'Unable to load project.'
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [projectId]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) return;

    setError(null);
    setSuccess(null);

    const min = Number(budgetMin);
    const max = Number(budgetMax);

    // Frontend validation.
    if (!title.trim() || !category || !style) {
      setError('Please complete all required fields.');
      return;
    }

    if (
      !budgetMin.trim() ||
      !budgetMax.trim() ||
      !Number.isSafeInteger(min) ||
      !Number.isSafeInteger(max) ||
      min < 0 ||
      max < min
    ) {
      setError('Please enter a valid budget range.');
      return;
    }

    const images = queue.map((item) => item.url);

    if (images.length > 8) {
      setError('A project can contain at most 8 images.');
      return;
    }

    const body: ProjectInput = {
      title: title.trim(),
      description: description.trim(),
      category,
      style,
      budget_min: min,
      budget_max: max,
      images,
      tags: tags
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean),
    };

    setSaving(true);

    try {
      if (projectId) {
        await updateProject(projectId, body);
        setSuccess('Project updated successfully!');
      } else {
        const created = await createProject(body);
        setSuccess('Project created successfully!');
        navigate(`/projects/${created.id}/edit`, { replace: true });
      }
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.detail
          : 'Unable to save project.'
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleAdd(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = '';
    if (files.length === 0 || uploading) return;

    const room = MAX_IMAGES - queue.length;
    if (room <= 0) {
      setError('A project can show 8 photos. Remove one before adding another.');
      return;
    }

    setUploading(true);
    setError(null);
    const added: QueueItem[] = [];
    const warnings: string[] = [];

    try {
      for (const file of files.slice(0, room)) {
        const stored = await uploadImage(file);
        const reading = await suggestTagsFromUpload(file);

        // A photo is kept even when the analyser refuses to read it. The
        // designer chose the picture; only the tags depend on the reading.
        const tags = reading.subject === 'other' ? [] : reading.tags;
        if (reading.subject === 'other') {
          warnings.push(`${file.name} does not look like an interior, so it added no tags.`);
        } else if ((reading.objects ?? []).length === 0 && reading.objects !== undefined) {
          warnings.push(`No furniture was recognised in ${file.name}, so it added no tags.`);
        }
        added.push({ key: stored.url, url: stored.url, tags });
      }

      setQueue((previous) => [...previous, ...added]);
      const extra = added.flatMap((item) => item.tags);
      if (extra.length > 0) {
        setTags((previous) => mergeTags(splitTags(previous), extra).join(', '));
      }
      if (files.length > room) {
        warnings.push(`Only ${room} more photo${room === 1 ? '' : 's'} fitted, so the rest were skipped.`);
      }
      if (warnings.length > 0) setError(warnings.join(' '));
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.detail
          : 'That file could not be read as a photo.'
      );
    } finally {
      setUploading(false);
    }
  }

  function removeImage(item: QueueItem) {
    const keptByOthers = queue
      .filter((other) => other.key !== item.key)
      .flatMap((other) => other.tags.map((tag) => tag.toLowerCase()));

    // A tag stays when another photo, or the designer, still wants it.
    const kept = splitTags(tags).filter((tag) => {
      const own = item.tags.some((entry) => entry.toLowerCase() === tag.toLowerCase());
      return !own || keptByOthers.includes(tag.toLowerCase());
    });

    setQueue((previous) => previous.filter((other) => other.key !== item.key));
    setTags(kept.join(', '));
  }

  if (loading) {
    return <p className="page-state">Loading project...</p>;
  }

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>{editing ? 'Edit Project' : 'Create Project'}</h1>
          <p className="muted">
            Enter your interior design project information.
          </p>
        </div>
      </div>

      {error && (
        <p className="alert alert-error" role="alert">{error}</p>
      )}

      {success && (
        <p className="alert alert-success" role="status">{success}</p>
      )}

      <section className="card">
        <form className="form" onSubmit={handleSubmit}>

          <div className="field">
            <label htmlFor="project-title">Project Title *</label>
            <input
              id="project-title"
              required
              maxLength={120}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Modern HDB Renovation"
            />
          </div>

          <div className="field">
            <label htmlFor="project-desc">Description</label>
            <textarea
              id="project-desc"
              maxLength={2000}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the renovation project"
            />
          </div>

          <div className="field">
            <label htmlFor="project-category">Category *</label>
            <select
              id="project-category"
              required
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="">Select category</option>
              {catalogue?.categories.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          </div>

          <div className="field">
            <label htmlFor="project-style">Style *</label>
            <select
              id="project-style"
              required
              value={style}
              onChange={(e) => setStyle(e.target.value)}
            >
              <option value="">Select style</option>
              {catalogue?.styles.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
          </div>

          <div className="field">
            <label htmlFor="budget-min">Minimum Budget (S$) *</label>
            <input
              id="budget-min"
              type="number"
              required
              min="0"
              step="1"
              value={budgetMin}
              onChange={(e) => setBudgetMin(e.target.value)}
            />
          </div>

          <div className="field">
            <label htmlFor="budget-max">Maximum Budget (S$) *</label>
            <input
              id="budget-max"
              type="number"
              required
              min="0"
              step="1"
              value={budgetMax}
              onChange={(e) => setBudgetMax(e.target.value)}
            />
          </div>

          <div className="field">
            <label htmlFor="project-images">
              Project photos ({queue.length} of {MAX_IMAGES})
            </label>
            <div className="image-queue">
              {queue.map((item) => (
                <figure key={item.key} className="queue-item">
                  <img src={item.url} alt="A project photo" />
                  <button
                    type="button"
                    className="queue-remove"
                    aria-label="Remove this photo"
                    title="Remove this photo"
                    onClick={() => removeImage(item)}
                  >
                    ×
                  </button>
                </figure>
              ))}
              {queue.length < MAX_IMAGES && (
                <label className="queue-add">
                  <span>{uploading ? 'Reading…' : '+ Add photo'}</span>
                  <input
                    id="project-images"
                    type="file"
                    multiple
                    accept="image/jpeg,image/png,image/webp"
                    onChange={(event) => void handleAdd(event)}
                    disabled={uploading}
                    hidden
                  />
                </label>
              )}
            </div>
            <p className="hint">
              Up to {MAX_IMAGES} photos. Each photo adds its tags to the field
              below. Remove a photo to remove the tags it added.
            </p>
          </div>

          <div className="field">
            <label htmlFor="project-tags">Description tags</label>
            <input
              id="project-tags"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="warm neutrals, bright, oak"
            />
            <p className="hint">
              Separate tags with commas. Customers can search them.
            </p>
          </div>

          <div className="actions">
            <button className="button" type="submit" disabled={saving}>
              {saving ? 'Saving...' : editing ? 'Update Project' : 'Create Project'}
            </button>
            <Link className="button button-secondary" to="/dashboard">
              Back to Dashboard
            </Link>
          </div>

        </form>
      </section>
    </div>
  );
}
