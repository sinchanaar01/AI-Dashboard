import { useEffect, useState } from 'react'
import { Area, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { apiRequest } from '../lib/api'
import GlassCard from './GlassCard'

const axisStyle = { fill: '#94a3b8', fontSize: 11 }
const tooltipStyle = {
  backgroundColor: '#0f172a',
  border: '1px solid rgba(255,255,255,0.12)',
  borderRadius: 12,
  color: '#e2e8f0',
}

export default function ForecastChart({ horizon }) {
  const [result, setResult] = useState({ horizon: null, forecast: null, error: '' })

  useEffect(() => {
    let active = true
    apiRequest(`/api/forecast?horizon=${horizon}`)
      .then((data) => { if (active) setResult({ horizon, forecast: data, error: '' }) })
      .catch((requestError) => { if (active) setResult({ horizon, forecast: null, error: requestError.message }) })
    return () => { active = false }
  }, [horizon])

  const loading = result.horizon !== horizon
  const error = loading ? '' : result.error
  const forecast = loading ? null : result.forecast
  const chartData = forecast
    ? [
        ...forecast.history.map((point, index) => ({
          ...point,
          forecast: index === forecast.history.length - 1 ? point.actual : null,
          ciLower: index === forecast.history.length - 1 ? point.actual : null,
          ciRange: 0,
        })),
        ...forecast.forecast.map((point) => ({
          ...point,
          actual: null,
          ciRange: point.ciUpper - point.ciLower,
        })),
      ]
    : []

  return (
    <GlassCard className="h-full min-h-[360px]">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">Revenue forecast</h2>
          <p className="mt-1 text-xs text-slate-400">Monthly history and {horizon}-month projection</p>
        </div>
        {forecast && <span className="rounded-full border border-indigo-400/20 bg-indigo-400/10 px-3 py-1 text-xs text-indigo-200">{forecast.model}</span>}
      </div>
      {error ? (
        <p role="alert" className="rounded-lg border border-rose-400/20 bg-rose-400/10 p-4 text-sm text-rose-200">{error}</p>
      ) : loading || !forecast ? (
        <div className="flex h-[280px] items-center justify-center text-sm text-slate-400" role="status">Loading forecast…</div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={chartData}>
            <XAxis dataKey="date" tick={axisStyle} axisLine={false} tickLine={false} minTickGap={20} />
            <YAxis tick={axisStyle} axisLine={false} tickLine={false} width={68} tickFormatter={(value) => `$${Math.round(value / 1000)}k`} />
            <Tooltip contentStyle={tooltipStyle} formatter={(value, name) => [typeof value === 'number' ? `$${value.toLocaleString()}` : value, name]} />
            <Area dataKey="ciLower" stackId="confidence" stroke="none" fill="transparent" isAnimationActive={false} />
            <Area dataKey="ciRange" stackId="confidence" stroke="none" fill="#818cf8" fillOpacity={0.16} name="Confidence interval" />
            <Line dataKey="actual" type="monotone" stroke="#34d399" strokeWidth={2.5} dot={false} name="Actual" connectNulls />
            <Line dataKey="forecast" type="monotone" stroke="#818cf8" strokeWidth={2.5} strokeDasharray="6 4" dot={{ r: 3 }} name="Forecast" connectNulls />
          </ComposedChart>
        </ResponsiveContainer>
      )}
    </GlassCard>
  )
}
