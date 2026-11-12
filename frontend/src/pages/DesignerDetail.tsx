import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ApiError, companyById } from '../api';
import { useAuth } from '../auth';
import type { CompanyPublic } from '../types';

export default function DesignerDetail() {
  const { companyId } = useParams<{ companyId: string }>();
  const { account } = useAuth();
  const [company, setCompany] = useState<CompanyPublic | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (companyId === undefined) {
      setError('No designer was named.');
      setLoading(false);
      return;
    }

    let cancelled = false;

    companyById(companyId)
      .then((found) => {
        if (!cancelled) setCompany(found);
      })
      .catch((caught: unknown) => {
        if (cancelled) return;
        setError(caught instanceof ApiError ? caught.detail : 'Unable to load the profile.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [companyId]);

  if (loading) {
    return (
      <div className="page-state" role="status">
        Loading the profile…
      </div>
    );
  }

  if (error !== null || company === null) {
    return (
      <div className="stack">
        <p className="alert alert-error" role="alert">
          {error ?? 'Designer not found.'}
        </p>
        <p>
          <Link to="/designers">Back to the designer list</Link>
        </p>
      </div>
    );
  }

  return (
    <div className="stack">
      <p>
        <Link to="/designers">Back to the designer list</Link>
      </p>

      <section className="card">
        {company.logo_url !== '' && (
          <img className="company-logo" src={company.logo_url} alt={`${company.name} logo`} />
        )}
        <h1>{company.name}</h1>
        {company.location !== '' && <p className="muted">{company.location}</p>}
        {company.description !== '' && <p>{company.description}</p>}

        <dl className="facts">
          <div>
            <dt>Contact email</dt>
            <dd>
              <a href={`mailto:${company.contact_email}`}>{company.contact_email}</a>
            </dd>
          </div>
          {company.contact_phone !== '' && (
            <div>
              <dt>Contact phone</dt>
              <dd>
                <a href={`tel:${company.contact_phone.replace(/\s+/g, '')}`}>
                  {company.contact_phone}
                </a>
              </dd>
            </div>
          )}
          {company.meeting_address !== '' && (
            <div>
              <dt>Meeting address</dt>
              <dd>{company.meeting_address}</dd>
            </div>
          )}
          {company.call_link !== '' && (
            <div>
              <dt>Video call</dt>
              <dd>
                <a href={company.call_link} target="_blank" rel="noreferrer">
                  {company.call_link}
                </a>
              </dd>
            </div>
          )}
          {company.offers_online && company.call_link === '' && (
            <div>
              <dt>Video call</dt>
              <dd className="muted">
                The link is shared after your booking is confirmed.
              </dd>
            </div>
          )}
          <div>
            <dt>Profile updated</dt>
            <dd>{new Date(company.updated_at).toLocaleDateString()}</dd>
          </div>
        </dl>

        {account?.role === 'CUSTOMER' && (
          <div className="actions">
            <Link className="button" to={`/quotes/new/${company.id}`}>
              Request a quote
            </Link>
            <Link className="button button-secondary" to={`/designers/${company.id}/book`}>
              Book a consultation
            </Link>
          </div>
        )}
      </section>
    </div>
  );
}