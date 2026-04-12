import { useState } from 'react'
import {
    ComposedChart, Line, Area, Bar, BarChart,
    XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, ReferenceLine, Legend,
} from 'recharts'
import { useFetch } from '../hooks/useFetch'
import { forecast as forecastApi } from '../api'
import { LoadingTiles, ErrorCard, SectionHeader, fmt } from '../components/UI'

const COLORS = {
    actual: '#3b82f6',
    predicted: '#f59e0b',
    band: '#fef3c7',
    green: '#22c55e',
    red: '#ef4444',
    teal: '#14b8a6',
    gray: '#94a3b8',
}

function TrendBadge({ direction }) {
    const config = {
        up: { label: 'Trending up', bg: '#dcfce7', text: '#15803d', arrow: '↑' },
        down: { label: 'Trending down', bg: '#fee2e2', text: '#b91c1c', arrow: '↓' },
        stable: { label: 'Stable', bg: '#f1f5f9', text: '#475569', arrow: '→' },
    }
    const c = config[direction] || config.stable
    return (
        <span style={{
            background: c.bg, color: c.text,
            padding: '3px 12px', borderRadius: 99,
            fontSize: 12, fontWeight: 600,
            display: 'inline-flex', alignItems: 'center', gap: 4,
        }}>
            {c.arrow} {c.label}
        </span>
    )
}

function CustomTooltip({ active, payload, label }) {
    if (!active || !payload?.length) return null
    const isActual = payload[0]?.payload?.is_actual
    return (
        <div style={{
            background: '#fff', border: '1px solid var(--border)',
            borderRadius: 8, padding: '10px 14px', fontSize: 12,
            boxShadow: '0 4px 12px rgba(0,0,0,0.08)', minWidth: 180,
        }}>
            <div style={{ fontWeight: 600, marginBottom: 6, color: 'var(--text-primary)' }}>
                {label}
                <span style={{
                    marginLeft: 8, fontSize: 10, fontWeight: 500,
                    color: isActual ? COLORS.actual : COLORS.predicted,
                }}>
                    {isActual ? 'actual' : 'forecast'}
                </span>
            </div>
            {payload.map((p, i) => {
                if (p.dataKey === 'band') return null
                return (
                    <div key={i} style={{ color: p.color || 'var(--text-primary)', marginTop: 2 }}>
                        {p.name}: ₹{Number(p.value).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                    </div>
                )
            })}
            {payload[0]?.payload?.yhat_lower && !isActual && (
                <div style={{ color: 'var(--text-muted)', marginTop: 4, fontSize: 11 }}>
                    Range: ₹{Number(payload[0].payload.yhat_lower).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                    {' – '}
                    ₹{Number(payload[0].payload.yhat_upper).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                </div>
            )}
        </div>
    )
}

function HolidayCard({ holiday }) {
    const isBoost = holiday.direction === 'boost'
    return (
        <div style={{
            background: isBoost ? '#f0fdf4' : '#fff5f5',
            border: `1px solid ${isBoost ? '#bbf7d0' : '#fecaca'}`,
            borderRadius: 10, padding: '12px 14px',
        }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>
                        {holiday.holiday}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                        {holiday.date}
                    </div>
                </div>
                <span style={{
                    background: isBoost ? '#dcfce7' : '#fee2e2',
                    color: isBoost ? '#15803d' : '#b91c1c',
                    padding: '2px 10px', borderRadius: 99,
                    fontSize: 11, fontWeight: 600,
                }}>
                    {isBoost ? '+' : ''}{(holiday.effect * 100).toFixed(1)}%
                </span>
            </div>
        </div>
    )
}

export default function ForecastingPage() {
    const [horizon, setHorizon] = useState(30)

    const { data, loading, error } = useFetch(
        () => forecastApi.dashboard(horizon), [horizon]
    )

    if (error) return (
        <div className="page-wrapper">
            <div className="page-title-row"><h1>Sales Forecasting</h1></div>
            <ErrorCard message={error} />
        </div>
    )

    const summary = data?.summary
    const weather = data?.weather_correlation || []
    const holidays = data?.holiday_effects || []

    // Build chart data — actuals solid, forecast dashed with band
    const chartData = (data?.forecast || []).map(p => ({
        date: p.date.slice(5),
        fullDate: p.date,
        is_actual: p.is_actual,
        revenue: p.is_actual ? p.yhat : null,
        forecast: !p.is_actual ? p.yhat : null,
        yhat: p.yhat,
        yhat_lower: p.yhat_lower,
        yhat_upper: p.yhat_upper,
        band: !p.is_actual ? [p.yhat_lower, p.yhat_upper] : null,
    }))

    // Find the split point for the reference line
    const splitIdx = chartData.findLastIndex(p => p.is_actual)
    const splitDate = chartData[splitIdx]?.date

    const weatherChart = weather.map(w => ({
        condition: w.condition.charAt(0).toUpperCase() + w.condition.slice(1),
        revenue: parseFloat(w.avg_revenue),
        orders: w.order_count,
    }))

    const dayLabels = {
        Monday: 'Mon', Tuesday: 'Tue', Wednesday: 'Wed',
        Thursday: 'Thu', Friday: 'Fri', Saturday: 'Sat', Sunday: 'Sun',
    }

    return (
        <div className="page-wrapper gap-16">
            {/* ── Header + horizon slider ── */}
            <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
                <div className="page-title-row" style={{ marginBottom: 0 }}>
                    <h1>Sales Forecasting</h1>
                    <p>Prophet model trained on 366 days of historical data</p>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, background: '#fff', border: '1px solid var(--border)', borderRadius: 10, padding: '10px 16px' }}>
                    <span style={{ fontSize: 12, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>Forecast horizon</span>
                    <input
                        type="range" min="7" max="90" step="1"
                        value={horizon}
                        onChange={e => setHorizon(Number(e.target.value))}
                        style={{ width: 120 }}
                    />
                    <span style={{ fontSize: 13, fontWeight: 600, minWidth: 50 }}>
                        {horizon} days
                    </span>
                </div>
            </div>

            {loading && (
                <div style={{ background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 10, padding: '10px 16px', fontSize: 13, color: '#92400e' }}>
                    Training Prophet model on your data — this takes about 5 seconds…
                </div>
            )}

            {/* ── Summary tiles ── */}
            <div className="grid-4">
                {loading ? <LoadingTiles count={4} /> : summary ? (
                    <>
                        <div className="metric-tile" style={{ borderTop: '3px solid #f59e0b' }}>
                            <div className="label">Next 7 days</div>
                            <div className="value">{fmt(summary.predicted_next_7_days, 'currency')}</div>
                            <div className="sub">Predicted revenue</div>
                        </div>
                        <div className="metric-tile" style={{ borderTop: '3px solid #f59e0b' }}>
                            <div className="label">Next 30 days</div>
                            <div className="value">{fmt(summary.predicted_next_30_days, 'currency')}</div>
                            <div className="sub">Predicted revenue</div>
                        </div>
                        <div className="metric-tile" style={{ borderTop: '3px solid #8b5cf6' }}>
                            <div className="label">Avg daily forecast</div>
                            <div className="value">{fmt(summary.avg_daily_forecast, 'currency')}</div>
                            <div className="sub">Per day average</div>
                        </div>
                        <div className="metric-tile">
                            <div className="label">Trend direction</div>
                            <div style={{ marginTop: 6 }}>
                                <TrendBadge direction={summary.trend_direction} />
                            </div>
                            <div className="sub" style={{ marginTop: 6 }}>
                                Best: {dayLabels[summary.strongest_day] || summary.strongest_day} &nbsp;·&nbsp;
                                Worst: {dayLabels[summary.weakest_day] || summary.weakest_day}
                            </div>
                        </div>
                    </>
                ) : null}
            </div>

            {/* ── Main forecast chart ── */}
            <div className="card">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
                    <span className="section-title">Revenue forecast — actual vs predicted</span>
                    <div style={{ display: 'flex', gap: 16, fontSize: 12, color: 'var(--text-secondary)', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <div style={{ width: 20, height: 2, background: COLORS.actual, borderRadius: 1 }} />
                            Actual
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <div style={{ width: 20, height: 2, background: COLORS.predicted, borderRadius: 1, borderTop: '2px dashed #f59e0b' }} />
                            Forecast
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <div style={{ width: 20, height: 10, background: COLORS.band, borderRadius: 2 }} />
                            90% confidence
                        </div>
                    </div>
                </div>
                {loading
                    ? <div className="skeleton" style={{ height: 320 }} />
                    : (
                        <div className="chart-wrap-tall">
                            <ResponsiveContainer width="100%" height="100%">
                                <ComposedChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                    <XAxis
                                        dataKey="date" tick={{ fontSize: 10 }}
                                        interval={Math.floor(chartData.length / 10)}
                                    />
                                    <YAxis
                                        tick={{ fontSize: 11 }}
                                        tickFormatter={v => `₹${(v / 1000).toFixed(0)}k`}
                                    />
                                    <Tooltip content={<CustomTooltip />} />

                                    {/* Confidence band */}
                                    <Area
                                        dataKey="yhat_upper" stroke="none"
                                        fill={COLORS.band} fillOpacity={0.6}
                                        name="Upper bound" legendType="none"
                                    />
                                    <Area
                                        dataKey="yhat_lower" stroke="none"
                                        fill="#fff" fillOpacity={1}
                                        name="Lower bound" legendType="none"
                                    />

                                    {/* Actual line */}
                                    <Line
                                        type="monotone" dataKey="revenue" name="Actual"
                                        stroke={COLORS.actual} strokeWidth={2}
                                        dot={false} activeDot={{ r: 4 }}
                                        connectNulls={false}
                                    />

                                    {/* Forecast line */}
                                    <Line
                                        type="monotone" dataKey="forecast" name="Forecast"
                                        stroke={COLORS.predicted} strokeWidth={2}
                                        strokeDasharray="6 3"
                                        dot={false} activeDot={{ r: 4 }}
                                        connectNulls={false}
                                    />

                                    {/* Today divider */}
                                    {splitDate && (
                                        <ReferenceLine
                                            x={splitDate} stroke="#94a3b8"
                                            strokeDasharray="4 4" strokeWidth={1}
                                            label={{ value: 'Today', position: 'top', fontSize: 10, fill: '#94a3b8' }}
                                        />
                                    )}
                                </ComposedChart>
                            </ResponsiveContainer>
                        </div>
                    )
                }
            </div>

            {/* ── Holiday effects + Weather correlation ── */}
            <div className="grid-2">
                <div className="card">
                    <SectionHeader title="Holiday effects detected by Prophet">
                        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Revenue impact vs baseline</span>
                    </SectionHeader>
                    {loading
                        ? <div className="skeleton" style={{ height: 200 }} />
                        : holidays.length === 0
                            ? <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>No holiday effects detected.</p>
                            : (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                    {holidays.slice(0, 8).map((h, i) => (
                                        <HolidayCard key={i} holiday={h} />
                                    ))}
                                </div>
                            )
                    }
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    {/* Weather correlation */}
                    <div className="card">
                        <SectionHeader title="Revenue by weather condition" />
                        {loading
                            ? <div className="skeleton" style={{ height: 180 }} />
                            : (
                                <div style={{ height: 180 }}>
                                    <ResponsiveContainer width="100%" height="100%">
                                        <BarChart data={weatherChart} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
                                            <XAxis dataKey="condition" tick={{ fontSize: 12 }} />
                                            <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `₹${(v / 1000).toFixed(0)}k`} />
                                            <Tooltip formatter={v => [`₹${Number(v).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`, 'Avg revenue']} />
                                            <Bar dataKey="revenue" name="Avg revenue" radius={[4, 4, 0, 0]}>
                                                {weatherChart.map((w, i) => (
                                                    <rect key={i} fill={
                                                        w.condition === 'Sunny' ? '#fbbf24' :
                                                            w.condition === 'Cloudy' ? '#94a3b8' : '#3b82f6'
                                                    } />
                                                ))}
                                            </Bar>
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            )
                        }
                        {!loading && weather.length > 0 && (
                            <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
                                {weather.map((w, i) => (
                                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                                        <span style={{ color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{w.condition}</span>
                                        <span style={{ fontWeight: 500 }}>
                                            {fmt(w.avg_revenue, 'currency')} avg &nbsp;·&nbsp;
                                            <span style={{ color: 'var(--text-muted)' }}>{w.order_count.toLocaleString()} orders</span>
                                        </span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* Best / worst day tiles */}
                    {!loading && summary && (
                        <div className="grid-2">
                            <div className="card" style={{ textAlign: 'center', borderTop: '3px solid #22c55e' }}>
                                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>Strongest day</div>
                                <div style={{ fontFamily: 'var(--font-heading)', fontSize: 20, fontWeight: 600, color: '#15803d' }}>
                                    {dayLabels[summary.strongest_day] || summary.strongest_day}
                                </div>
                                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>highest avg revenue</div>
                            </div>
                            <div className="card" style={{ textAlign: 'center', borderTop: '3px solid #ef4444' }}>
                                <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>Weakest day</div>
                                <div style={{ fontFamily: 'var(--font-heading)', fontSize: 20, fontWeight: 600, color: '#b91c1c' }}>
                                    {dayLabels[summary.weakest_day] || summary.weakest_day}
                                </div>
                                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>lowest avg revenue</div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}