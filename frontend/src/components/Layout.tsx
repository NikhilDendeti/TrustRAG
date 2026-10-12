import { useState, type ReactNode } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../AuthContext'
import { ChatIcon, DocIcon, InfoIcon, KeyIcon, MenuIcon, ShieldIcon } from './icons'
import { Button } from './ui'

const NAV_ITEMS = [
  { to: '/assistant', label: 'Secure AI Assistant', icon: ChatIcon },
  { to: '/documents', label: 'Document Access', icon: DocIcon },
  { to: '/delegation', label: 'Temporary Delegation', icon: KeyIcon },
  { to: '/audit', label: 'Security Audit', icon: ShieldIcon },
  { to: '/about', label: 'About and Limitations', icon: InfoIcon },
]

export function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [drawerOpen, setDrawerOpen] = useState(false)

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="flex min-h-screen bg-bg text-text">
      {/* Desktop sidebar */}
      <aside className="hidden w-72 shrink-0 flex-col border-r border-border bg-surface p-5 md:flex">
        <SidebarContent user={user} onLogout={handleLogout} />
      </aside>

      {/* Mobile drawer */}
      {drawerOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setDrawerOpen(false)} />
          <aside className="absolute left-0 top-0 h-full w-72 max-w-[85vw] overflow-y-auto border-r border-border bg-surface p-5">
            <SidebarContent
              user={user}
              onLogout={handleLogout}
              onNavigate={() => setDrawerOpen(false)}
            />
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Mobile top bar */}
        <header className="flex items-center justify-between border-b border-border bg-surface px-4 py-3 md:hidden">
          <button
            onClick={() => setDrawerOpen(true)}
            className="rounded-lg p-2 text-text hover:bg-surface-2"
            aria-label="Open menu"
          >
            <MenuIcon className="h-5 w-5" />
          </button>
          <span className="text-sm font-semibold text-accent">TrustRAG</span>
          <div className="h-9 w-9" />
        </header>

        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6 lg:px-8">{children}</div>
        </main>
      </div>
    </div>
  )
}

function SidebarContent({
  user,
  onLogout,
  onNavigate,
}: {
  user: {
    display_name: string
    roles: string[]
    accessible_count: number
    total_count: number
    embedding_name: string
    embedding_fallback_reason: string | null
    indexed_chunk_count: number
  } | null
  onLogout: () => void
  onNavigate?: () => void
}) {
  return (
    <>
      <Link to="/" className="mb-1 flex items-center gap-2">
        <ShieldIcon className="h-6 w-6 text-accent" />
        <span className="text-lg font-bold">TrustRAG</span>
      </Link>
      <p className="mb-5 text-xs text-text-muted">Secure Enterprise AI — hackathon prototype</p>

      {user && (
        <div className="mb-5 rounded-lg border border-success/30 bg-success-bg px-3 py-2.5 text-sm">
          <p className="text-success">
            Signed in as <span className="font-semibold">{user.display_name}</span>
          </p>
          <p className="mt-1 text-xs text-text-muted">Role(s): {user.roles.join(', ')}</p>
          <p className="mt-1 text-xs text-text-muted">
            Accessible documents: {user.accessible_count} of {user.total_count}
          </p>
          <p className="mt-1 text-xs text-text-muted">
            Embedding: {user.embedding_name} · {user.indexed_chunk_count} chunks indexed
          </p>
          {user.embedding_fallback_reason && (
            <p className="mt-1 text-xs text-warning">
              Offline fallback embedding in use: {user.embedding_fallback_reason}
            </p>
          )}
        </div>
      )}

      <nav className="flex flex-1 flex-col gap-1">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            onClick={onNavigate}
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                isActive ? 'bg-accent/15 text-accent' : 'text-text-muted hover:bg-surface-2 hover:text-text'
              }`
            }
          >
            <Icon className="h-4 w-4 shrink-0" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-6">
        <Button variant="secondary" className="w-full" onClick={onLogout}>
          Log out
        </Button>
      </div>
    </>
  )
}
