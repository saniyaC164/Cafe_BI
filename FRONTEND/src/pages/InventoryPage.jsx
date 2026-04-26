import { useState, useMemo } from 'react'
import {
    BarChart, Bar, LineChart, Line,
    XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, Cell,
} from 'recharts'
import { useFetch } from '../hooks/useFetch'
import { inventory as invApi } from '../api'
import { ErrorCard, SectionHeader, fmt } from '../components/UI'

const STATUS_CONFIG = {
    ok: { bg: '#dcfce7', text: '#15803d', border: '#bbf7d0', label: 'OK' },
    low: { bg: '#fef3c7', text: '#92400e', border: '#fde68a', label: 'Low' },
    critical: { bg: '#fee2e2', text: '#b91c1c', border: '#fecaca', label: 'Critical' },
}
const URGENCY_CONFIG = {
    critical: { bg: '#fee2e2', text: '#b91c1c', label: 'Critical' },
    low: { bg: '#fef3c7', text: '#92400e', label: 'Low stock' },
    scheduled: { bg: '#dbeafe', text: '#1d4ed8', label: 'Scheduled' },
}
const DAY_ORDER = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

function StatusBadge({ status }) {
    const c = STATUS_CONFIG[status] || STATUS_CONFIG.ok
    return (
        <span style={{
            background: c.bg, color: c.text,
            padding: '2px 10px', borderRadius: 99,
            fontSize: 11, fontWeight: 600,
        }}>
            {c.label}
        </span>
    )
}

function UrgencyBadge({ urgency }) {
    const c = URGENCY_CONFIG[urgency] || URGENCY_CONFIG.scheduled
    return (
        <span style={{
            background: c.bg, color: c.text,
            padding: '2px 10px', borderRadius: 99,
            fontSize: 11, fontWeight: 600,
        }}>
            {c.label}
        </span>
    )
}

function StockBar({ current, reorder }) {
    const max = Math.max(current, reorder * 4, 1)
    const pct = Math.min((current / max) * 100, 100)
    const reoPct = Math.min((reorder / max) * 100, 100)
    const color = current <= 0 ? '#ef4444'
        : current < reorder ? '#ef4444'
            : current < reorder * 1.5 ? '#f59e0b'
                : '#22c55e'
    return (
        <div style={{ position: 'relative', background: '#f1f5f9', borderRadius: 99, height: 8, overflow: 'visible', flex: 1 }}>
            <div style={{
                width: `${pct}%`, height: '100%',
                background: color, borderRadius: 99, transition: 'width 0.4s ease',
            }} />
            <div style={{
                position: 'absolute', top: -3, left: `${reoPct}%`,
                width: 2, height: 14, background: '#94a3b8',
                transform: 'translateX(-50%)',
            }} title={`Reorder at ${reorder}`} />
        </div>
    )
}

function CustomTooltip({ active, payload, label }) {
    if (!active || !payload?.length) return null
    return (
        <div style={{
            background: '#fff', border: '1px solid var(--border)',
            borderRadius: 8, padding: '10px 14px', fontSize: 12,
            boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
        }}>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>{label}</div>
            {payload.map((p, i) => (
                <div key={i} style={{ color: p.color || 'var(--text-primary)' }}>
                    {p.name}: {typeof p.value === 'number' ? p.value.toFixed(2) : p.value}
                </div>
            ))}
        </div>
    )
}

export default function InventoryPage() {
    const [search, setSearch] = useState('')
    const [statusFilter, setStatusFilter] = useState('all')
    const [showReorder, setShowReorder] = useState(true)

    const { data, loading, error } = useFetch(
        () => invApi.dashboard(), []
    )

    const stock = data?.stock_status || []
    const depletion = data?.depletion_rates || []
    const reorders = data?.reorder_suggestions || []
    const wastage = data?.wastage_trend || []
    const byWeekday = data?.wastage_by_weekday || []
    const alertCount = data?.alert_count || 0

    const criticalCount = stock.filter(s => s.status === 'critical').length
    const lowCount = stock.filter(s => s.status === 'low').length

    const filteredStock = useMemo(() => {
        return stock.filter(s => {
            const matchSearch = s.name.toLowerCase().includes(search.toLowerCase())
            const matchStatus = statusFilter === 'all' || s.status === statusFilter
            return matchSearch && matchStatus
        })
    }, [stock, search, statusFilter])

    const depletionChart = depletion.slice(0, 10).map(d => ({
        name: d.name.length > 12 ? d.name.slice(0, 11) + '…' : d.name,
        usage: parseFloat(d.avg_daily_usage.toFixed(3)),
        days: d.days_remaining ? parseFloat(d.days_remaining.toFixed(1)) : null,
    }))

    const wastageChart = wastage.slice(-30).map(w => ({
        date: w.date.slice(5),
        events: w.total_wastage_events,
    }))

    const weekdayChart = DAY_ORDER.map(day => {
        const match = byWeekday.find(w => w.day_of_week === day)
        return {
            day,
            wastage: match ? parseFloat(match.total_wastage.toFixed(2)) : 0,
            events: match ? match.event_count : 0,
        }
    })

    if (error) return (
        <div className="page-wrapper">
            <div className="page-title-row"><h1>Inventory</h1></div>
            <ErrorCard message={error} />
        </div>
    )

    return (
        <div className="page-wrapper gap-16">
            {/* ── Header ── */}
            <div className="page-title-row">
                <h1>Inventory Management</h1>
                <p>Stock levels, depletion rates, wastage patterns and reorder alerts</p>
            </div>

            {/* ── Alert banner ── */}
            {!loading && alertCount > 0 && (
                <div style={{
                    background: criticalCount > 0 ? '#fff1f2' : '#fffbeb',
                    border: `1px solid ${criticalCount > 0 ? '#fecaca' : '#fde68a'}`,
                    borderRadius: 10, padding: '12px 18px',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                }}>
                    <div style={{ fontSize: 13, color: criticalCount > 0 ? '#b91c1c' : '#92400e', fontWeight: 500 }}>
                        {criticalCount > 0 && `⚠ ${criticalCount} ingredient${criticalCount > 1 ? 's' : ''} critically low.  `}
                        {lowCount > 0 && `${lowCount} ingredient${lowCount > 1 ? 's' : ''} approaching reorder level.`}
                    </div>
                    <button
                        onClick={() => setShowReorder(r => !r)}
                        style={{
                            background: 'transparent', border: '1px solid currentColor',
                            borderRadius: 6, padding: '4px 12px', fontSize: 12,
                            color: criticalCount > 0 ? '#b91c1c' : '#92400e', cursor: 'pointer',
                        }}
                    >
                        {showReorder ? 'Hide' : 'Show'} reorder panel
                    </button>
                </div>
            )}

            {/* ── Summary tiles ── */}
            <div className="grid-3">
                {loading ? (
                    [1, 2, 3].map(i => (
                        <div key={i} className="metric-tile">
                            <div className="skeleton" style={{ height: 12, width: '40%', marginBottom: 10 }} />
                            <div className="skeleton" style={{ height: 28, width: '50%' }} />
                        </div>
                    ))
                ) : (
                    <>
                        <div className="metric-tile" style={{ borderTop: '3px solid #3b82f6' }}>
                            <div className="label" style={{ color: 'black', fontWeight: 700 }}>Total ingredients</div>
                            <div className="value">{stock.length}</div>
                            <div className="sub">Tracked items</div>
                        </div>
                        <div className="metric-tile" style={{ borderTop: '3px solid #f59e0b' }}>
                            <div className="label" style={{ color: 'black', fontWeight: 700 }}>Need reorder</div>
                            <div className="value" style={{ color: alertCount > 0 ? '#b91c1c' : 'var(--text-primary)' }}>
                                {alertCount}
                            </div>
                            <div className="sub">{criticalCount} critical · {lowCount} low</div>
                        </div>
                        <div className="metric-tile" style={{ borderTop: '3px solid #22c55e' }}>
                            <div className="label" style={{ color: 'black', fontWeight: 700 }}>Reorder suggestions</div>
                            <div className="value">{reorders.length}</div>
                            <div className="sub">Items to action</div>
                        </div>
                    </>
                )}
            </div>

            {/* ── Reorder suggestions panel ── */}
            {showReorder && !loading && reorders.length > 0 && (
                <div className="card">
                    <SectionHeader title="Reorder suggestions">
                        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                            Suggested qty = 4× reorder level
                        </span>
                    </SectionHeader>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 10 }}>
                        {reorders.map((r, i) => (
                            <div key={i} style={{
                                background: '#fafafa', border: '1px solid var(--border)',
                                borderRadius: 10, padding: '12px 14px',
                                borderLeft: `3px solid ${r.urgency === 'critical' ? '#ef4444' : r.urgency === 'low' ? '#f59e0b' : '#3b82f6'}`,
                            }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                                    <div style={{ fontWeight: 600, fontSize: 13 }}>{r.name}</div>
                                    <UrgencyBadge urgency={r.urgency} />
                                </div>
                                <div style={{ fontSize: 12, color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: 3 }}>
                                    <span>Current: <strong>{r.current_stock} {r.unit}</strong></span>
                                    <span>Reorder at: {r.reorder_level} {r.unit}</span>
                                    <span>Order: <strong style={{ color: '#1d4ed8' }}>{r.suggested_order} {r.unit}</strong> from {r.supplier}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* ── Stock status table ── */}
            <div className="card">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14, flexWrap: 'wrap', gap: 10 }}>
                    <span className="section-title">Stock status</span>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                        <input
                            type="text" placeholder="Search ingredient…" value={search}
                            onChange={e => setSearch(e.target.value)}
                            style={{ padding: '5px 10px', borderRadius: 6, border: '1px solid var(--border)', fontSize: 12, width: 160 }}
                        />
                        <div style={{ display: 'flex', gap: 3 }}>
                            {['all', 'critical', 'low', 'ok'].map(s => (
                                <button key={s}
                                    onClick={() => setStatusFilter(s)}
                                    style={{
                                        padding: '4px 12px', borderRadius: 6,
                                        border: '1px solid var(--border)',
                                        background: statusFilter === s ? '#0f172a' : 'transparent',
                                        color: statusFilter === s ? '#fff' : 'var(--text-secondary)',
                                        fontSize: 11, fontWeight: 500, cursor: 'pointer',
                                        textTransform: 'capitalize',
                                    }}
                                >
                                    {s === 'all' ? 'All' : s}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                {loading
                    ? <div className="skeleton" style={{ height: 240 }} />
                    : (
                        <div style={{ overflowX: 'auto' }}>
                            <table className="data-table">
                                <thead>
                                    <tr>
                                        <th style={{ color: 'black' }}>Ingredient</th>
                                        <th style={{ color: 'black' }}>Unit</th>
                                        <th style={{ width: 180 }, { color: 'black' }}>Stock level</th>
                                        <th style={{ color: 'black' }}>Current</th>
                                        <th style={{ color: 'black' }}>Reorder at</th>
                                        <th style={{ color: 'black' }}>Days left</th>
                                        <th style={{ color: 'black' }}>Status</th>
                                        <th style={{ color: 'black' }}>Supplier</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredStock.map((s, i) => (
                                        <tr key={i}>
                                            <td style={{ fontWeight: 500 }}>{s.name}</td>
                                            <td style={{ color: 'var(--text-muted)' }}>{s.unit}</td>
                                            <td>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                                    <StockBar current={s.current_stock} reorder={s.reorder_level} />
                                                </div>
                                            </td>
                                            <td style={{ fontWeight: 500 }}>{s.current_stock}</td>
                                            <td style={{ color: 'var(--text-muted)' }}>{s.reorder_level}</td>
                                            <td style={{
                                                fontWeight: 500,
                                                color: s.days_until_empty <= 2 ? '#b91c1c'
                                                    : s.days_until_empty <= 5 ? '#92400e' : 'var(--text-primary)',
                                            }}>
                                                {s.days_until_empty != null ? `${s.days_until_empty}d` : '—'}
                                            </td>
                                            <td><StatusBadge status={s.status} /></td>
                                            <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{s.supplier}</td>
                                        </tr>
                                    ))}
                                    {filteredStock.length === 0 && (
                                        <tr>
                                            <td colSpan={8} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '24px 0' }}>
                                                No ingredients match your filter.
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    )
                }
            </div>

            {/* ── Depletion rates + Wastage by weekday ── */}
            <div className="grid-2">
                <div className="card">
                    <SectionHeader title="Depletion rates">
                        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Avg daily usage</span>
                    </SectionHeader>
                    {loading
                        ? <div className="skeleton" style={{ height: 240 }} />
                        : (
                            <div style={{ height: 240 }}>
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={depletionChart} layout="vertical" margin={{ left: 4, right: 16 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                                        <XAxis type="number" tick={{ fontSize: 10, color: 'black' }} />
                                        <YAxis type="category" dataKey="name" tick={{ fontSize: 11, color: 'black' }} width={80} />
                                        <Tooltip content={<CustomTooltip />} />
                                        <Bar dataKey="usage" name="Daily usage" fill="#14b8a6" radius={[0, 4, 4, 0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        )
                    }
                </div>

                <div className="card">
                    <SectionHeader title="Wastage by day of week">
                        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Monday spike expected</span>
                    </SectionHeader>
                    {loading
                        ? <div className="skeleton" style={{ height: 240 }} />
                        : (
                            <div style={{ height: 240 }}>
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={weekdayChart} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                                        <XAxis dataKey="day" tick={{ fontSize: 12 }} />
                                        <YAxis tick={{ fontSize: 11 }} />
                                        <Tooltip content={<CustomTooltip />} />
                                        <Bar dataKey="wastage" name="Total wastage" radius={[4, 4, 0, 0]}>
                                            {weekdayChart.map((w, i) => (
                                                <Cell
                                                    key={i}
                                                    fill={w.day === 'Mon' ? '#ef4444' : '#f97316'}
                                                    opacity={w.day === 'Mon' ? 1 : 0.6}
                                                />
                                            ))}
                                        </Bar>
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        )
                    }
                </div>
            </div>

            {/* ── Wastage trend ── */}
            <div className="card">
                <SectionHeader title="Wastage trend — last 30 days">
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Number of wastage events per day</span>
                </SectionHeader>
                {loading
                    ? <div className="skeleton" style={{ height: 200 }} />
                    : (
                        <div style={{ height: 200 }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={wastageChart} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                    <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                                    <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                                    <Tooltip content={<CustomTooltip />} />
                                    <Line
                                        type="monotone" dataKey="events" name="Wastage events"
                                        stroke="#f97316" strokeWidth={2}
                                        dot={false} activeDot={{ r: 4 }}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    )
                }
            </div>
        </div>
    )
}