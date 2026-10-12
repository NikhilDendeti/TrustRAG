import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertIcon,
  ArrowRightIcon,
  BrainIcon,
  ChainIcon,
  CheckCircleIcon,
  GithubIcon,
  KeyIcon,
  LockCheckIcon,
  PlusIcon,
  ShieldIcon,
  SparkleIcon,
} from '../components/icons'

const STATS = [
  { value: '3', label: 'Roles enforced' },
  { value: '7', label: 'Synthetic documents' },
  { value: '2×', label: 'Independent ACL checks' },
  { value: '46', label: 'Passing security tests' },
]

const FEATURES = [
  {
    icon: LockCheckIcon,
    eyebrow: 'Security before generation',
    title: 'Authorization happens before the model ever sees a word.',
    body: 'Every question is scoped to documents you’re actually allowed to read — twice. Once before the vector search runs, and again on every single chunk that comes back, independent of the first check. Unauthorized content never enters the prompt, even if a bug widens the first filter.',
    visual: <AuthVisual />,
  },
  {
    icon: BrainIcon,
    eyebrow: 'Powered by Gemma 4',
    title: 'Grounded answers, with a reasoning mode you can actually see.',
    body: 'Answers cite the exact source passage they came from — citations are validated against what was really retrieved, so nothing gets fabricated. Flip on Reasoning Mode to trade latency for Gemma 4’s deeper multi-step thinking on harder, cross-document questions.',
    visual: <ReasoningVisual />,
  },
  {
    icon: ChainIcon,
    eyebrow: 'Tamper-evident by design',
    title: 'Every security event, hash-chained and verifiable.',
    body: 'Logins, denials, delegations, and verification runs are appended to a SHA-256 hash chain. One click recomputes the entire chain and tells you exactly which event broke it — no silent tampering.',
    visual: <AuditVisual />,
  },
  {
    icon: KeyIcon,
    eyebrow: 'Least privilege, on a timer',
    title: 'Grant access for an hour. Not forever.',
    body: 'A manager can hand an employee temporary access to one specific document — never more than they themselves can access — and it expires automatically. Revoke it early and the door closes immediately, server-side.',
    visual: <DelegationVisual />,
  },
]

const FAQS = [
  {
    q: 'Is the sign-in on this demo a real production login?',
    a: 'No. It checks your username and password against a small hardcoded demo credential set (SHA-256 hashed, no salt) — enough to give the demo a real login flow instead of a bare identity dropdown, but it is not a production identity system. See the 3 demo accounts on the sign-in page.',
  },
  {
    q: 'What happens if no Gemma API key is configured?',
    a: 'The app still runs. Authorization, retrieval, prompt scanning, delegation, and audit logging all work fully offline. Without a key, the Assistant shows the raw authorized evidence instead of a generated answer — it never fabricates one.',
  },
  {
    q: 'What actually gets sent to Gemma?',
    a: 'Only the chunks that already passed both authorization checks, plus your question. No other document content and no metadata beyond what’s shown in the UI ever leaves the app.',
  },
  {
    q: 'Can I trust the hash-chained audit log completely?',
    a: 'It detects tampering with the log as currently stored — any edited, deleted, or reordered event breaks verification. It is not immune to someone rewriting the entire log file and recomputing every hash from scratch; production would need external WORM storage or signatures.',
  },
]

export function LandingPage() {
  return (
    <div className="bg-bg text-text">
      <Nav />
      <Hero />
      <Stats />
      <Features />
      <Quote />
      <Faq />
      <FinalCta />
      <Footer />
    </div>
  )
}

function Nav() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    function onScroll() {
      setScrolled(window.scrollY > 24)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <header
      className={`fixed inset-x-0 top-0 z-30 px-6 py-4 transition-colors duration-300 sm:px-10 ${
        scrolled ? 'border-b border-white/10 bg-bg' : 'border-b border-transparent bg-gradient-to-b from-black/85 to-transparent'
      }`}
    >
      <div className="mx-auto flex max-w-7xl items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <ShieldIcon className="h-7 w-7 text-accent" />
          <span className="text-xl font-extrabold tracking-tight">TrustRAG</span>
        </Link>
        <Link
          to="/login"
          className="rounded px-4 py-1.5 text-sm font-semibold text-white transition-colors bg-accent hover:bg-accent-hover"
        >
          Sign In
        </Link>
      </div>
    </header>
  )
}

function Hero() {
  return (
    <section className="relative flex min-h-[92vh] items-center overflow-hidden px-6 sm:px-10">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-[-20%] h-[900px] w-[1400px] -translate-x-1/2 rounded-full bg-accent/25 blur-[180px]" />
        <HeroGrid />
        <div className="absolute inset-0 shadow-[inset_0_0_220px_60px_rgba(0,0,0,0.75)]" />
        <div className="absolute inset-x-0 bottom-0 h-64 bg-gradient-to-t from-bg to-transparent" />
      </div>

      <div className="animate-fade-up relative mx-auto max-w-4xl text-center">
        <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-accent">
          Hacktoberfest 2026 · Built with Gemma 4
        </p>
        <h1 className="text-4xl font-black leading-[1.05] tracking-tight sm:text-6xl lg:text-7xl">
          Ask anything.
          <br />
          See <span className="text-accent">only</span> what you're allowed to.
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-text-muted sm:text-xl">
          TrustRAG is a secure RAG assistant where authorization happens in application
          code, before Gemma 4 ever sees a document — never as a prompt instruction the
          model could be talked out of.
        </p>

        <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link
            to="/login"
            className="flex items-center gap-2 rounded px-8 py-3.5 text-base font-bold text-white shadow-lg shadow-accent/20 transition-all hover:scale-[1.02] bg-accent hover:bg-accent-hover"
          >
            Get Started <ArrowRightIcon className="h-5 w-5" />
          </Link>
          <a
            href="https://github.com/NikhilDendeti/TrustRAG"
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-2 rounded border border-border bg-surface/60 px-8 py-3.5 text-base font-semibold text-text backdrop-blur transition-colors hover:border-text-muted hover:bg-surface"
          >
            <GithubIcon className="h-5 w-5" /> View Source
          </a>
        </div>
      </div>
    </section>
  )
}

function HeroGrid() {
  return (
    <svg className="absolute inset-0 h-full w-full opacity-[0.07]" aria-hidden>
      <defs>
        <pattern id="grid" width="48" height="48" patternUnits="userSpaceOnUse">
          <path d="M 48 0 L 0 0 0 48" fill="none" stroke="currentColor" strokeWidth="1" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#grid)" />
    </svg>
  )
}

function Stats() {
  return (
    <section className="border-y border-border bg-surface/40 px-6 py-10 sm:px-10">
      <div className="mx-auto grid max-w-5xl grid-cols-2 gap-6 sm:grid-cols-4">
        {STATS.map((s) => (
          <div key={s.label} className="text-center">
            <p className="text-3xl font-extrabold text-accent sm:text-4xl">{s.value}</p>
            <p className="mt-1 text-xs text-text-muted sm:text-sm">{s.label}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

function Features() {
  return (
    <section className="px-6 py-24 sm:px-10">
      <div className="mx-auto max-w-6xl space-y-28">
        {FEATURES.map((f, i) => (
          <div
            key={f.title}
            className={`flex flex-col items-center gap-10 lg:gap-16 ${
              i % 2 === 1 ? 'lg:flex-row-reverse' : 'lg:flex-row'
            }`}
          >
            <div className="flex-1">
              <div className="mb-4 inline-flex items-center gap-2 text-accent">
                <f.icon className="h-5 w-5" />
                <span className="text-sm font-bold uppercase tracking-wider">{f.eyebrow}</span>
              </div>
              <h2 className="text-2xl font-bold leading-tight sm:text-3xl">{f.title}</h2>
              <p className="mt-4 text-base leading-relaxed text-text-muted">{f.body}</p>
            </div>
            <div className="w-full flex-1">{f.visual}</div>
          </div>
        ))}
      </div>
    </section>
  )
}

function VisualFrame({ children }: { children: React.ReactNode }) {
  return (
    <div className="group overflow-hidden rounded-xl border border-border bg-surface shadow-2xl shadow-black/50 transition-transform duration-300 hover:-translate-y-1">
      <div className="flex items-center gap-1.5 border-b border-border bg-surface-2 px-4 py-2.5">
        <span className="h-2.5 w-2.5 rounded-full bg-danger/70" />
        <span className="h-2.5 w-2.5 rounded-full bg-warning/70" />
        <span className="h-2.5 w-2.5 rounded-full bg-success/70" />
      </div>
      <div className="p-5 sm:p-6">{children}</div>
    </div>
  )
}

function AuthVisual() {
  return (
    <VisualFrame>
      <p className="mb-3 text-xs text-text-muted">alice_employee asks about the finance forecast</p>
      <div className="rounded-lg bg-surface-2 p-4">
        <p className="text-sm text-text-muted">
          I couldn't find supporting information in the documents you are authorized to access.
        </p>
      </div>
      <div className="mt-3 flex items-center gap-2 text-xs font-medium text-danger">
        <AlertIcon className="h-4 w-4 shrink-0" />
        finance_forecast.md rejected by second ACL check — never reached Gemma
      </div>
    </VisualFrame>
  )
}

function ReasoningVisual() {
  return (
    <VisualFrame>
      <div className="flex items-center gap-2 text-sm">
        <span className="relative inline-flex h-5 w-9 items-center rounded-full border border-accent bg-accent">
          <span className="absolute right-0.5 h-4 w-4 rounded-full bg-white" />
        </span>
        <span className="inline-flex items-center gap-1.5">
          <SparkleIcon className="h-4 w-4 text-accent" />
          Reasoning mode
        </span>
      </div>
      <p className="mt-4 text-sm leading-relaxed text-text">
        The Engineering department has an approved quarterly operating budget of{' '}
        <span className="font-semibold">INR 25,00,000</span>{' '}
        <code className="rounded bg-bg px-1.5 py-0.5 text-xs text-accent">
          [doc:department_budget#0]
        </code>
      </p>
      <p className="mt-3 flex items-center gap-1.5 text-xs text-text-muted">
        <SparkleIcon className="h-3.5 w-3.5 text-accent" />
        Answered with Gemma 4 reasoning mode (thinking_level="high")
      </p>
    </VisualFrame>
  )
}

function AuditVisual() {
  const rows = [
    { seq: 21, type: 'audit_verification_run' },
    { seq: 20, type: 'prompt_risk_detected' },
    { seq: 19, type: 'query_submitted' },
    { seq: 18, type: 'delegation_created' },
  ]
  return (
    <VisualFrame>
      <div className="mb-3 flex items-center gap-2 rounded-md bg-success-bg px-3 py-2 text-sm font-medium text-success">
        <CheckCircleIcon className="h-4 w-4 shrink-0" />
        Chain verified (21 events checked)
      </div>
      <div className="space-y-1.5 font-mono text-xs text-text-muted">
        {rows.map((r) => (
          <div key={r.seq} className="flex items-center justify-between rounded bg-surface-2 px-2.5 py-1.5">
            <span>
              #{r.seq} {r.type}
            </span>
            <CheckCircleIcon className="h-3.5 w-3.5 text-success" />
          </div>
        ))}
      </div>
    </VisualFrame>
  )
}

function DelegationVisual() {
  return (
    <VisualFrame>
      <p className="text-sm">
        <span className="font-semibold">bob_manager</span> → <span className="font-semibold">alice_employee</span>
      </p>
      <p className="mt-1 text-sm italic text-text-muted">on Engineering Department Budget</p>
      <div className="mt-4 flex items-center justify-between">
        <span className="inline-flex items-center rounded-full border border-success/30 bg-success-bg px-2.5 py-0.5 text-xs font-medium text-success">
          active
        </span>
        <span className="text-xs text-text-muted">expires in 58 min</span>
      </div>
    </VisualFrame>
  )
}

function Quote() {
  return (
    <section className="border-y border-border bg-surface/40 px-6 py-20 text-center sm:px-10">
      <p className="mx-auto max-w-3xl text-2xl font-semibold leading-snug sm:text-3xl">
        "Retrieved documents are <span className="text-accent">evidence to report on</span> —
        never instructions for the model to follow."
      </p>
      <p className="mt-4 text-sm text-text-muted">The core rule every line of TrustRAG's RAG pipeline enforces.</p>
    </section>
  )
}

function Faq() {
  const [openIndex, setOpenIndex] = useState<number | null>(0)
  return (
    <section className="px-6 py-24 sm:px-10">
      <div className="mx-auto max-w-3xl">
        <h2 className="mb-10 text-center text-3xl font-extrabold sm:text-4xl">Frequently Asked Questions</h2>
        <div className="space-y-2">
          {FAQS.map((item, i) => {
            const open = openIndex === i
            return (
              <div key={item.q} className="overflow-hidden rounded-lg bg-surface-2">
                <button
                  onClick={() => setOpenIndex(open ? null : i)}
                  className="flex w-full items-center justify-between px-6 py-4 text-left text-base font-medium sm:text-lg"
                >
                  {item.q}
                  <PlusIcon
                    className={`ml-4 h-5 w-5 shrink-0 text-text-muted transition-transform duration-200 ${
                      open ? 'rotate-45' : ''
                    }`}
                  />
                </button>
                {open && (
                  <div className="px-6 pb-5 text-sm leading-relaxed text-text-muted sm:text-base">{item.a}</div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </section>
  )
}

function FinalCta() {
  return (
    <section className="px-6 py-24 text-center sm:px-10">
      <h2 className="text-3xl font-extrabold sm:text-4xl">Ready to see secure RAG in action?</h2>
      <p className="mx-auto mt-3 max-w-xl text-text-muted">
        Sign in with one of the three demo accounts and try the golden path in under 3 minutes.
      </p>
      <Link
        to="/login"
        className="mt-8 inline-flex items-center gap-2 rounded px-8 py-3.5 text-base font-bold text-white shadow-lg shadow-accent/20 transition-all hover:scale-[1.02] bg-accent hover:bg-accent-hover"
      >
        Get Started <ArrowRightIcon className="h-5 w-5" />
      </Link>
    </section>
  )
}

function Footer() {
  return (
    <footer className="border-t border-border px-6 py-10 sm:px-10">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 text-sm text-text-muted sm:flex-row">
        <div className="flex items-center gap-2">
          <ShieldIcon className="h-5 w-5 text-accent" />
          <span className="font-semibold text-text">TrustRAG</span>
          <span>— hackathon prototype, MIT licensed.</span>
        </div>
        <div className="flex items-center gap-5">
          <a href="https://github.com/NikhilDendeti/TrustRAG" target="_blank" rel="noreferrer" className="hover:text-text">
            GitHub
          </a>
          <Link to="/login" className="hover:text-text">
            Sign In
          </Link>
        </div>
      </div>
    </footer>
  )
}
