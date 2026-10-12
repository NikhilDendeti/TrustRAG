import { useEffect, useState } from 'react'
import { api, ApiError, type AuditEvent, type VerifyResult } from '../api'
import {
  AlertIcon,
  CheckCircleIcon,
  ChatIcon,
  DocIcon,
  KeyIcon,
  LockCheckIcon,
  XCircleIcon,
  type IconComponent,
} from '../components/icons'
import { Banner, Button, Card, Spinner } from '../components/ui'

type Tone = 'success' | 'warning' | 'danger' | 'info' | 'neutral'

const TONE_CLASSES: Record<Tone, { icon: string; chip: string }> = {
  success: { icon: 'bg-success-bg text-success', chip: 'bg-success-bg text-success' },
  warning: { icon: 'bg-warning-bg text-warning', chip: 'bg-warning-bg text-warning' },
  danger: { icon: 'bg-danger-bg text-danger', chip: 'bg-danger-bg text-danger' },
  info: { icon: 'bg-info-bg text-info', chip: 'bg-info-bg text-info' },
  neutral: { icon: 'bg-surface-2 text-text-muted', chip: 'bg-surface-2 text-text-muted' },
}

const EVENT_META: Record<string, { icon: IconComponent; tone: Tone; label: string }> = {
  login: { icon: KeyIcon, tone: 'success', label: 'Signed in' },
  login_failed: { icon: XCircleIcon, tone: 'danger', label: 'Sign-in failed' },
  logout: { icon: KeyIcon, tone: 'neutral', label: 'Signed out' },
  query_submitted: { icon: ChatIcon, tone: 'info', label: 'Question submitted' },
  retrieval_completed: { icon: DocIcon, tone: 'success', label: 'Retrieval completed' },
  prompt_risk_detected: { icon: AlertIcon, tone: 'warning', label: 'Prompt risk detected' },
  unauthorized_chunk_rejected: { icon: LockCheckIcon, tone: 'danger', label: 'Unauthorized chunk rejected' },
  delegation_created: { icon: KeyIcon, tone: 'success', label: 'Delegation granted' },
  delegation_revoked: { icon: KeyIcon, tone: 'warning', label: 'Delegation revoked' },
  delegation_denied: { icon: XCircleIcon, tone: 'danger', label: 'Delegation denied' },
  audit_verification_run: { icon: CheckCircleIcon, tone: 'info', label: 'Audit chain verified' },
}

const DEFAULT_META = { icon: DocIcon, tone: 'neutral' as Tone, label: '' }

function eventMeta(type: string) {
  return EVENT_META[type] ?? { ...DEFAULT_META, label: prettify(type) }
}

function prettify(raw: string) {
  return raw.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase())
}

function formatTimestamp(iso: string) {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return { relative: iso, absolute: iso }
  const diffMs = Date.now() - date.getTime()
  const diffSec = Math.round(diffMs / 1000)
  let relative: string
  if (diffSec < 5) relative = 'just now'
  else if (diffSec < 60) relative = `${diffSec}s ago`
  else if (diffSec < 3600) relative = `${Math.round(diffSec / 60)}m ago`
  else if (diffSec < 86400) relative = `${Math.round(diffSec / 3600)}h ago`
  else relative = date.toLocaleDateString()
  const absolute = date.toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'medium',
  })
  return { relative, absolute }
}

function formatDetailValue(value: unknown): string {
  if (Array.isArray(value)) return value.join(', ')
  if (typeof value === 'boolean') return value ? 'yes' : 'no'
  return String(value)
}

export function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [verifyResult, setVerifyResult] = useState<VerifyResult | null>(null)
  const [verifying, setVerifying] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function loadEvents() {
    try {
      setEvents(await api.auditEvents())
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load events.')
    }
  }

  useEffect(() => {
    loadEvents()
  }, [])

  async function handleVerify() {
    setVerifying(true)
    setError(null)
    try {
      const result = await api.verifyAudit()
      setVerifyResult(result)
      await loadEvents()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Verification failed to run.')
    } finally {
      setVerifying(false)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold sm:text-3xl">Security Audit</h1>
      <p className="mt-1 text-sm text-text-muted">
        Every security-relevant event, hash-chained in order. Verify to recompute the chain.
      </p>

      <div className="mt-5">
        <Button onClick={handleVerify} disabled={verifying}>
          {verifying ? (
            <span className="flex items-center gap-2">
              <Spinner className="h-4 w-4" /> Verifying…
            </span>
          ) : (
            'Verify chain'
          )}
        </Button>
      </div>

      {error && (
        <div className="mt-4">
          <Banner tone="danger">{error}</Banner>
        </div>
      )}

      {verifyResult && (
        <div className="mt-4">
          {verifyResult.valid ? (
            <Banner tone="success">
              <span className="flex items-center gap-2">
                <CheckCircleIcon className="h-4 w-4 shrink-0" />
                Chain verified ({verifyResult.checked_count} events checked)
              </span>
            </Banner>
          ) : (
            <Banner tone="danger">
              <span className="flex items-start gap-2">
                <XCircleIcon className="mt-0.5 h-4 w-4 shrink-0" />
                <span>
                  Integrity verification failed — first invalid sequence:{' '}
                  {verifyResult.first_invalid_sequence}. Reason: {verifyResult.reason}
                </span>
              </span>
            </Banner>
          )}
        </div>
      )}

      <h2 className="mb-3 mt-8 text-lg font-semibold">Recent events</h2>

      {events.length === 0 && !error && <p className="text-sm text-text-muted">No events yet.</p>}

      <ol className="relative">
        {events.map((e, i) => {
          const meta = eventMeta(e.event_type)
          const Icon = meta.icon
          const tone = TONE_CLASSES[meta.tone]
          const { relative, absolute } = formatTimestamp(e.timestamp)
          const details = Object.entries(e.details ?? {})
          const isLast = i === events.length - 1

          return (
            <li key={e.sequence} className="relative flex gap-4 pb-6">
              {!isLast && <span className="absolute left-[15px] top-8 h-[calc(100%-1.25rem)] w-px bg-border" />}

              <span className={`relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${tone.icon}`}>
                <Icon className="h-4 w-4" />
              </span>

              <Card className="flex-1 py-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="font-semibold">{meta.label}</p>
                    <p className="text-xs text-text-muted">
                      {e.actor_id} · <span title={absolute}>{relative}</span>
                    </p>
                  </div>
                  <span className="rounded bg-surface-2 px-1.5 py-0.5 font-mono text-[11px] text-text-muted">
                    #{e.sequence}
                  </span>
                </div>

                {details.length > 0 && (
                  <div className="mt-2.5 flex flex-wrap gap-1.5">
                    {details.map(([key, value]) => (
                      <span
                        key={key}
                        className={`rounded px-2 py-0.5 text-[11px] font-medium ${tone.chip}`}
                      >
                        {prettify(key)}: {formatDetailValue(value)}
                      </span>
                    ))}
                  </div>
                )}
              </Card>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
