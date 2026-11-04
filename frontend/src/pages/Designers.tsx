import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ApiError, listCompanies } from '../api';
import type { CompanyPublic } from '../types';

export default function Designers() {
  const [companies, setCompanies] = useState<CompanyPublic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    listCompanies()
      .then((rows) => {
        if (!cancelled) setCompanies(rows);
      })
      .catch((caught: unknown) => {
        if (cancelled) return;
        setError(caught instanceof ApiError ? caught.detail : 'Unable to load designers.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Interior designers</h1>
          <p className="muted">Every studio with a published profile.</p>
        </div>
      </div>

      {error !== null && (
        <p className="alert alert-error" role="alert">
          {error}
        </p>
      )}

      {loading ? (
        <p className="page-state" role="status">
          Loading designers…
        </p>
      ) : companies.length === 0 ? (
        <p className="page-state">No designer has published a profile yet.</p>
      ) : (
        <section className="grid">
          {companies.map((company) => (
            <article className="card" key={company.id}>
              {company.logo_url !== '' && (
                <img className="company-logo" src={company.logo_url} alt={`${company.name} logo`} />
              )}
              <h2>{company.name}</h2>
              {company.location !== '' && <p className="muted">{company.location}</p>}
              {company.description !== '' && <p>{company.description}</p>}
              <div className="actions">
                <Link className="button button-secondary" to={`/designers/${company.id}`}>
                  View profile
                </Link>
              </div>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}