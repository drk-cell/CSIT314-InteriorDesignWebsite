import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ApiError,
  acceptAppointment,
  cancelAppointment,
  listAppointments,
  listCompanies,
} from '../api';
import { useAuth } from '../auth';
import type { AppointmentPublic, CompanyPublic } from '../types';

function longDay(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString('en-SG', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  });
}

export default function Appointments() {
  const { account } = useAuth();
  const isDesigner = account?.role === 'DESIGNER';
  const [rows, setRows] = useState<AppointmentPublic[]>([]);
  const [companies, setCompanies] = useState<CompanyPublic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    Promise.all([listAppointments(), listCompanies()])
      .then(([appointments, found]) => {
        if (!live) return;
        setRows(appointments);
        setCompanies(found);
      })
      .catch((caught: unknown) => {
        if (live) {
          setError(caught instanceof ApiError ? caught.detail : 'Unable to load appointments.');
        }
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, []);

  function companyName(companyId: string): string {
    const found = companies.find((entry) => entry.id === companyId);
    return found === undefined ? 'Designer' : found.name;
  }

  async function act(appointmentId: string, action: 'accept' | 'cancel') {
    setBusy(appointmentId);
    setError(null);
    try {
      const updated =
        action === 'accept'
          ? await acceptAppointment(appointmentId)
          : await cancelAppointment(appointmentId);
      setRows((current) =>
        current.map((entry) => (entry.id === updated.id ? updated : entry))
      );
    } catch (caught: unknown) {
      setError(caught instanceof ApiError ? caught.detail : 'That action did not work.');
    } finally {
      setBusy(null);
    }
  }

  if (loading) return <p className="page-state">Loading appointments…</p>;

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>{isDesigner ? 'Consultation inbox' : 'My appointments'}</h1>
          <p className="muted">
            {isDesigner
              ? 'Customers who asked for one hour with your company.'
              : 'One hour consultations you booked with designers.'}
          </p>
        </div>
        {!isDesigner && (
          <Link className="button" to="/designers">
            Book a consultation
          </Link>
        )}
      </div>

      {error !== null && (
        <p className="alert alert-error" role="alert">
          {error}
        </p>
      )}

      {rows.length === 0 ? (
        <section className="card empty-state">
          <h2>No appointments yet</h2>
          <p className="muted">
            {isDesigner
              ? 'When a customer books an hour, it appears here.'
              : 'Open a designer profile and press Book a consultation.'}
          </p>
        </section>
      ) : (
        <section className="card">
          <table className="table">
            <thead>
              <tr>
                <th>{isDesigner ? 'Customer' : 'Designer'}</th>
                <th>Day</th>
                <th>Time</th>
                <th>What they need</th>
                <th>State</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((entry) => (
                <tr key={entry.id}>
                  <td>
                    {isDesigner
                      ? entry.customer_name === ''
                        ? 'Customer'
                        : entry.customer_name
                      : companyName(entry.company_id)}
                  </td>
                  <td>{longDay(entry.appointment_date)}</td>
                  <td>{entry.appointment_time}</td>
                  <td>{entry.requirements === '' ? '—' : entry.requirements}</td>
                  <td>
                    <span className={`badge badge-${entry.state.toLowerCase()}`}>
                      {entry.state}
                    </span>
                  </td>
                  <td>
                    <div className="actions">
                      {isDesigner && entry.state === 'PENDING' && (
                        <button
                          className="button button-secondary"
                          type="button"
                          disabled={busy === entry.id}
                          onClick={() => act(entry.id, 'accept')}
                        >
                          Accept
                        </button>
                      )}
                      {entry.state !== 'CANCELLED' && (
                        <button
                          className="button button-secondary"
                          type="button"
                          disabled={busy === entry.id}
                          onClick={() => act(entry.id, 'cancel')}
                        >
                          Cancel
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </div>
  );
}
