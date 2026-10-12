import { useEffect, useState } from 'react'
import { api, ApiError, type DocumentSummary } from '../api'
import { Badge, Banner, Card, Spinner } from '../components/ui'

export function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .documents()
      .then(setDocuments)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Failed to load documents.'))
  }, [])

  return (
    <div>
      <h1 className="text-2xl font-bold sm:text-3xl">Document Access</h1>
      <p className="mt-1 text-sm text-text-muted">
        Showing only documents visible to the signed-in user.
      </p>

      <div className="mt-6">
        {error && <Banner tone="danger">{error}</Banner>}

        {!documents && !error && (
          <div className="flex items-center gap-2 text-text-muted">
            <Spinner className="h-4 w-4" /> Loading…
          </div>
        )}

        {documents && documents.length === 0 && (
          <Banner tone="info">No documents are currently accessible to this user.</Banner>
        )}

        {documents && documents.length > 0 && (
          <div className="grid gap-3 sm:grid-cols-2">
            {documents.map((doc) => (
              <Card key={doc.document_id}>
                <h2 className="font-semibold">{doc.title}</h2>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-text-muted">
                  <Badge tone={classificationTone(doc.classification)}>{doc.classification}</Badge>
                  <span>Owner: {doc.owner_id}</span>
                </div>
                {doc.allowed_roles && (
                  <p className="mt-2 text-xs text-text-muted">
                    Allowed roles: {doc.allowed_roles.join(', ') || '—'}
                  </p>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function classificationTone(classification: string): 'success' | 'warning' | 'danger' | 'neutral' {
  if (classification === 'public') return 'success'
  if (classification === 'confidential') return 'danger'
  if (classification === 'restricted') return 'warning'
  return 'neutral'
}
