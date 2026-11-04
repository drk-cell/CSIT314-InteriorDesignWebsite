import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, getCatalogue, listCompanies, searchProjects } from '../api';
import BudgetSlider from '../components/BudgetSlider';
import type { Catalogue, SearchResponse } from '../types';

function formatBudget(value: number): string {
  return `S$${value.toLocaleString('en-SG')}`;
}

export default function Search() {
  const [catalogue, setCatalogue] = useState<Catalogue | null>(null);
  const [designers, setDesigners] = useState<Record<string, string>>({});
  const [keyword, setKeyword] = useState('');
  const [category, setCategory] = useState('');
  const [style, setStyle] = useState('');
  const [low, setLow] = useState(0);
  const [high, setHigh] = useState(200000);
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    getCatalogue()
      .then((data) => {
        if (!live) return;
        setCatalogue(data);
        setLow(data.budget.min);
        setHigh(data.budget.max);
      })
      .catch(() => {
        if (live) setError('Cannot load the filters. Check that the backend is running.');
      });
    listCompanies()
      .then((rows) => {
        if (!live) return;
        setDesigners(Object.fromEntries(rows.map((row) => [row.id, row.name])));
      })
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, []);

  const run = useCallback(
    async (page: number) => {
      setLoading(true);
      setError(null);
      try {
        setResult(
          await searchProjects({
            keyword,
            category,
            style,
            budget_min: low,
            budget_max: high,
            page,
          }),
        );
      } catch (caught) {
        setError(caught instanceof ApiError ? caught.detail : 'Unable to search.');
        setResult(null);
      } finally {
        setLoading(false);
      }
    },
    [keyword, category, style, low, high],
  );

  useEffect(() => {
    if (catalogue === null) return;
    const timer = setTimeout(() => {
      void run(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [catalogue, run]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void run(1);
  }

  function clear() {
    if (catalogue === null) return;
    setKeyword('');
    setCategory('');
    setStyle('');
    setLow(catalogue.budget.min);
    setHigh(catalogue.budget.max);
  }

  const currentPage = result?.page ?? 1;
  const totalPages = result?.pages ?? 1;

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Find a project</h1>
          <p className="muted">Filter the catalogue by room, style and budget.</p>
        </div>
      </div>

      <section className="card">
        <form className="filter-bar" onSubmit={submit}>
          <div className="field">
            <label htmlFor="search-keyword">Keyword</label>
            <input
              id="search-keyword"
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
              placeholder="e.g. birch, calm, open"
            />
          </div>

          <div className="field">
            <label htmlFor="search-category">Room</label>
            <select
              id="search-category"
              value={category}
              onChange={(event) => setCategory(event.target.value)}
            >
              <option value="">All rooms</option>
              {catalogue?.categories.map((room) => (
                <option key={room} value={room}>
                  {room}
                </option>
              ))}
            </select>
          </div>

          <div className="field">
            <label htmlFor="search-style">Style</label>
            <select
              id="search-style"
              value={style}
              onChange={(event) => setStyle(event.target.value)}
            >
              <option value="">All styles</option>
              {catalogue?.styles.map((entry) => (
                <option key={entry} value={entry}>
                  {entry}
                </option>
              ))}
            </select>
          </div>

          <div className="field field-budget">
            <span className="field-label" id="budget-label">
              Budget
            </span>
            <output className="range-value">
              {formatBudget(low)} – {formatBudget(high)}
            </output>
            <BudgetSlider
              min={catalogue?.budget.min ?? 0}
              max={catalogue?.budget.max ?? 200000}
              step={catalogue?.budget.step ?? 5000}
              low={low}
              high={high}
              onChange={(nextLow, nextHigh) => {
                setLow(nextLow);
                setHigh(nextHigh);
              }}
            />
          </div>

          <div className="filter-actions">
            <button className="button" type="submit" disabled={loading}>
              {loading ? 'Searching…' : 'Search'}
            </button>
            <button
              className="button button-secondary"
              type="button"
              onClick={clear}
              disabled={loading}
            >
              Clear
            </button>
          </div>
        </form>
      </section>

      {error !== null && (
        <p className="alert alert-error" role="alert">
          {error}
        </p>
      )}

      {result !== null && (
        <p className="result-count">
          {result.total} project{result.total === 1 ? '' : 's'} found
        </p>
      )}

      {result !== null && result.items.length === 0 && (
        <section className="card empty-state">
          <h2>No projects match these filters</h2>
          <p className="muted">Widen the budget or choose a different room.</p>
          <button className="button button-secondary" type="button" onClick={clear}>
            Clear all filters
          </button>
        </section>
      )}

      {result !== null && result.items.length > 0 && (
        <section className="grid">
          {result.items.map((project) => (
            <article className="card project-card" key={project.id}>
              {project.images.length > 0 && (
                <img className="project-photo" src={project.images[0]} alt={project.title} />
              )}
              <div className="project-body">
                <p className="project-eyebrow">
                  {project.category} · {project.style}
                </p>
                <h2>{project.title}</h2>
                <p className="project-designer">
                  {designers[project.company_id] ?? 'Independent studio'}
                </p>
                <p className="project-budget">
                  {formatBudget(project.budget_min)} – {formatBudget(project.budget_max)}
                </p>
                <div className="actions">
                  <Link
                    className="button button-secondary"
                    to={`/designers/${project.company_id}`}
                  >
                    View designer
                  </Link>
                </div>
              </div>
            </article>
          ))}
        </section>
      )}

      {totalPages > 1 && (
        <div className="pager">
          <button
            type="button"
            className="button button-secondary"
            disabled={currentPage <= 1 || loading}
            onClick={() => void run(currentPage - 1)}
          >
            Previous
          </button>
          <span className="muted">
            Page {currentPage} of {totalPages}
          </span>
          <button
            type="button"
            className="button button-secondary"
            disabled={currentPage >= totalPages || loading}
            onClick={() => void run(currentPage + 1)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}