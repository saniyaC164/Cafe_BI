import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { kpi, mba, inventory, sentiment } from '../api'
import { MetricTile, LoadingTiles, ErrorCard, fmt } from '../components/UI'

export default function Overview() {
    const [kpiData, setKpi] = useState(null)
    const [alerts, setAlerts] = useState([])
    const [bundles, setBundles] = useState([])
    const [sentData, setSent] = useState(null)
    const [revTrend, setTrend] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        Promise.all([
            kpi.summary('all'),
            inventory.reorderSuggestions(),
            mba.bundles(),
            sentiment.summary('all'),
            kpi.revenueTrend('7d'),
        ]).then(([k, inv, b, s, trend]) => {
            setKpi(k); setAlerts(inv); setBundles(b.slice(0, 3))
            setSent(s); setTrend(trend)
        }).catch(e => setError(e.message))
            .finally(() => setLoading(false))
    }, [])

    const criticalCount = alerts.filter(a => a.urgency === 'critical').length
    const lowCount = alerts.filter(a => a.urgency === 'low').length

    return (
        <div className="page-wrapper">
            <div className="page-title-row">
                <h1>Good morning ☕</h1>
                <p>Here's your cafe at a glance — updated live from your database</p>
            </div>

            {error && <div className="error-box" style={{ marginBottom: 20 }}>{error}</div>}

            {/* ── Inventory alert banner ── */}
            {!loading && alerts.length > 0 && (
                <div style={{
                    background: criticalCount > 0 ? '#fff1f2' : '#fffbeb',
                    border: `1px solid ${criticalCount > 0 ? '#fecaca' : '#fde68a'}`,
                    borderRadius: 10, padding: '12px 18px', marginBottom: 20,
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                }}>
                    <span style={{ fontSize: 13, color: criticalCount > 0 ? '#b91c1c' : '#92400e' }}>
                        {criticalCount > 0
                            ? `⚠ ${criticalCount} ingredient${criticalCount > 1 ? 's' : ''} critically low — reorder immediately`
                            : `${lowCount} ingredient${lowCount > 1 ? 's' : ''} approaching reorder level`}
                    </span>
                    <Link to="/inventory" style={{ fontSize: 12, color: '#3b82f6', textDecoration: 'none', fontWeight: 500 }}>
                        View inventory →
                    </Link>
                </div>
            )}

            {/* ── KPI tiles ── */}
            <div className="grid-4" style={{ marginBottom: 20 }}>
                {loading ? <LoadingTiles count={4} /> : kpiData ? (
                    <>
                        <MetricTile label="Total revenue" value={fmt(kpiData.total_revenue, 'currency')} sub="All time" accent="var(--blue)" />
                        <MetricTile label="Total orders" value={fmt(kpiData.total_orders)} sub="All time" accent="var(--teal)" />
                        <MetricTile label="Avg order value" value={fmt(kpiData.avg_order_value, 'currency')} sub="Per order" accent="var(--purple)" />
                        <MetricTile label="Profit margin" value={fmt(kpiData.profit_margin_pct, 'pct')} sub="Gross margin" accent="var(--accent)" />
                    </>
                ) : null}
            </div>

            <div className="grid-2" style={{ marginBottom: 20 }}>
                {/* ── 7-day sparkline ── */}
                <div className="card">
                    <div className="section-header">
                        <span className="section-title">Revenue — last 7 days</span>
                        <Link to="/kpi" style={{ fontSize: 12, color: 'var(--blue)', textDecoration: 'none' }}>Full dashboard →</Link>
                    </div>
                    {loading ? <div className="skeleton" style={{ height: 120 }} /> : (
                        <div style={{ overflowX: 'auto' }}>
                            <table className="data-table">
                                <thead><tr><th style={{ color: 'black', fontWeight: 700 }}>Date</th><th style={{ color: 'black', fontWeight: 700 }}>Revenue</th><th style={{ color: 'black', fontWeight: 700 }}>Orders</th></tr></thead>
                                <tbody>
                                    {revTrend.slice(-7).map(r => (
                                        <tr key={r.date}>
                                            <td>{r.date}</td>
                                            <td style={{ fontWeight: 500 }}>{fmt(r.revenue, 'currency')}</td>
                                            <td>{r.orders}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>

                {/* ── Bundle suggestions ── */}
                <div className="card">
                    <div className="section-header">
                        <span className="section-title">Top bundle opportunities</span>
                        <Link to="/market-basket" style={{ fontSize: 12, color: 'var(--blue)', textDecoration: 'none' }}>View all →</Link>
                    </div>
                    {loading ? <div className="skeleton" style={{ height: 120 }} /> : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                            {bundles.map((b, i) => (
                                <div key={i} style={{
                                    background: '#fef9ee', border: '1px solid #fde68a',
                                    borderRadius: 8, padding: '10px 14px',
                                }}>
                                    <div style={{ fontWeight: 500, fontSize: 13 }}>
                                        {b.trigger_item}
                                        <span style={{ color: 'var(--accent)', margin: '0 8px' }}>→</span>
                                        {b.paired_item}
                                    </div>
                                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 3 }}>
                                        {b.confidence_pct}% confidence · {b.lift}× lift
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* ── Sentiment summary ── */}
            {!loading && sentData && (
                <div className="card">
                    <div className="section-header">
                        <span className="section-title">Customer sentiment snapshot</span>
                        <Link to="/sentiment" style={{ fontSize: 12, color: 'var(--blue)', textDecoration: 'none' }}>Full analysis →</Link>
                    </div>
                    <div style={{ display: 'flex', gap: 32 }}>
                        <div>
                            <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>Avg rating</div>
                            <div style={{ fontFamily: 'var(--font-heading)', fontSize: 24, fontWeight: 600 }}>
                                {sentData.avg_rating} <span style={{ color: '#fbbf24', fontSize: 18 }}>★</span>
                            </div>
                        </div>
                        <div>
                            <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>Positive reviews</div>
                            <div style={{ fontFamily: 'var(--font-heading)', fontSize: 24, fontWeight: 600, color: '#15803d' }}>
                                {sentData.positive_pct}%
                            </div>
                        </div>
                        <div>
                            <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>Total reviews</div>
                            <div style={{ fontFamily: 'var(--font-heading)', fontSize: 24, fontWeight: 600 }}>
                                {sentData.total_reviews.toLocaleString()}
                            </div>
                        </div>
                        <div>
                            <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>Negative reviews</div>
                            <div style={{ fontFamily: 'var(--font-heading)', fontSize: 24, fontWeight: 600, color: '#b91c1c' }}>
                                {sentData.negative_pct}%
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}