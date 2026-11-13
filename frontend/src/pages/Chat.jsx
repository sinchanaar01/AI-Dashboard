import { useEffect, useRef, useState } from 'react'
import { Bot, Download, Send, Sparkles, User } from 'lucide-react'
import DynamicChart from '../components/DynamicChart'
import GlassCard from '../components/GlassCard'
import { apiRequest } from '../lib/api'

const starters = [
  'Top 5 products by revenue',
  'Revenue trend by region',
  'Revenue by category',
  'Top 5 regions by revenue',
  'Monthly revenue in 2018',
  'Total units sold by product',
]

function downloadRowsCsv(rows, filename) {
  if (!rows?.length) return
  const columns = Object.keys(rows[0])
  const escapeCell = (value) => {
    let text = String(value ?? '')
    if (/^[=+\-@\t\r]/.test(text)) text = `'${text}`
    return `"${text.replaceAll('"', '""')}"`
  }
  const csv = [
    columns.map(escapeCell).join(','),
    ...rows.map((row) => columns.map((column) => escapeCell(row[column])).join(',')),
  ].join('\r\n')
  const url = URL.createObjectURL(new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = `${filename.replace(/[^a-z0-9-_]+/gi, '-').toLowerCase() || 'sales-result'}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

export default function Chat() {
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const endOfMessages = useRef(null)

  useEffect(() => {
    endOfMessages.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, sending])

  async function sendMessage(text = draft) {
    const message = text.trim()
    if (!message || sending) return

    const previousMessages = messages
    setMessages((current) => [...current, { role: 'user', message }])
    setDraft('')
    setSending(true)
    setError('')
    try {
      const response = await apiRequest('/api/chat', {
        method: 'POST',
        body: JSON.stringify({
          message,
          history: previousMessages.slice(-6).map(({ role, message: content }) => ({ role, content })),
        }),
      })
      setMessages((current) => [...current, { role: 'assistant', ...response }])
    } catch (requestError) {
      setError(requestError.message)
      setMessages((current) => [
        ...current,
        { role: 'assistant', message: requestError.message, response_type: 'text', rows: [] },
      ])
    } finally {
      setSending(false)
    }
  }

  function handleSubmit(event) {
    event.preventDefault()
    sendMessage()
  }

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-5xl flex-col gap-5">
      <header>
        <h1 className="text-2xl font-bold text-slate-100 sm:text-3xl">Chat with your sales data</h1>
        <p className="mt-1 text-sm text-slate-400">Ask questions about products, revenue, regions, and time trends.</p>
      </header>
      <GlassCard className="flex min-h-[60vh] flex-1 flex-col p-0">
        <div className="flex-1 space-y-5 overflow-y-auto p-4 sm:p-6" aria-live="polite">
          {!messages.length && (
            <div className="flex min-h-[42vh] flex-col items-center justify-center text-center">
              <span className="mb-4 rounded-2xl bg-indigo-400/10 p-4 text-indigo-300"><Sparkles className="h-7 w-7" /></span>
              <h2 className="text-lg font-semibold text-slate-100">Explore your sales data</h2>
              <p className="mt-2 max-w-md text-sm text-slate-400">Ask a question to get a concise answer and, when useful, a chart backed by the dataset.</p>
              <div className="mt-5 flex flex-wrap justify-center gap-2">
                {starters.map((question) => (
                  <button
                    key={question}
                    type="button"
                    onClick={() => sendMessage(question)}
                    disabled={sending}
                    className="rounded-full border border-white/10 bg-white/[0.03] px-4 py-2 text-xs text-slate-300 transition hover:border-indigo-400/30 hover:text-indigo-200 disabled:opacity-50"
                  >
                    {question}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((item, index) => (
            <div key={`${item.role}-${index}`} className={`flex gap-3 ${item.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <span className={`mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${item.role === 'user' ? 'bg-indigo-400/15 text-indigo-200' : 'bg-emerald-400/10 text-emerald-200'}`}>
                {item.role === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
              </span>
              <div className={`min-w-0 max-w-[90%] rounded-2xl px-4 py-3 sm:max-w-[82%] ${item.role === 'user' ? 'bg-indigo-500/15 text-indigo-50' : 'border border-white/5 bg-white/[0.03] text-slate-200'}`}>
                <p className="whitespace-pre-wrap text-sm leading-relaxed">{item.message}</p>
                {item.response_type === 'chart' && item.chart && <DynamicChart chart={item.chart} />}
                {item.response_type === 'table' && item.rows?.length > 0 && (
                  <div className="mt-3">
                    <button
                      type="button"
                      onClick={() => downloadRowsCsv(item.rows, `sales-chat-result-${index + 1}`)}
                      className="mb-2 inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-slate-300 hover:bg-white/5"
                    >
                      <Download className="h-3.5 w-3.5" /> Download CSV
                    </button>
                    <div className="max-w-full overflow-x-auto rounded-lg border border-white/10">
                      <table className="w-full min-w-max text-left text-xs">
                        <thead className="bg-white/[0.04] text-slate-400">
                          <tr>{Object.keys(item.rows[0]).map((key) => <th key={key} className="px-3 py-2 font-medium">{key}</th>)}</tr>
                        </thead>
                        <tbody>{item.rows.map((row, rowIndex) => (
                          <tr key={rowIndex} className="border-t border-white/5">
                            {Object.values(row).map((value, valueIndex) => <td key={valueIndex} className="px-3 py-2 text-slate-300">{typeof value === 'number' ? value.toLocaleString() : value}</td>)}
                          </tr>
                        ))}</tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}
          {sending && (
            <div className="flex items-center gap-3 text-sm text-slate-400" role="status">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-400/10 text-emerald-200"><Bot className="h-4 w-4" /></span>
              <span className="animate-pulse">Analyzing your data…</span>
            </div>
          )}
          <div ref={endOfMessages} />
        </div>
        <form onSubmit={handleSubmit} className="border-t border-white/10 p-3 sm:p-4">
          {error && <p className="mb-2 text-xs text-rose-300" role="alert">{error}</p>}
          <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-slate-950/60 p-2 focus-within:border-indigo-400/40">
            <input
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Ask a question about sales…"
              maxLength={500}
              aria-label="Ask about sales data"
              className="min-w-0 flex-1 bg-transparent px-2 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-500"
            />
            <button type="submit" disabled={!draft.trim() || sending} aria-label="Send message" className="rounded-lg bg-indigo-500 p-2.5 text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-40">
              <Send className="h-4 w-4" />
            </button>
          </div>
          <p className="mt-2 px-1 text-[11px] text-slate-500">Answers are calculated from the available sales data; unsupported questions are declined.</p>
        </form>
      </GlassCard>
    </div>
  )
}
