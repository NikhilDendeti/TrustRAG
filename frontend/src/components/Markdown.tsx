import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

/**
 * Renders Gemma's markdown-formatted answer text (bold, lists, etc.) instead
 * of showing raw asterisks/hashes as plain text. Citation tags like
 * [doc:leave_policy#0] are wrapped in backticks beforehand so they render as
 * small accent-colored code chips instead of plain bracketed text.
 */
export function Markdown({ text }: { text: string }) {
  const withStyledCitations = text.replace(/(?<!`)(\[doc:[^\]]+\])(?!`)/g, '`$1`')

  return (
    <div className="prose-answer leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
          strong: ({ children }) => <strong className="font-semibold text-text">{children}</strong>,
          em: ({ children }) => <em className="italic">{children}</em>,
          ul: ({ children }) => <ul className="mb-3 ml-5 list-disc space-y-1 last:mb-0">{children}</ul>,
          ol: ({ children }) => <ol className="mb-3 ml-5 list-decimal space-y-1 last:mb-0">{children}</ol>,
          li: ({ children }) => <li className="pl-1">{children}</li>,
          h1: ({ children }) => <h3 className="mb-2 mt-4 text-base font-bold first:mt-0">{children}</h3>,
          h2: ({ children }) => <h3 className="mb-2 mt-4 text-base font-bold first:mt-0">{children}</h3>,
          h3: ({ children }) => <h4 className="mb-2 mt-3 text-sm font-bold first:mt-0">{children}</h4>,
          a: ({ children, href }) => (
            <a href={href} target="_blank" rel="noreferrer" className="text-accent underline underline-offset-2 hover:text-accent-hover">
              {children}
            </a>
          ),
          code: ({ children }) => (
            <code className="rounded bg-bg px-1.5 py-0.5 text-[0.85em] text-accent">{children}</code>
          ),
          blockquote: ({ children }) => (
            <blockquote className="mb-3 border-l-2 border-border pl-3 text-text-muted last:mb-0">
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div className="mb-3 overflow-x-auto last:mb-0">
              <table className="w-full border-collapse text-sm">{children}</table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border-b border-border px-2 py-1.5 text-left font-semibold">{children}</th>
          ),
          td: ({ children }) => <td className="border-b border-border px-2 py-1.5">{children}</td>,
          hr: () => <hr className="my-4 border-border" />,
        }}
      >
        {withStyledCitations}
      </ReactMarkdown>
    </div>
  )
}
