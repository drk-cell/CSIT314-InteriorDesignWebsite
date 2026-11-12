import { useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  ApiError,
  bookAppointment,
  companyById,
  listSlots,
} from '../api';
import type { AppointmentPublic, CompanyPublic } from '../types';

const BOOKING_DAYS = 14;

function isoDay(day: Date): string {
  const month = String(day.getMonth() + 1).padStart(2, '0');
  const date = String(day.getDate()).padStart(2, '0');
  return `${day.getFullYear()}-${month}-${date}`;
}

function dayLabel(day: Date): string {
  return day.toLocaleDateString('en-SG', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  });
}

/** The next two weeks, today first. */
function bookingDays(): Date[] {
  const today = new Date();
  return Array.from({ length: BOOKING_DAYS }, (_, offset) => {
    return new Date(today.getFullYear(), today.getMonth(), today.getDate() + offset);
  });
}

export default function BookConsultation() {
  const { companyId } = useParams<{ companyId: string }>();
  const days = useMemo(bookingDays, []);
  const [company, setCompany] = useState<CompanyPublic | null>(null);
  const [day, setDay] = useState<string>(isoDay(days[0]));
  const [slots, setSlots] = useState<string[]>([]);
  const [time, setTime] = useState<string>('');
  const [requirements, setRequirements] = useState<string>('');
  const [loadingSlots, setLoadingSlots] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [booked, setBooked] = useState<AppointmentPublic | null>(null);

  useEffect(() => {
    if (companyId === undefined) return;
    companyById(companyId)
      .then(setCompany)
      .catch((caught: unknown) => {
        setError(caught instanceof ApiError ? caught.detail : 'Unable to load the designer.');
      });
  }, [companyId]);

  useEffect(() => {
    if (companyId === undefined) return;
    let live = true;
    setLoadingSlots(true);
    setTime('');
    listSlots(companyId, day)
      .then((result) => {
        if (live) setSlots(result.slots);
      })
      .catch((caught: unknown) => {
        if (live) {
          setSlots([]);
          setError(caught instanceof ApiError ? caught.detail : 'Unable to load the times.');
        }
      })
      .finally(() => {
        if (live) setLoadingSlots(false);
      });
    return () => {
      live = false;
    };
  }, [companyId, day]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (companyId === undefined) return;
    if (time === '') {
      setError('Choose a time first.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const appointment = await bookAppointment({
        company_id: companyId,
        date: day,
        time,
        requirements,
      });
      setBooked(appointment);
    } catch (caught: unknown) {
      setError(caught instanceof ApiError ? caught.detail : 'Unable to book that time.');
    } finally {
      setSaving(false);
    }
  }

  if (booked !== null) {
    return (
      <div className="stack">
        <section className="card narrow">
          <h1>Consultation booked</h1>
          <p>
            {company?.name ?? 'The designer'} holds{' '}
            <strong>
              {new Date(`${booked.appointment_date}T00:00:00`).toLocaleDateString('en-SG', {
                weekday: 'long',
                day: 'numeric',
                month: 'long',
              })}{' '}
              at {booked.appointment_time}
            </strong>
            .
          </p>
          <p className="muted">
            The designer sees your booking and confirms it. You can cancel it from
            Appointments.
          </p>
          <div className="actions">
            <Link className="button" to="/appointments">
              View my appointments
            </Link>
            <Link className="button button-secondary" to="/designers">
              Back to designers
            </Link>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="stack">
      <p>
        <Link to={`/designers/${companyId ?? ''}`}>Back to the designer</Link>
      </p>

      <div className="page-head">
        <div>
          <h1>Book a consultation</h1>
          <p className="muted">
            {company === null ? 'One hour with the designer.' : `One hour with ${company.name}.`}
          </p>
        </div>
      </div>

      {error !== null && (
        <p className="alert alert-error" role="alert">
          {error}
        </p>
      )}

      <form className="card stack" onSubmit={submit}>
        <div className="field">
          <label htmlFor="appointment-day">Day</label>
          <select
            id="appointment-day"
            value={day}
            onChange={(event) => setDay(event.target.value)}
          >
            {days.map((entry) => (
              <option key={isoDay(entry)} value={isoDay(entry)}>
                {dayLabel(entry)}
              </option>
            ))}
          </select>
        </div>

        <div className="field">
          <span className="field-label">Time</span>
          {loadingSlots ? (
            <p className="muted">Loading times…</p>
          ) : slots.length === 0 ? (
            <p className="muted">No times are free on this day. Choose another day.</p>
          ) : (
            <div className="slot-grid" role="group" aria-label="Free times">
              {slots.map((slot) => (
                <button
                  key={slot}
                  type="button"
                  className="slot"
                  aria-pressed={time === slot}
                  onClick={() => setTime(slot)}
                >
                  {slot}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="field">
          <label htmlFor="appointment-requirements">What do you need? (optional)</label>
          <textarea
            id="appointment-requirements"
            rows={4}
            maxLength={1000}
            value={requirements}
            onChange={(event) => setRequirements(event.target.value)}
            placeholder="For example: two bedrooms, warm light, keep the existing sofa."
          />
        </div>

        <div className="actions">
          <button className="button" type="submit" disabled={saving || time === ''}>
            {saving ? 'Booking…' : 'Book this time'}
          </button>
        </div>
      </form>
    </div>
  );
}
