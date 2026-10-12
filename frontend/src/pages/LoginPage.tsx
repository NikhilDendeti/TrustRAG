import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../AuthContext'
import { ApiError } from '../api'
import { Banner, Button, TextInput } from '../components/ui'
import { ShieldIcon } from '../components/icons'

const DEMO_CREDENTIALS = [
  { username: 'alice_employee', password: 'alice123', role: 'employee' },
  { username: 'bob_manager', password: 'bob123', role: 'manager, employee' },
  { username: 'casey_admin', password: 'casey123', role: 'admin' },
]

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showCreds, setShowCreds] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(username.trim(), password)
      navigate('/assistant', { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Login failed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden bg-bg">
      {/* Cinematic background, Netflix-style: dark radial glow + vignette */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-[-10%] h-[700px] w-[1100px] -translate-x-1/2 rounded-full bg-accent/20 blur-[160px]" />
        <div className="absolute inset-0 bg-gradient-to-b from-black/10 via-bg/70 to-bg" />
      </div>

      <header className="relative z-10 px-6 py-5 sm:px-10">
        <Link to="/" className="inline-flex items-center gap-2">
          <ShieldIcon className="h-7 w-7 text-accent" />
          <span className="text-xl font-extrabold tracking-tight text-text">TrustRAG</span>
        </Link>
      </header>

      <main className="relative z-10 flex flex-1 items-center justify-center px-4 pb-16">
        <div className="w-full max-w-md rounded-2xl border border-border bg-surface/90 p-8 shadow-2xl backdrop-blur">
          <h1 className="text-3xl font-bold text-text">Sign In</h1>
          <p className="mt-1 text-sm text-text-muted">to your TrustRAG workspace</p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <TextInput
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Username"
              autoComplete="username"
              required
            />
            <TextInput
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              autoComplete="current-password"
              required
            />

            {error && <Banner tone="danger">{error}</Banner>}

            <Button type="submit" className="w-full py-3 text-base" disabled={submitting}>
              {submitting ? 'Signing in…' : 'Sign In'}
            </Button>
          </form>

          <div className="mt-6 border-t border-border pt-4">
            <button
              type="button"
              onClick={() => setShowCreds((v) => !v)}
              className="flex w-full items-center justify-between text-sm text-text-muted transition-colors hover:text-text"
            >
              Need a demo account?
              <span className={`transition-transform ${showCreds ? 'rotate-90' : ''}`}>›</span>
            </button>

            {showCreds && (
              <div className="mt-3 overflow-hidden rounded-lg border border-border">
                <table className="w-full text-left text-sm">
                  <thead className="bg-surface-2 text-text-muted">
                    <tr>
                      <th className="px-3 py-2 font-medium">Username</th>
                      <th className="px-3 py-2 font-medium">Password</th>
                      <th className="px-3 py-2 font-medium">Role</th>
                    </tr>
                  </thead>
                  <tbody>
                    {DEMO_CREDENTIALS.map((c) => (
                      <tr key={c.username} className="border-t border-border bg-bg/40">
                        <td className="px-3 py-2 font-mono text-xs text-text">{c.username}</td>
                        <td className="px-3 py-2 font-mono text-xs text-text">{c.password}</td>
                        <td className="px-3 py-2 text-text-muted">{c.role}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
