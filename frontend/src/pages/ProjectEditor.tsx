
import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  ApiError,
  createProject,
  getProject,
  updateProject,
  getCatalogue,
} from '../api';
import type { Catalogue, ProjectInput } from '../types';

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
  const [imageUrls, setImageUrls] = useState('');

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
        setImageUrls(project.images.join('\n'));
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

    const images = [
      ...new Set(
        imageUrls
          .split('\n')
          .map((url) => url.trim())
          .filter(Boolean)
      ),
    ];

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
              Image URLs (maximum 8)
            </label>
            <textarea
              id="project-images"
              rows={4}
              value={imageUrls}
              onChange={(e) => setImageUrls(e.target.value)}
              placeholder="Enter one image URL per line"
            />
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
