import { useEffect, useState, type FormEvent } from 'react'
import { useAuth } from '../AuthContext'
import { api, ApiError, type DelegationSummary } from '../api'
import { Badge, Banner, Button, Card, Select, TextInput } from '../components/ui'

function defaultExpiry(): string {
  const d = new Date(Date.now() + 60 * 60 * 1000)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function DelegationPage() {
  const { user, refresh } = useAuth()
  const [docs, setDocs] = useState<{ document_id: string; title: string }[]>([])
  const [peers, setPeers] = useState<{ user_id: string; display_name: string }[]>([])
  const [delegations, setDelegations] = useState<DelegationSummary[]>([])
  const [granteeId, setGranteeId] = useState('')
  const [documentId, setDocumentId] = useState('')
  const [expiresAt, setExpiresAt] = useState(defaultExpiry())
  const [reason, setReason] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function loadAll() {
    const [d, u, g] = await Promise.all([api.delegatableDocuments(), api.users(), api.delegations()])
    setDocs(d)
    setPeers(u)
    setDelegations(g)
    if (!granteeId && u.length > 0) setGranteeId(u[0].user_id)
    if (!documentId && d.length > 0) setDocumentId(d[0].document_id)
  }

  useEffect(() => {
    loadAll().catch((err) => setError(err instanceof ApiError ? err.message : 'Failed to load.'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSuccess(null)
    if (!docs.length) {
      setError('You have no document access to delegate.')
      return
    }
    setSubmitting(true)
    try {
      const res = await api.createDelegation({
        grantee_id: granteeId,
        document_id: documentId,
        expires_at: new Date(expiresAt).toISOString(),
        reason: reason || undefined,
      })
      setSuccess(`Grant ${res.grant_id} created.`)
      setReason('')
      await loadAll()
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to create delegation.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleRevoke(grantId: string) {
    setError(null)
    try {
      await api.revokeDelegation(grantId)
      await loadAll()
      await refresh()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to revoke.')
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold sm:text-3xl">Temporary Delegation</h1>
      <p className="mt-1 text-sm text-text-muted">
        Grant another user time-limited access to one document you can access.
      </p>

      <Card className="mt-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-sm font-medium">Grantee</label>
              <Select value={granteeId} onChange={(e) => setGranteeId(e.target.value)}>
                {peers.map((p) => (
                  <option key={p.user_id} value={p.user_id}>
                    {p.display_name}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium">Document</label>
              <Select value={documentId} onChange={(e) => setDocumentId(e.target.value)} disabled={!docs.length}>
                {docs.map((d) => (
                  <option key={d.document_id} value={d.document_id}>
                    {d.title}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium">Expires at</label>
            <TextInput
              type="datetime-local"
              value={expiresAt}
              onChange={(e) => setExpiresAt(e.target.value)}
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium">Reason (optional)</label>
            <TextInput value={reason} onChange={(e) => setReason(e.target.value)} />
          </div>

          {error && <Banner tone="danger">{error}</Banner>}
          {success && <Banner tone="success">{success}</Banner>}

          <Button type="submit" disabled={submitting || !docs.length}>
            {submitting ? 'Creating…' : 'Create grant'}
          </Button>
        </form>
      </Card>

      <h2 className="mb-3 mt-8 text-lg font-semibold">Existing grants</h2>
      <div className="space-y-2.5">
        {delegations.length === 0 && <p className="text-sm text-text-muted">No delegations yet.</p>}
        {delegations.map((d) => (
          <Card key={d.grant_id} className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0 text-sm">
              <p className="font-mono text-xs text-text-muted">{d.grant_id}</p>
              <p className="mt-1">
                <span className="font-medium">{d.grantor_id}</span> → <span className="font-medium">{d.grantee_id}</span>{' '}
                on <span className="italic">{d.document_title}</span>
              </p>
              <p className="mt-1 text-xs text-text-muted">expires {d.expires_at}</p>
            </div>
            <div className="flex items-center gap-2 self-start sm:self-auto">
              <Badge tone={statusTone(d.status)}>{d.status}</Badge>
              {d.can_revoke && (
                <Button variant="danger" onClick={() => handleRevoke(d.grant_id)}>
                  Revoke
                </Button>
              )}
            </div>
          </Card>
        ))}
      </div>

      {user && docs.length === 0 && (
        <div className="mt-4">
          <Banner tone="info">
            You have no document access of your own to delegate, so the form above can't submit
            yet.
          </Banner>
        </div>
      )}
    </div>
  )
}

function statusTone(status: string): 'success' | 'warning' | 'danger' {
  if (status === 'active') return 'success'
  if (status === 'expired') return 'warning'
  return 'danger'
}
