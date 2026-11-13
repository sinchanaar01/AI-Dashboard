import { useEffect, useState } from 'react'
import ForecastChart from '../components/ForecastChart'
import AiInsightsCard from '../components/AiInsightsCard'
import GlassCard from '../components/GlassCard'
import { apiRequest } from '../lib/api'

const metricLabels = [
  ['mae', 'MAE'],
  ['rmse', 'RMSE'],
  ['mape', 'MAPE (%)'],
]

export default function Predictions() {
  const [comparison, setComparison] = useState(null)
  const [error, setError] = useState('')
  const [horizon, setHorizon] = useState(3)

  useEffect(() => {
    let active = true
    apiRequest('/api/model-metrics')
      .then((data) => { if (active) setComparison(data) })
      .catch((requestError) => { if (active) setError(requestError.message) })
    return () => { active = false }
  }, [])

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <header>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-100 sm:text-3xl">Revenue predictions</h1>
            <p className="mt-1 text-sm text-slate-400">Rolling-origin model evaluation and a configurable forecast.</p>
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-300">
            Forecast horizon
            <select
              value={horizon}
              onChange={(event) => setHorizon(Number(event.target.value))}
              className="rounded-lg border border-white/10 bg-slate-900 px-3 py-2 text-slate-100 outline-none focus:border-indigo-400/40"
            >
              {Array.from({ length: 6 }, (_, index) => index + 1).map((month) => (
                <option key={month} value={month}>{month} {month === 1 ? 'month' : 'months'}</option>
              ))}
            </select>
          </label>
        </div>
      </header>
      <div className="grid gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]">
        <ForecastChart horizon={horizon} />
        <AiInsightsCard />
      </div>
      <GlassCard>
        <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold text-slate-100">Model comparison</h2>
            <p className="mt-1 text-xs text-slate-400">Lower error is better · evaluated on chronological rolling origins</p>
          </div>
          {comparison && <span className="text-xs text-emerald-300">Selected: {comparison.selectedModel}</span>}
        </div>
        {error ? (
          <p role="alert" className="text-sm text-rose-200">{error}</p>
        ) : !comparison ? (
          <p role="status" className="text-sm text-slate-400">Loading model metrics…</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-slate-500">
                <tr><th className="py-3 pr-4">Model</th>{metricLabels.map(([, label]) => <th key={label} className="px-4 py-3 text-right">{label}</th>)}<th className="px-4 py-3 text-right">Origins</th></tr>
              </thead>
              <tbody>
                {comparison.metrics.map((row) => (
                  <tr key={row.model} className={`border-t border-white/5 ${row.selected ? 'bg-emerald-400/[0.06] text-emerald-100' : 'text-slate-300'}`}>
                    <td className="py-3 pr-4 font-medium">{row.model}{row.selected && <span className="ml-2 text-xs text-emerald-300">Best MAE</span>}</td>
                    {metricLabels.map(([key]) => <td key={key} className="px-4 py-3 text-right tabular-nums">{row[key].toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>)}
                    <td className="px-4 py-3 text-right tabular-nums">{row.backtestPoints}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>
    </div>
  )
}