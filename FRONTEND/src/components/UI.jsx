export function MetricTile({ label, value, sub, accent }) {
    return (
        <div className="metric-tile" style={accent ? { borderTop: `3px solid ${accent}` } : {}}>
            <div className="label" style={{ color: "black" }}><b>{label}</b></div>
            <div className="value">{value}</div>
            {sub && <div className="sub">{sub}</div>}
        </div>
    )
}

export function LoadingCard({ height = 200 }) {
    return (
        <div className="card">
            <div className="skeleton" style={{ height, borderRadius: 8 }} />
        </div>
    )
}

export function LoadingTiles({ count = 4 }) {
    return (
        <>
            {Array.from({ length: count }).map((_, i) => (
                <div key={i} className="metric-tile">
                    <div className="skeleton" style={{ height: 12, width: '40%', marginBottom: 10 }} />
                    <div className="skeleton" style={{ height: 28, width: '60%', marginBottom: 6 }} />
                    <div className="skeleton" style={{ height: 10, width: '30%' }} />
                </div>
            ))}
        </>
    )
}

export function ErrorCard({ message }) {
    return (
        <div className="error-box">
            <strong>Failed to load</strong><br />
            <span style={{ color: '#ef4444', fontSize: 12 }}>{message}</span>
        </div>
    )
}

export function SectionHeader({ title, children }) {
    return (
        <div className="section-header">
            <span className="section-title">{title}</span>
            {children}
        </div>
    )
}

export function Badge({ type, children }) {
    return <span className={`badge badge-${type}`}>{children}</span>
}

export function PeriodSelector({ value, onChange }) {
    const periods = ['7d', '30d', '90d', 'all']
    return (
        <div className="period-selector">
            {periods.map(p => (
                <button
                    key={p}
                    className={`period-btn${value === p ? ' active' : ''}`}
                    onClick={() => onChange(p)}
                >
                    {p === 'all' ? 'All time' : p}
                </button>
            ))}
        </div>
    )
}

export function fmt(num, type = 'number') {
    if (num == null) return '—'
    if (type === 'currency') return `₹${Number(num).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
    if (type === 'pct') return `${Number(num).toFixed(1)}%`
    if (type === 'decimal') return Number(num).toFixed(2)
    return Number(num).toLocaleString('en-IN')
}