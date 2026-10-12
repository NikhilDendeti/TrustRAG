import { useState, type FormEvent } from 'react'
import { api, ApiError, type AskResponse } from '../api'
import { ChevronDownIcon, InfoIcon, SparkleIcon } from '../components/icons'
import { Badge, Banner, Button, Card, Spinner, TextInput } from '../components/ui'

export function AssistantPage() {
  const [question, setQuestion] = useState('')
  const [reasoningMode, setReasoningMode] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<AskResponse | null>(null)
  const [evidenceOpen, setEvidenceOpen] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!question.trim()) {
      setError('Please enter a question before submitting.')
      return
    }
    setError(null)
    setLoading(true)
    setResult(null)
    try {
      const res = await api.ask(question, reasoningMode ? 'high' : 'minimal')
      setResult(res)
      setEvidenceOpen(false)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold sm:text-3xl">Secure AI Assistant</h1>
      <p className="mt-1 text-sm text-text-muted">
        Answers are grounded only in documents you are currently authorized to access.
      </p>

      <Card className="mt-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="question" className="mb-1.5 block text-sm font-medium">
              Ask a question about company documents
            </label>
            <TextInput
              id="question"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. How many days of annual leave does the policy provide?"
            />
          </div>

          <div className="flex items-center justify-between gap-3">
            <label className="flex w-fit cursor-pointer items-center gap-2.5 text-sm">
              <span className="relative inline-flex h-5 w-9 items-center">
                <input
                  type="checkbox"
                  checked={reasoningMode}
                  onChange={(e) => setReasoningMode(e.target.checked)}
                  className="peer sr-only"
                />
                <span className="absolute inset-0 rounded-full border border-border bg-surface-2 transition-colors peer-checked:border-accent peer-checked:bg-accent" />
                <span className="absolute left-0.5 h-4 w-4 rounded-full bg-text-muted transition-transform peer-checked:translate-x-4 peer-checked:bg-white" />
              </span>
              <span className="inline-flex items-center gap-1.5">
                <SparkleIcon className="h-4 w-4 text-accent" />
                Reasoning mode
              </span>
              <span
                className="text-text-muted"
                title='Uses Gemma 4 thinking_level="high" for multi-step reasoning on harder questions.'
              >
                <InfoIcon className="h-3.5 w-3.5" />
              </span>
            </label>

            <Button type="submit" disabled={loading}>
              {loading ? (
                <span className="flex items-center gap-2">
                  <Spinner className="h-4 w-4" /> Thinking…
                </span>
              ) : (
                'Ask'
              )}
            </Button>
          </div>
        </form>
      </Card>

      {error && (
        <div className="mt-5">
          <Banner tone="danger">{error}</Banner>
        </div>
      )}

      {result && (
        <div className="mt-6 space-y-3">
          {result.findings.map((f) => (
            <Banner key={f.rule_id} tone={f.severity === 'high' ? 'danger' : 'warning'}>
              <span className="font-semibold">
                [{f.rule_id}] {f.title}
              </span>{' '}
              — {f.explanation}
            </Banner>
          ))}

          {result.blocked && (
            <Banner tone="danger">
              This request was blocked before retrieval ran, due to the high-severity prompt
              finding above.
            </Banner>
          )}

          {!result.blocked && result.answer?.abstained && (
            <Banner tone="info">{result.answer.text}</Banner>
          )}

          {!result.blocked && result.answer && !result.answer.abstained && (
            <Card>
              {result.answer.used_fallback ? (
                <Banner tone="warning">{result.answer.text}</Banner>
              ) : (
                <>
                  <p className="whitespace-pre-wrap leading-relaxed">{result.answer.text}</p>
                  {result.answer.thinking_level === 'high' && (
                    <p className="mt-3 flex items-center gap-1.5 text-xs text-text-muted">
                      <SparkleIcon className="h-3.5 w-3.5 text-accent" />
                      Answered with Gemma 4 reasoning mode (thinking_level="high")
                    </p>
                  )}
                </>
              )}

              {result.evidence.length > 0 && (
                <div className="mt-4 border-t border-border pt-3">
                  <button
                    type="button"
                    onClick={() => setEvidenceOpen((v) => !v)}
                    className="flex items-center gap-1.5 text-sm font-medium text-accent"
                  >
                    <ChevronDownIcon
                      className={`h-4 w-4 transition-transform ${evidenceOpen ? 'rotate-180' : ''}`}
                    />
                    Source evidence
                  </button>

                  {evidenceOpen && (
                    <div className="mt-3 space-y-3">
                      {result.evidence.map((chunk) => (
                        <div key={chunk.source_id} className="rounded-lg bg-surface-2 p-3">
                          <div className="mb-1.5 flex flex-wrap items-center gap-2">
                            <code className="rounded bg-bg px-1.5 py-0.5 text-xs text-accent">
                              [{chunk.source_id}]
                            </code>
                            <span className="text-sm font-medium">{chunk.title}</span>
                            <Badge>{chunk.classification}</Badge>
                          </div>
                          <pre className="whitespace-pre-wrap font-sans text-sm text-text-muted">
                            {chunk.text}
                          </pre>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
