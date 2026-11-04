import { Link, Navigate, NavLink, Route, Routes } from 'react-router-dom';
import { useAuth } from './auth';
import ProtectedRoute from './components/ProtectedRoute';
import Admin from './pages/Admin';
import Dashboard from './pages/Dashboard';
import DesignerDetail from './pages/DesignerDetail';
import Designers from './pages/Designers';
import Home from './pages/Home';
import Login from './pages/Login';
import Profile from './pages/Profile';
import Register from './pages/Register';
import Search from './pages/Search';
import ProjectEditor from './pages/ProjectEditor';
import MyProjects from './pages/MyProjects';

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
                {account.role === 'DESIGNER' && (
                  <>
                  <NavLink to="/profile">Company profile</NavLink>
                  <NavLink to="/projects/new">Create Project</NavLink>
                  <NavLink to="/projects">My Projects</NavLink>
                  </>
                )}
                {account.role === 'ADMIN' && <NavLink to="/admin">Admin</NavLink>}
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
            path="/projects"
            element={
              <ProtectedRoute roles={['DESIGNER']}>
                <MyProjects />
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