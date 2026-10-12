export interface AuthUser {
  user_id: string
  display_name: string
  roles: string[]
}

export interface MeResponse extends AuthUser {
  accessible_count: number
  total_count: number
}

export interface DocumentSummary {
  document_id: string
  title: string
  classification: string
  owner_id: string
  allowed_roles: string[] | null
}

export interface PromptFinding {
  rule_id: string
  title: string
  severity: 'low' | 'medium' | 'high'
  evidence: string
  explanation: string
}

export interface EvidenceChunk {
  source_id: string
  title: string
  classification: string
  text: string
}

export interface AnswerPayload {
  text: string
  citations: string[]
  abstained: boolean
  used_fallback: boolean
  thinking_level: 'minimal' | 'high' | null
}

export interface AskResponse {
  blocked: boolean
  findings: PromptFinding[]
  answer: AnswerPayload | null
  evidence: EvidenceChunk[]
}

export interface DelegationSummary {
  grant_id: string
  grantor_id: string
  grantee_id: string
  document_id: string
  document_title: string
  expires_at: string
  status: 'active' | 'expired' | 'revoked'
  can_revoke: boolean
}

export interface AuditEvent {
  sequence: number
  timestamp: string
  event_type: string
  actor_id: string
  details: Record<string, unknown>
}

export interface VerifyResult {
  valid: boolean
  checked_count: number
  first_invalid_sequence: number | null
  reason: string | null
}

const TOKEN_KEY = 'trustrag_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers = new Headers(options.headers)
  headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const res = await fetch(`/api${path}`, { ...options, headers })
  if (!res.ok) {
    let message = res.statusText
    try {
      const body = await res.json()
      message = body.detail ?? message
    } catch {
      // ignore — fall back to statusText
    }
    if (res.status === 401) setToken(null)
    throw new ApiError(res.status, message)
  }
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

export const api = {
  login: (username: string, password: string) =>
    request<{ token: string; user: AuthUser }>('/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request<{ ok: true }>('/logout', { method: 'POST' }),
  me: () => request<MeResponse>('/me'),
  documents: () => request<DocumentSummary[]>('/documents'),
  delegatableDocuments: () => request<{ document_id: string; title: string }[]>('/delegatable-documents'),
  users: () => request<{ user_id: string; display_name: string }[]>('/users'),
  ask: (question: string, thinkingLevel: 'minimal' | 'high') =>
    request<AskResponse>('/ask', {
      method: 'POST',
      body: JSON.stringify({ question, thinking_level: thinkingLevel }),
    }),
  delegations: () => request<DelegationSummary[]>('/delegations'),
  createDelegation: (payload: { grantee_id: string; document_id: string; expires_at: string; reason?: string }) =>
    request<{ grant_id: string }>('/delegations', { method: 'POST', body: JSON.stringify(payload) }),
  revokeDelegation: (grantId: string) =>
    request<{ ok: true }>(`/delegations/${grantId}/revoke`, { method: 'POST' }),
  auditEvents: () => request<AuditEvent[]>('/audit/events'),
  verifyAudit: () => request<VerifyResult>('/audit/verify', { method: 'POST' }),
}
