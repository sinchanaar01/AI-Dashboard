import { useEffect, useRef, useState } from 'react'
import { ArrowDownRight, ArrowUpRight, MapPin, Package, Wallet } from 'lucide-react'
import DynamicChart from '../components/DynamicChart'
import GlassCard from '../components/GlassCard'
import { apiRequest } from '../lib/api'

const currency = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })

function KpiCard({ label, value, icon: Icon, detail, positive }) {
  return (
    <GlassCard className="min-w-0">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm text-slate-400">{label}</p>
          <p className="mt-2 truncate text-xl font-semibold text-slate-100 sm:text-2xl">{value}</p>
          {detail && <p className={`mt-2 flex items-center gap-1 text-xs ${positive === false ? 'text-rose-300' : 'text-emerald-300'}`}>
            {positive === false ? <ArrowDownRight className="h-4 w-4" /> : <ArrowUpRight className="h-4 w-4" />}{detail}
          </p>}
        </div>
        <span className="rounded-xl bg-indigo-400/10 p-3 text-indigo-300"><Icon className="h-5 w-5" /></span>
      </div>
    </GlassCard>
  )
}

export default function Overview() {
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState('')
  const [uploadMessage, setUploadMessage] = useState('')
  const [uploadError, setUploadError] = useState('')
  const [uploading, setUploading] = useState(false)
  const fileInput = useRef(null)

  async function refreshSummary() {
    const data = await apiRequest('/api/summary')
    setSummary(data)
  }

  useEffect(() => {
    let active = true
    apiRequest('/api/summary')
      .then((data) => { if (active) setSummary(data) })
      .catch((requestError) => { if (active) setError(requestError.message) })
    return () => { active = false }
  }, [])

  async function handleUpload(event) {
    const file = event.target.files?.[0]
    if (!file) return
    setUploading(true)
    setUploadMessage('')
    setUploadError('')
    try {
      const body = new FormData()
      body.append('file', file)
      const result = await apiRequest('/api/upload', { method: 'POST', body })
      await refreshSummary()
      setUploadMessage(`${result.message} ${result.rows.toLocaleString()} rows loaded. The upload is temporary and resets when the backend restarts.`)
    } catch (requestError) {
      setUploadError(requestError.message)
    } finally {
      setUploading(false)
      event.target.value = ''
    }
  }

  async function handleReset() {
    setUploading(true)
    setUploadMessage('')
    setUploadError('')
    try {
      const result = await apiRequest('/api/upload/reset', { method: 'POST' })
      await refreshSummary()
      setUploadMessage(`${result.message} ${result.rows.toLocaleString()} rows loaded.`)
    } catch (requestError) {
      setUploadError(requestError.message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <header>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-100 sm:text-3xl">Sales overview</h1>
            <p className="mt-1 text-sm text-slate-400">A live view of sales performance across the full dataset.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <input ref={fileInput} type="file" accept=".csv,text/csv" className="hidden" onChange={handleUpload} aria-label="Upload sales CSV" />
            <button type="button" disabled={uploading} onClick={() => fileInput.current?.click()} className="rounded-lg border border-indigo-400/30 bg-indigo-400/10 px-4 py-2 text-sm text-indigo-200 hover:bg-indigo-400/20 disabled:opacity-50">
              {uploading ? 'Loading…' : 'Upload CSV'}
            </button>
            <button type="button" disabled={uploading} onClick={handleReset} className="rounded-lg border border-white/10 px-4 py-2 text-sm text-slate-300 hover:bg-white/5 disabled:opacity-50">
              Reset to default data
            </button>
          </div>
        </div>
        <p className="mt-3 text-xs text-slate-500">CSV must include Date, Product, Category, Region, Units, and Revenue. Maximum 20 MB; uploads are in-memory only.</p>
        {uploadMessage && <p role="status" className="mt-2 text-sm text-emerald-300">{uploadMessage}</p>}
        {uploadError && <p role="alert" className="mt-2 text-sm text-rose-300">{uploadError}</p>}
      </header>
      {error ? (
        <p role="alert" className="rounded-xl border border-rose-400/20 bg-rose-400/10 p-4 text-sm text-rose-200">{error}</p>
      ) : !summary ? (
        <p role="status" className="py-12 text-center text-sm text-slate-400">Loading sales summary…</p>
      ) : (
        <>
          <section className="grid gap-4 sm:grid-cols-2 2xl:grid-cols-5">
            <KpiCard label="Total revenue" value={currency.format(summary.totalRevenue)} icon={Wallet} />
            <KpiCard
              label="Year-over-year"
              value={summary.yoyGrowthPercent === null ? '—' : `${summary.yoyGrowthPercent.toFixed(1)}%`}
              icon={ArrowUpRight}
              detail={summary.yoyGrowthPercent === null ? 'requires 13 months of data' : 'vs. same month last year'}
              positive={summary.yoyGrowthPercent === null ? undefined : summary.yoyGrowthPercent >= 0}
            />
            <KpiCard label="Top sub-category" value={summary.topSubCategories[0]?.name ?? '—'} icon={Package} detail={currency.format(summary.topSubCategories[0]?.revenue ?? 0)} />
            <KpiCard label="Top region" value={summary.topRegions[0]?.name ?? '—'} icon={MapPin} detail={currency.format(summary.topRegions[0]?.revenue ?? 0)} />
            <KpiCard label="MoM (seasonal-sensitive)" value={`${summary.momGrowthPercent.toFixed(1)}%`} icon={ArrowUpRight} detail="vs. previous month" positive={summary.momGrowthPercent >= 0} />
          </section>
          <section className="grid gap-6 xl:grid-cols-[minmax(0,1.6fr)_minmax(320px,1fr)]">
            <GlassCard>
              <h2 className="text-lg font-semibold text-slate-100">Monthly revenue</h2>
              <DynamicChart chart={{ type: 'area', title: '', x_key: 'date', y_keys: ['revenue'], data: summary.monthlyRevenue }} />
            </GlassCard>
            <GlassCard>
              <h2 className="text-lg font-semibold text-slate-100">Revenue by category</h2>
              <DynamicChart chart={{ type: 'pie', title: '', x_key: 'category', y_keys: ['revenue'], data: summary.revenueByCategory }} />
            </GlassCard>
          </section>
          <GlassCard>
            <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
              <div>
                <h2 className="text-lg font-semibold text-slate-100">Unusual monthly revenue</h2>
                <p className="mt-1 text-xs text-slate-400">IQR outliers over the historical monthly series</p>
              </div>
              <span className="text-xs text-slate-500">{summary.anomalies.length} flagged periods</span>
            </div>
            {summary.anomalies.length ? (
              <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {summary.anomalies.map((item) => (
                  <li key={item.date} className="flex items-center justify-between gap-3 rounded-xl border border-white/5 bg-white/[0.03] p-4">
                    <div><p className="font-medium text-slate-200">{item.date}</p><p className="mt-1 text-xs capitalize text-slate-500">{item.kind} outlier</p></div>
                    <span className={`text-sm font-semibold tabular-nums ${item.kind === 'high' ? 'text-emerald-300' : 'text-amber-300'}`}>{currency.format(item.revenue)}</span>
                  </li>
                ))}
              </ul>
            ) : <p className="text-sm text-slate-400">No outliers were detected in the monthly revenue series.</p>}
          </GlassCard>
        </>
      )}
    </div>
  )
}
