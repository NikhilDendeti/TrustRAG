import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './AuthContext'
import { Layout } from './components/Layout'
import { Spinner } from './components/ui'
import { AboutPage } from './pages/AboutPage'
import { AssistantPage } from './pages/AssistantPage'
import { AuditPage } from './pages/AuditPage'
import { DelegationPage } from './pages/DelegationPage'
import { DocumentsPage } from './pages/DocumentsPage'
import { LandingPage } from './pages/LandingPage'
import { LoginPage } from './pages/LoginPage'

function ProtectedRoutes() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg text-text-muted">
        <Spinner className="h-6 w-6" />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return (
    <Layout>
      <Routes>
        <Route path="/assistant" element={<AssistantPage />} />
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/delegation" element={<DelegationPage />} />
        <Route path="/audit" element={<AuditPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="*" element={<Navigate to="/assistant" replace />} />
      </Routes>
    </Layout>
  )
}

function RootRoutes() {
  const { user, loading } = useAuth()

  return (
    <Routes>
      <Route
        path="/"
        element={!loading && user ? <Navigate to="/assistant" replace /> : <LandingPage />}
      />
      <Route
        path="/login"
        element={!loading && user ? <Navigate to="/assistant" replace /> : <LoginPage />}
      />
      <Route path="/*" element={<ProtectedRoutes />} />
    </Routes>
  )
}

export default function App() {
  return (
    <Router>
      <AuthProvider>
        <RootRoutes />
      </AuthProvider>
    </Router>
  )
}
