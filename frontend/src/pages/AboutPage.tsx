import { Card } from '../components/ui'

export function AboutPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold sm:text-3xl">About TrustRAG</h1>

      <Card className="prose-content mt-6 space-y-4 text-sm leading-relaxed text-text">
        <p>
          TrustRAG is a hackathon prototype demonstrating secure,
          authorization-filtered retrieval-augmented generation. It is{' '}
          <strong>not</strong> a production-ready enterprise security system.
        </p>

        <Section title="Role-based access control (RBAC)">
          Every document carries explicit <code>allowed_roles</code> / <code>allowed_users</code>{' '}
          metadata. Access is decided centrally in <code>auth/permissions.py</code> before any
          retrieval happens.
        </Section>

        <Section title="Retrieval-augmented generation (RAG)">
          Questions are answered only from document chunks the current user is authorized to see.
          Every retrieved chunk is re-validated against the authorization service a second time
          before it can enter the model's context, even if it was returned by the vector search.
        </Section>

        <Section title="Prompt-injection scanning is heuristic">
          It flags common attack patterns (instruction overrides, hidden-prompt extraction,
          safeguard bypass attempts, restricted-document requests). The absence of a match does{' '}
          <strong>not</strong> mean a prompt is safe — this is a mitigation layer, not a
          guarantee.
        </Section>

        <Section title="Time-limited delegation">
          Lets a user who can already access a document grant another user scoped, expiring
          access to that one document. Expiry and revocation are enforced at query time, not only
          in the UI.
        </Section>

        <Section title="Hash-chained audit log">
          Every security-relevant event is appended with a SHA-256 hash over its canonical payload
          plus the previous event's hash. Verification recomputes the whole chain and detects any
          modification, deletion, or reordering of the stored events.
        </Section>

        <Section title="Honest limitation on the audit chain">
          This hash chain detects tampering with the <em>currently stored</em> log file. It is{' '}
          <strong>not</strong> immutable against an attacker who can rewrite the entire log and
          recompute every hash from scratch — that requires protected external storage, digital
          signatures, or trusted checkpoints, which are out of scope for this MVP.
        </Section>

        <Section title="When content is sent to the LLM provider">
          When a Gemma API key is configured, only the already-authorized, already-filtered chunk
          text and your question are sent to Google's Generative Language API to generate an
          answer. No other document content, and no document metadata beyond what's shown in the
          UI, is sent. If no key is configured, or the call fails, the app shows the raw
          authorized evidence instead of a generated answer, and never fabricates a citation.
        </Section>
      </Card>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h2 className="mb-1 font-semibold text-text">{title}</h2>
      <p className="text-text-muted">{children}</p>
    </div>
  )
}
