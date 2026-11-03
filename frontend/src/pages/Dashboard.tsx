import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import type { Role, Status } from '../types';

const ROLE_LABELS: Record<Role, string> = {
  CUSTOMER: 'Customer',
  DESIGNER: 'Interior designer',
  ADMIN: 'Administrator',
  PLATFORM_MANAGER: 'Platform manager',
};

const STATUS_LABELS: Record<Status, string> = {
  PENDING: 'Pending approval',
  ACTIVE: 'Active',
  SUSPENDED: 'Suspended',
};

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

export default function Dashboard() {
  const { account, logout } = useAuth();
  const navigate = useNavigate();

  if (account === null) {
    return null;
  }

  function handleLogout() {
    logout();
    navigate('/login', { replace: true });
  }

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <h1>Dashboard</h1>
          <p className="muted">Signed in as {account.email}</p>
        </div>
        <button type="button" className="button button-secondary" onClick={handleLogout}>
          Log out
        </button>
      </div>

      {account.status === 'PENDING' && (
        <p className="alert alert-notice" role="status">
          Your account is waiting for admin approval. Designer accounts become active once an
          administrator reviews them.
        </p>
      )}

      {account.status === 'SUSPENDED' && (
        <p className="alert alert-error" role="alert">
          This account is suspended. Contact the platform team if you think this is a mistake.
        </p>
      )}

      <section className="card" aria-labelledby="account-details">
        <h2 id="account-details">Account details</h2>
        <dl className="facts">
          <div>
            <dt>Display name</dt>
            <dd>{account.display_name}</dd>
          </div>
          <div>
            <dt>Email</dt>
            <dd>{account.email}</dd>
          </div>
          <div>
            <dt>Role</dt>
            <dd>{ROLE_LABELS[account.role]}</dd>
          </div>
          <div>
            <dt>Status</dt>
            <dd>
              <span className={`badge badge-${account.status.toLowerCase()}`}>
                {STATUS_LABELS[account.status]}
              </span>
            </dd>
          </div>
          <div>
            <dt>Account ID</dt>
            <dd className="mono">{account.id}</dd>
          </div>
          <div>
            <dt>Member since</dt>
            <dd>{formatDate(account.created_at)}</dd>
          </div>
        </dl>
      </section>
    </div>
  );
}