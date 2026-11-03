import { Navigate, useLocation } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAuth } from '../auth';

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { account, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="page-state" role="status">
        Checking your session…
      </div>
    );
  }

  if (account === null) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <>{children}</>;
}