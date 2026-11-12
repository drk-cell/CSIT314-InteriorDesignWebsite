import { useEffect, useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { ApiError, createCompany, myCompany, updateMyCompany } from '../api';
import { useAuth } from '../auth';
import type { CompanyInput, CompanyPublic } from '../types';

const EMPTY: CompanyInput = {
  name: '',
  description: '',
  contact_email: '',
  contact_phone: '',
  location: '',
  meeting_address: '',
  call_link: '',
  logo_url: '',
};

function toInput(company: CompanyPublic): CompanyInput {
  return {
    name: company.name,
    description: company.description,
    contact_email: company.contact_email,
    contact_phone: company.contact_phone,
    location: company.location,
    meeting_address: company.meeting_address,
    call_link: company.call_link,
    logo_url: company.logo_url,
  };
}

export default function Profile() {
  const { account } = useAuth();
  const [company, setCompany] = useState<CompanyPublic | null>(null);
  const [form, setForm] = useState<CompanyInput>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    myCompany()
      .then((found) => {
        if (cancelled) return;
        setCompany(found);
        setForm(toInput(found));
      })
      .catch((caught: unknown) => {
        if (cancelled) return;
        if (caught instanceof ApiError && caught.status === 404) {
          setCompany(null);
          return;
        }
        setError(caught instanceof ApiError ? caught.detail : 'Unable to load the profile.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  function change(field: keyof CompanyInput) {
    return (event: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      const value = event.target.value;
      setForm((current) => ({ ...current, [field]: value }));
    };
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const creating = company === null;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const saved = creating ? await createCompany(form) : await updateMyCompany(form);
      setCompany(saved);
      setForm(toInput(saved));
      setNotice(creating ? 'Profile created.' : 'Profile saved.');
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : 'Unable to save the profile.');
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="page-state" role="status">
        Loading your company profile…
      </div>
    );
  }

  const creating = company === null;

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Company profile</h1>
          <p className="muted">
            {creating
              ? 'Customers see this page before they contact you. Create it once, then keep it current.'
              : 'This is what a customer reads before they contact you.'}
          </p>
        </div>
        {account !== null && <span className="badge badge-active">{account.display_name}</span>}
      </div>

      {error !== null && (
        <p className="alert alert-error" role="alert">
          {error}
        </p>
      )}

      {notice !== null && (
        <p className="alert alert-success" role="status">
          {notice}
        </p>
      )}

      <section className="card">
        <form className="form" onSubmit={submit}>
          <div className="field">
            <label htmlFor="company-name">Company name</label>
            <input
              id="company-name"
              required
              maxLength={120}
              value={form.name}
              onChange={change('name')}
            />
          </div>

          <div className="field">
            <label htmlFor="company-description">About the studio</label>
            <textarea
              id="company-description"
              rows={4}
              maxLength={2000}
              value={form.description}
              onChange={change('description')}
            />
          </div>

          <div className="field">
            <label htmlFor="company-email">Contact email</label>
            <input
              id="company-email"
              type="email"
              required
              maxLength={254}
              value={form.contact_email}
              onChange={change('contact_email')}
            />
          </div>

          <div className="field">
            <label htmlFor="company-phone">Contact phone</label>
            <input
              id="company-phone"
              maxLength={40}
              value={form.contact_phone}
              onChange={change('contact_phone')}
            />
          </div>

          <div className="field">
            <label htmlFor="company-location">Service area</label>
            <input
              id="company-location"
              maxLength={120}
              value={form.location}
              onChange={change('location')}
            />
          </div>

          <div className="field">
            <label htmlFor="company-meeting">Meeting address</label>
            <input
              id="company-meeting"
              maxLength={240}
              value={form.meeting_address}
              onChange={change('meeting_address')}
            />
            <p className="hint">
              Where an in person consultation takes place. Leave it empty to offer
              video calls only.
            </p>
          </div>

          <div className="field">
            <label htmlFor="company-call">Video call link</label>
            <input
              id="company-call"
              maxLength={500}
              value={form.call_link}
              onChange={change('call_link')}
            />
            <p className="hint">
              The room customers join. It must start with http:// or https://.
            </p>
          </div>

          <div className="field">
            <label htmlFor="company-logo">Logo address</label>
            <input
              id="company-logo"
              maxLength={500}
              value={form.logo_url}
              onChange={change('logo_url')}
            />
            <p className="hint">Paste a link to an image. Leave it empty if you have none.</p>
          </div>

          <div className="actions">
            <button className="button" type="submit" disabled={saving}>
              {saving ? 'Saving…' : creating ? 'Create profile' : 'Save changes'}
            </button>
          </div>
        </form>
      </section>

      {!creating && company !== null && (
        <section className="card">
          <h2>Record</h2>
          <dl className="facts">
            <div>
              <dt>Profile id</dt>
              <dd className="mono">{company.id}</dd>
            </div>
            <div>
              <dt>Last changed</dt>
              <dd>{new Date(company.updated_at).toLocaleString()}</dd>
            </div>
          </dl>
        </section>
      )}
    </div>
  );
}