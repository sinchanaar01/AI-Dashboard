import { useEffect, useState } from 'react'
import { Sparkles, TrendingUp } from 'lucide-react'
import { apiRequest } from '../lib/api'
import GlassCard from './GlassCard'

const currency = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })

export default function AiInsightsCard() {
  const [insights, setInsights] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    apiRequest('/api/insights')
      .then((data) => { if (active) setInsights(data) })
      .catch((requestError) => { if (active) setError(requestError.message) })
    return () => { active = false }
  }, [])

  return (
    <GlassCard className="flex h-full flex-col">
      <div className="mb-4 flex items-center gap-2 text-indigo-300">
        <Sparkles className="h-5 w-5" />
        <h2 className="font-semibold text-slate-100">AI forecast insights</h2>
      </div>
      {error ? (
        <p role="alert" className="text-sm text-rose-200">{error}</p>
      ) : !insights ? (
        <p className="text-sm text-slate-400" role="status">Preparing insights…</p>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl bg-white/[0.04] p-3">
              <p className="text-xs text-slate-400">Latest month</p>
              <p className="mt-1 text-lg font-semibold text-slate-100">{currency.format(insights.metrics.latestMonthRevenue)}</p>
            </div>
            <div className="rounded-xl bg-white/[0.04] p-3">
              <p className="text-xs text-slate-400">Year-over-year</p>
              <p className={`mt-1 text-lg font-semibold ${insights.metrics.yoyGrowthPercent === null ? 'text-slate-300' : insights.metrics.yoyGrowthPercent >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>
                {insights.metrics.yoyGrowthPercent === null ? '—' : `${insights.metrics.yoyGrowthPercent.toFixed(1)}%`}
              </p>
            </div>
          </div>
          <p className="mt-4 text-sm leading-relaxed text-slate-300">{insights.narrative}</p>
          <div className="mt-auto pt-5">
            <div className="rounded-xl border border-indigo-400/20 bg-indigo-400/[0.07] p-4">
              <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-indigo-200">
                <TrendingUp className="h-4 w-4" /> Recommended action
              </div>
              <p className="text-sm text-slate-300">{insights.recommendation}</p>
              <p className="mt-2 text-xs text-slate-500">Model: {insights.metrics.selectedModel}</p>
            </div>
          </div>
        </>
      )}
    </GlassCard>
  )
}
