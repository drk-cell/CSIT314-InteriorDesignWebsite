import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, searchProjects } from '../api';
import type { SearchParams, SearchResponse } from '../types';

function formatBudget(value: number): string {
  return `S$${value.toLocaleString('en-SG')}`;
}

export default function Search() {
  const [keyword, setKeyword] = useState('');
  const [category, setCategory] = useState('');
  const [style, setStyle] = useState('');
  const [budgetMin, setBudgetMin] = useState('');
  const [budgetMax, setBudgetMax] = useState('');
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(
    async (page: number) => {
      setLoading(true);
      setError(null);
      const params: SearchParams = {
        keyword,
        category,
        style,
        budget_min: budgetMin === '' ? undefined : Number(budgetMin),
        budget_max: budgetMax === '' ? undefined : Number(budgetMax),
        page,
      };
      try {
        setResult(await searchProjects(params));
      } catch (caught) {
        setError(caught instanceof ApiError ? caught.detail : 'Unable to search.');
        setResult(null);
      } finally {
        setLoading(false);
      }
    },
    [keyword, category, style, budgetMin, budgetMax],
  );

  useEffect(() => {
    void run(1);
  }, [run]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void run(1);
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
        <form className="filter-form" onSubmit={submit}>
          <div className="field">
            <label htmlFor="search-keyword">Keyword</label>
            <input
              id="search-keyword"
              value={keyword}
              onChange={(event) => setKeyword(event.target.value)}
              placeholder="e.g. living room"
            />
          </div>
          <div className="field">
            <label htmlFor="search-category">Category</label>
            <input
              id="search-category"
              value={category}
              onChange={(event) => setCategory(event.target.value)}
              placeholder="e.g. Living Room"
            />
          </div>
          <div className="field">
            <label htmlFor="search-style">Style</label>
            <input
              id="search-style"
              value={style}
              onChange={(event) => setStyle(event.target.value)}
              placeholder="e.g. Minimal"
            />
          </div>
          <div className="field">
            <label htmlFor="search-budget-min">Minimum budget</label>
            <input
              id="search-budget-min"
              type="number"
              min={0}
              value={budgetMin}
              onChange={(event) => setBudgetMin(event.target.value)}
              placeholder="e.g. 20000"
            />
          </div>
          <div className="field">
            <label htmlFor="search-budget-max">Maximum budget</label>
            <input
              id="search-budget-max"
              type="number"
              min={0}
              value={budgetMax}
              onChange={(event) => setBudgetMax(event.target.value)}
              placeholder="e.g. 60000"
            />
          </div>
          <button className="button" type="submit" disabled={loading}>
            {loading ? 'Searching…' : 'Search'}
          </button>
        </form>
      </section>

      {error !== null && (
        <p className="alert alert-error" role="alert">
          {error}
        </p>
      )}

      {!loading && result !== null && (
        <>
          <p className="muted">
            {result.total} project{result.total === 1 ? '' : 's'} found.
          </p>

          {result.items.length === 0 ? (
            <p className="page-state">Nothing matches these filters.</p>
          ) : (
            <section className="grid">
              {result.items.map((project) => (
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
                    {project.style} · {project.category}
                  </p>
                  <p className="muted">
                    Budget {formatBudget(project.budget_min)} –{' '}
                    {formatBudget(project.budget_max)}
                  </p>
                  <div className="actions">
                    <Link className="button button-secondary" to={`/designers/${project.company_id}`}>
                      View designer
                    </Link>
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
        </>
      )}
    </div>
  );
}