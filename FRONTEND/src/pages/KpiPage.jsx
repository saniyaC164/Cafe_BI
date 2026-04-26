import { useState } from 'react'
import {
    LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend,
    ResponsiveContainer
} from 'recharts'
import { useFetch } from '../hooks/useFetch'
import { kpi } from '../api'
import {
    MetricTile, LoadingTiles, LoadingCard,
    ErrorCard, SectionHeader, PeriodSelector, Badge, fmt
} from '../components/UI'

const COLORS = {
    blue: '#3b82f6',
    teal: '#14b8a6',
    coral: '#f97316',
    purple: '#8b5cf6',
    amber: '#f59e0b',
    green: '#22c55e',
}

const CHANNEL_COLORS = ['#3b82f6', '#14b8a6', '#f97316']
const PAYMENT_COLORS = ['#8b5cf6', '#3b82f6', '#14b8a6']

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const HOURS = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]

function HourlyHeatmap({ data }) {
    if (!data || data.length === 0) return null

    const grid = {}
    data.forEach(({ hour, day_of_week, order_count }) => {
        const key = `${day_of_week}-${hour}`
        grid[key] = order_count
    })

    const maxVal = Math.max(...Object.values(grid), 1)

    const getColor = (count) => {
        if (!count) return '#f8fafc'
        const intensity = count / maxVal
        if (intensity > 0.75) return '#1d4ed8'
        if (intensity > 0.50) return '#3b82f6'
        if (intensity > 0.25) return '#93c5fd'
        return '#dbeafe'
    }

    return (
        <div style={{ overflowX: 'auto' }}>
            <table style={{ borderCollapse: 'collapse', fontSize: 11, width: '100%' }}>
                <thead>
                    <tr>
                        <th style={{ padding: '4px 8px', color: 'var(--text-muted)', textAlign: 'left', fontWeight: 500 }}>Day</th>
                        {HOURS.map(h => (
                            <th key={h} style={{ padding: '4px 6px', color: 'var(--text-muted)', fontWeight: 500, textAlign: 'center' }}>
                                {h > 12 ? `${h - 12}p` : `${h}a`}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {DAYS.map(day => (
                        <tr key={day}>
                            <td style={{ padding: '4px 8px', color: 'var(--text-secondary)', fontWeight: 500, whiteSpace: 'nowrap' }}>{day}</td>
                            {HOURS.map(h => {
                                const count = grid[`${day}-${h}`] || 0
                                return (
                                    <td key={h} style={{ padding: '2px 3px' }}>
                                        <div
                                            title={`${day} ${h}:00 — ${count} orders`}
                                            style={{
                                                width: 28, height: 22,
                                                background: getColor(count),
                                                borderRadius: 4,
                                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                color: count / maxVal > 0.5 ? '#fff' : 'transparent',
                                                fontSize: 9, fontWeight: 600,
                                            }}
                                        >
                                            {count || ''}
                                        </div>
                                    </td>
                                )
                            })}
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}

function CustomTooltip({ active, payload, label, prefix = '', suffix = '' }) {
    if (!active || !payload?.length) return null
    return (
        <div style={{
            background: '#fff', border: '1px solid var(--border)',
            borderRadius: 8, padding: '10px 14px', fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
        }}>
            <div style={{ fontWeight: 600, marginBottom: 4, color: 'var(--text-primary)' }}>{label}</div>
            {payload.map((p, i) => (
                <div key={i} style={{ color: p.color, marginTop: 2 }}>
                    {p.name}: {prefix}{typeof p.value === 'number' ? p.value.toLocaleString('en-IN') : p.value}{suffix}
                </div>
            ))}
        </div>
    )
}

export default function KpiPage() {
    const [period, setPeriod] = useState('30d')

    const { data, loading, error } = useFetch(
        () => kpi.dashboard(period), [period]
    )

    if (error) return (
        <div className="page-wrapper">
            <div className="page-title-row"><h1>KPI Dashboard</h1></div>
            <ErrorCard message={error} />
        </div>
    )

    const summary = data?.summary
    const trend = data?.revenue_trend || []
    const items = data?.top_items || []
    const channels = data?.channel_split || []
    const heatmap = data?.hourly_heatmap || []
    const custStats = data?.customer_stats
    const payments = data?.payment_split || []

    const trendFormatted = trend.map(r => ({
        ...r,
        date: r.date.slice(5),
        revenue: parseFloat(r.revenue),
    }))

    const itemsFormatted = items.slice(0, 8).map(r => ({
        name: r.name.length > 14 ? r.name.slice(0, 13) + '…' : r.name,
        revenue: parseFloat(r.total_revenue),
        qty: r.total_qty,
    }))

    return (
        <div className="page-wrapper gap-16">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div className="page-title-row" style={{ marginBottom: 0 }}>
                    <h1>KPI Dashboard</h1>
                    <p>Key performance indicators across all orders</p>
                </div>
                <PeriodSelector value={period} onChange={setPeriod} />
            </div>

            {/* ── Metric tiles ── */}
            <div className="grid-4">
                {loading ? <LoadingTiles count={4} /> : summary ? (
                    <>
                        <MetricTile
                            label="Total revenue"
                            value={fmt(summary.total_revenue, 'currency')}
                            sub={`${fmt(summary.total_orders)} orders`}
                            accent={COLORS.blue}
                        />
                        <MetricTile
                            label="Avg order value"
                            value={fmt(summary.avg_order_value, 'currency')}
                            sub="Per transaction"
                            accent={COLORS.teal}
                        />
                        <MetricTile
                            label="Gross profit"
                            value={fmt(summary.gross_profit, 'currency')}
                            sub={`${fmt(summary.profit_margin_pct, 'pct')} margin`}
                            accent={COLORS.purple}
                        />
                        <MetricTile
                            label="Total orders"
                            value={fmt(summary.total_orders)}
                            sub="Transactions"
                            accent={COLORS.amber}
                        />
                    </>
                ) : null}
            </div>

            {/* ── Revenue trend ── */}
            <div className="card">
                <SectionHeader title="Daily revenue trend" />
                {loading
                    ? <div className="skeleton" style={{ height: 260 }} />
                    : (
                        <div className="chart-wrap-tall">
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={trendFormatted} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                    <XAxis dataKey="date" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                                    <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `₹${(v / 1000).toFixed(0)}k`} />
                                    <Tooltip content={<CustomTooltip prefix="₹" />} />
                                    <Line
                                        type="monotone" dataKey="revenue" name="Revenue"
                                        stroke={COLORS.blue} strokeWidth={2}
                                        dot={false} activeDot={{ r: 4 }}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    )
                }
            </div>

            {/* ── Top items + Channel split ── */}
            <div className="grid-2-1">
                <div className="card">
                    <SectionHeader title="Top items by revenue" />
                    {loading
                        ? <div className="skeleton" style={{ height: 260 }} />
                        : (
                            <div className="chart-wrap-tall">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={itemsFormatted} layout="vertical" margin={{ left: 8, right: 16 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                                        <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={v => `₹${v.toFixed(0)}`} />
                                        <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={90} />
                                        <Tooltip content={<CustomTooltip prefix="₹" />} />
                                        <Bar dataKey="revenue" name="Revenue" fill={COLORS.teal} radius={[0, 4, 4, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        )
                    }
                </div>

                <div className="card">
                    <SectionHeader title="Channel split" />
                    {loading
                        ? <div className="skeleton" style={{ height: 260 }} />
                        : (
                            <>
                                <div style={{ height: 200 }}>
                                    <ResponsiveContainer width="100%" height="100%">
                                        <PieChart>
                                            <Pie
                                                data={channels} dataKey="orders"
                                                nameKey="channel" cx="50%" cy="50%"
                                                innerRadius={55} outerRadius={85}
                                                paddingAngle={3}
                                            >
                                                {channels.map((_, i) => (
                                                    <Cell key={i} fill={CHANNEL_COLORS[i % CHANNEL_COLORS.length]} />
                                                ))}
                                            </Pie>
                                            <Tooltip formatter={(v, n) => [v.toLocaleString(), n]} />
                                        </PieChart>
                                    </ResponsiveContainer>
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
                                    {channels.map((c, i) => (
                                        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12 }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                                <div style={{ width: 10, height: 10, borderRadius: 2, background: CHANNEL_COLORS[i] }} />
                                                <span style={{ textTransform: 'capitalize' }}>{c.channel}</span>
                                            </div>
                                            <span style={{ fontWeight: 500 }}>{c.percentage}%</span>
                                        </div>
                                    ))}
                                </div>
                            </>
                        )
                    }
                </div>
            </div>

            {/* ── Hourly heatmap ── */}
            <div className="card">
                <SectionHeader title="Order heatmap — hour × day of week">
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: 11, color: 'black' }}>
                        <div style={{ width: 12, height: 12, background: '#dbeafe', borderRadius: 2 }} /> Low
                        <div style={{ width: 12, height: 12, background: '#3b82f6', borderRadius: 2 }} /> High
                    </div>
                </SectionHeader>
                {loading
                    ? <div className="skeleton" style={{ height: 160 }} />
                    : <HourlyHeatmap data={heatmap} />
                }
            </div>

            {/* ── Payment split + Customer stats ── */}
            <div className="grid-2">
                <div className="card">
                    <SectionHeader title="Payment methods" />
                    {loading
                        ? <div className="skeleton" style={{ height: 160 }} />
                        : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                                {payments.map((p, i) => (
                                    <div key={i}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                                            <span style={{ textTransform: 'uppercase', fontWeight: 500, color: 'var(--text-secondary)' }}>{p.method}</span>
                                            <span style={{ fontWeight: 600 }}>{p.percentage}% <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>({p.count.toLocaleString()})</span></span>
                                        </div>
                                        <div style={{ background: '#f1f5f9', borderRadius: 99, height: 7, overflow: 'hidden' }}>
                                            <div style={{
                                                width: `${p.percentage}%`, height: '100%',
                                                background: PAYMENT_COLORS[i % PAYMENT_COLORS.length],
                                                borderRadius: 99, transition: 'width 0.6s ease',
                                            }} />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )
                    }
                </div>

                <div className="card">
                    <SectionHeader title="Customer stats" />
                    {loading
                        ? <div className="skeleton" style={{ height: 160 }} />
                        : custStats ? (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                                <div style={{ display: 'flex', gap: 16 }}>
                                    <div>
                                        <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 2 }}>Active customers</div>
                                        <div style={{ fontFamily: 'var(--font-heading)', fontSize: 22, fontWeight: 600 }}>
                                            {custStats.total_customers.toLocaleString()}
                                        </div>
                                    </div>
                                    <div>
                                        <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 2 }}>Retention rate</div>
                                        <div style={{ fontFamily: 'var(--font-heading)', fontSize: 22, fontWeight: 600, color: COLORS.green }}>
                                            {custStats.retention_rate_pct}%
                                        </div>
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: 8 }}>
                                    {[
                                        { label: 'Regular', count: custStats.regular_count, color: COLORS.green },
                                        { label: 'Occasional', count: custStats.occasional_count, color: COLORS.blue },
                                        { label: 'New', count: custStats.new_count, color: COLORS.coral },
                                    ].map(s => (
                                        <div key={s.label} style={{
                                            flex: 1, padding: '10px 12px',
                                            background: '#f8fafc', borderRadius: 8,
                                            borderLeft: `3px solid ${s.color}`,
                                        }}>
                                            <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{s.label}</div>
                                            <div style={{ fontWeight: 600, fontSize: 15, marginTop: 2 }}>{s.count.toLocaleString()}</div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ) : null
                    }
                </div>
            </div>
        </div>
    )
}