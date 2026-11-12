import { Link, Navigate, NavLink, Route, Routes } from 'react-router-dom';
import { useAuth } from './auth';
import ProtectedRoute from './components/ProtectedRoute';
import Admin from './pages/Admin';
import Appointments from './pages/Appointments';
import BookConsultation from './pages/BookConsultation';
import Dashboard from './pages/Dashboard';
import DesignerDetail from './pages/DesignerDetail';
import Designers from './pages/Designers';
import Home from './pages/Home';
import Login from './pages/Login';
import ProjectDetail from './pages/ProjectDetail';
import Platform from './pages/Platform';
import QuoteDetail from './pages/QuoteDetail';
import Quotes from './pages/Quotes';
import RequestQuote from './pages/RequestQuote';
import Saved from './pages/Saved';
import Register from './pages/Register';
import Search from './pages/Search';
import ProjectEditor from './pages/ProjectEditor';
import MyProjects from './pages/MyProjects';
import Profile from './pages/Profile';

export default function App() {
  const { account, loading, logout } = useAuth();

  return (
    <div className="shell">
      <header className="site-header">
        <div className="container header-inner">
          <Link className="brand" to="/">
            Interior Design Platform
          </Link>
          <nav className="nav" aria-label="Main">
            <NavLink to="/" end>
              Home
            </NavLink>
            {account !== null && (
              <>
                <NavLink to="/dashboard">Dashboard</NavLink>
                <NavLink to="/search">Find a project</NavLink>
                <NavLink to="/designers">Designers</NavLink>
                {account.role === 'CUSTOMER' && <NavLink to="/saved">Saved</NavLink>}
                {(account.role === 'CUSTOMER' || account.role === 'DESIGNER') && (
                  <NavLink to="/quotes">
                    {account.role === 'DESIGNER' ? 'Quote inbox' : 'Requests'}
                  </NavLink>
                )}
                {(account.role === 'CUSTOMER' || account.role === 'DESIGNER') && (
                  <NavLink to="/appointments">
                    {account.role === 'DESIGNER' ? 'Consultations' : 'Appointments'}
                  </NavLink>
                )}
                {account.role === 'DESIGNER' && (
                  <>
                  <NavLink to="/profile">Company profile</NavLink>
                  <NavLink to="/projects/new">Create Project</NavLink>
                  <NavLink to="/projects">My Projects</NavLink>
                  </>
                )}
                {account.role === 'ADMIN' && <NavLink to="/admin">Admin</NavLink>}
                {account.role === 'ADMIN' && <NavLink to="/platform">Platform</NavLink>}
                <span className="nav-account">{account.display_name}</span>
                <button type="button" className="link-button" onClick={logout}>
                  Sign out
                </button>
              </>
            )}
            {account === null && !loading && (
              <>
                <NavLink to="/login">Sign in</NavLink>
                <NavLink to="/register">Create account</NavLink>
              </>
            )}
          </nav>
        </div>
      </header>

      <main className="container main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/search"
            element={
              <ProtectedRoute>
                <Search />
              </ProtectedRoute>
            }
          />
          <Route
            path="/designers"
            element={
              <ProtectedRoute>
                <Designers />
              </ProtectedRoute>
            }
          />
          <Route
            path="/designers/:companyId"
            element={
              <ProtectedRoute>
                <DesignerDetail />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute roles={['DESIGNER']}>
                <Profile />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute roles={['ADMIN']}>
                <Admin />
              </ProtectedRoute>
            }
          />
          <Route
            path="/projects/new"
            element={
              <ProtectedRoute roles={['DESIGNER']}>
                <ProjectEditor />
              </ProtectedRoute>
            }
          />
          <Route
            path="/projects/:projectId/edit"
            element={
              <ProtectedRoute roles={['DESIGNER']}>
                <ProjectEditor />
              </ProtectedRoute>
            }
          />
          <Route
            path="/projects/:projectId"
            element={
              <ProtectedRoute>
                <ProjectDetail />
              </ProtectedRoute>
            }
          />
          <Route
            path="/saved"
            element={
              <ProtectedRoute roles={['CUSTOMER']}>
                <Saved />
              </ProtectedRoute>
            }
          />
          <Route
            path="/projects"
            element={
              <ProtectedRoute roles={['DESIGNER']}>
                <MyProjects />
              </ProtectedRoute>
            }
          />
          <Route
            path="/designers/:companyId/book"
            element={
              <ProtectedRoute roles={['CUSTOMER']}>
                <BookConsultation />
              </ProtectedRoute>
            }
          />
          <Route
            path="/appointments"
            element={
              <ProtectedRoute roles={['CUSTOMER', 'DESIGNER']}>
                <Appointments />
              </ProtectedRoute>
            }
          />
          <Route
            path="/quotes/new/:companyId"
            element={
              <ProtectedRoute roles={['CUSTOMER']}>
                <RequestQuote />
              </ProtectedRoute>
            }
          />
          <Route
            path="/quotes/:requestId"
            element={
              <ProtectedRoute>
                <QuoteDetail />
              </ProtectedRoute>
            }
          />
          <Route
            path="/quotes"
            element={
              <ProtectedRoute>
                <Quotes />
              </ProtectedRoute>
            }
          />
          <Route
            path="/platform"
            element={
              <ProtectedRoute roles={['ADMIN', 'PLATFORM_MANAGER']}>
                <Platform />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      <footer className="site-footer">
        <div className="container">CSIT314 software engineering project</div>
      </footer>
    </div>
  );
}