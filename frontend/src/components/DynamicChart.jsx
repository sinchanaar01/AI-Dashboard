import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

const COLORS = ['#818cf8', '#34d399', '#fbbf24', '#fb7185', '#38bdf8', '#c084fc']
const axisStyle = { fill: '#94a3b8', fontSize: 11 }
const tooltipStyle = {
  backgroundColor: '#0f172a',
  border: '1px solid rgba(255,255,255,0.12)',
  borderRadius: 12,
  color: '#e2e8f0',
}

export default function DynamicChart({ chart }) {
  if (!chart?.data?.length || !chart?.y_keys?.length) {
    return <p className="mt-3 text-sm text-slate-400">No chart data is available.</p>
  }
  const { type, title, x_key: xKey, y_keys: yKeys, data } = chart

  return (
    <div className="mt-3 rounded-xl border border-white/10 bg-white/[0.03] p-3 sm:p-4">
      {title && <h4 className="mb-3 text-sm font-medium text-slate-200">{title}</h4>}
      <ResponsiveContainer width="100%" height={260}>
        {type === 'pie' ? (
          <PieChart>
            <Pie data={data} dataKey={yKeys[0]} nameKey={xKey} innerRadius={48} outerRadius={90} paddingAngle={3}>
              {data.map((row, index) => <Cell key={`${row[xKey]}-${index}`} fill={COLORS[index % COLORS.length]} />)}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ color: '#cbd5e1', fontSize: 12 }} />
          </PieChart>
        ) : type === 'bar' ? (
          <BarChart data={data}>
            <XAxis dataKey={xKey} tick={axisStyle} axisLine={false} tickLine={false} />
            <YAxis tick={axisStyle} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={tooltipStyle} />
            {yKeys.map((key, index) => <Bar key={key} dataKey={key} fill={COLORS[index % COLORS.length]} radius={[5, 5, 0, 0]} />)}
          </BarChart>
        ) : type === 'area' ? (
          <AreaChart data={data}>
            <XAxis dataKey={xKey} tick={axisStyle} axisLine={false} tickLine={false} />
            <YAxis tick={axisStyle} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={tooltipStyle} />
            {yKeys.map((key, index) => <Area key={key} dataKey={key} type="monotone" stroke={COLORS[index % COLORS.length]} fill={COLORS[index % COLORS.length]} fillOpacity={0.2} />)}
          </AreaChart>
        ) : (
          <LineChart data={data}>
            <XAxis dataKey={xKey} tick={axisStyle} axisLine={false} tickLine={false} />
            <YAxis tick={axisStyle} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ color: '#cbd5e1', fontSize: 12 }} />
            {yKeys.map((key, index) => <Line key={key} dataKey={key} type="monotone" stroke={COLORS[index % COLORS.length]} strokeWidth={2} dot={false} />)}
          </LineChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}