import { useState, useMemo } from 'react'
import { useFetch } from '../hooks/useFetch'
import { mba } from '../api'
import { LoadingCard, ErrorCard, SectionHeader, fmt } from '../components/UI'

function LiftBadge({ lift }) {
    const color = lift >= 2
        ? { bg: '#dcfce7', text: '#15803d' }
        : lift >= 1.5
            ? { bg: '#fef3c7', text: '#92400e' }
            : { bg: '#f1f5f9', text: '#475569' }
    return (
        <span style={{
            background: color.bg, color: color.text,
            padding: '2px 8px', borderRadius: 99,
            fontSize: 11, fontWeight: 600,
        }}>
            {lift.toFixed(2)}×
        </span>
    )
}

function ConfBar({ value }) {
    return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ flex: 1, background: '#f1f5f9', borderRadius: 99, height: 6, overflow: 'hidden' }}>
                <div style={{
                    width: `${(value * 100).toFixed(1)}%`,
                    height: '100%', background: '#8b5cf6', borderRadius: 99,
                }} />
            </div>
            <span style={{ fontSize: 11, fontWeight: 600, minWidth: 36 }}>
                {(value * 100).toFixed(1)}%
            </span>
        </div>
    )
}

function PairHeatmap({ pairs }) {
    if (!pairs?.length) return null

    const items = [...new Set([
        ...pairs.map(p => p.item_a),
        ...pairs.map(p => p.item_b),
    ])].slice(0, 12)

    const lookup = {}
    pairs.forEach(p => {
        lookup[`${p.item_a}||${p.item_b}`] = p.co_count
        lookup[`${p.item_b}||${p.item_a}`] = p.co_count
    })

    const maxCount = Math.max(...pairs.map(p => p.co_count), 1)

    const getColor = (count) => {
        if (!count) return '#f8fafc'
        const t = count / maxCount
        if (t > 0.75) return '#4f46e5'
        if (t > 0.5) return '#818cf8'
        if (t > 0.25) return '#c7d2fe'
        return '#e0e7ff'
    }

    const short = name => name.length > 10 ? name.slice(0, 9) + '…' : name

    return (
        <div style={{ overflowX: 'auto' }}>
            <table style={{ borderCollapse: 'collapse', fontSize: 11 }}>
                <thead>
                    <tr>
                        <th style={{ padding: '4px 8px', color: 'var(--text-muted)', fontWeight: 500, width: 90 }} />
                        {items.map(item => (
                            <th key={item} style={{
                                padding: '4px 6px', color: 'var(--text-secondary)',
                                fontWeight: 500, textAlign: 'center', maxWidth: 60,
                            }}>
                                {short(item)}
                            </th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {items.map(rowItem => (
                        <tr key={rowItem}>
                            <td style={{ padding: '3px 8px', color: 'var(--text-secondary)', fontWeight: 500, whiteSpace: 'nowrap' }}>
                                {short(rowItem)}
                            </td>
                            {items.map(colItem => {
                                const count = rowItem === colItem ? null : lookup[`${rowItem}||${colItem}`]
                                return (
                                    <td key={colItem} style={{ padding: '2px 3px' }}>
                                        <div
                                            title={count ? `${rowItem} + ${colItem}: ${count} orders` : rowItem === colItem ? '—' : '0 orders'}
                                            style={{
                                                width: 36, height: 28,
                                                background: rowItem === colItem ? '#e2e8f0' : getColor(count),
                                                borderRadius: 4,
                                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                fontSize: 9, fontWeight: 600,
                                                color: count && count / maxCount > 0.5 ? '#fff' : 'transparent',
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
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 10, fontSize: 11, color: 'var(--text-muted)' }}>
                <div style={{ width: 14, height: 14, background: '#e0e7ff', borderRadius: 3 }} /> Low
                <div style={{ width: 14, height: 14, background: '#818cf8', borderRadius: 3 }} /> Medium
                <div style={{ width: 14, height: 14, background: '#4f46e5', borderRadius: 3 }} /> High co-occurrence
            </div>
        </div>
    )
}

function BundleCard({ bundle }) {
    return (
        <div style={{
            background: '#fffbeb', border: '1px solid #fde68a',
            borderRadius: 10, padding: '14px 16px',
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                <span style={{
                    background: '#fff', border: '1px solid var(--border)',
                    borderRadius: 6, padding: '4px 10px',
                    fontSize: 13, fontWeight: 500,
                }}>
                    {bundle.trigger_item}
                </span>
                <span style={{ color: '#f59e0b', fontSize: 18, fontWeight: 700 }}>→</span>
                <span style={{
                    background: '#fff', border: '1px solid var(--border)',
                    borderRadius: 6, padding: '4px 10px',
                    fontSize: 13, fontWeight: 500,
                }}>
                    {bundle.paired_item}
                </span>
            </div>
            <div style={{ display: 'flex', gap: 10, marginBottom: 8 }}>
                <span style={{ background: '#dcfce7', color: '#15803d', borderRadius: 99, padding: '2px 10px', fontSize: 11, fontWeight: 600 }}>
                    {bundle.confidence_pct}% confidence
                </span>
                <LiftBadge lift={bundle.lift} />
            </div>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0 }}>
                {bundle.insight}
            </p>
        </div>
    )
}

export default function MbaPage() {
    const [minConf, setMinConf] = useState(0.20)
    const [minLift, setMinLift] = useState(1.0)
    const [sortBy, setSortBy] = useState('lift')

    const { data, loading, error } = useFetch(
        () => mba.results(minConf, minLift), [minConf, minLift]
    )

    const { data: pairsData, loading: pairsLoading } = useFetch(
        () => mba.productPairs(), []
    )

    const sortedRules = useMemo(() => {
        if (!data?.rules) return []
        return [...data.rules].sort((a, b) => b[sortBy] - a[sortBy])
    }, [data, sortBy])

    if (error) return (
        <div className="page-wrapper">
            <div className="page-title-row"><h1>Market Basket Analysis</h1></div>
            <ErrorCard message={error} />
        </div>
    )

    return (
        <div className="page-wrapper gap-16">
            <div className="page-title-row">
                <h1>Market Basket Analysis</h1>
                <p>Discover which items are bought together — use these insights to create combo deals</p>
            </div>

            {/* ── Controls ── */}
            <div className="card" style={{ padding: '16px 20px' }}>
                <div style={{ display: 'flex', gap: 40, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                    <div style={{ flex: 1, minWidth: 200 }}>
                        <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 6 }}>
                            Min confidence: <strong style={{ color: 'var(--text-primary)' }}>{(minConf * 100).toFixed(0)}%</strong>
                        </div>
                        <input
                            type="range" min="0.05" max="0.90" step="0.05"
                            value={minConf}
                            onChange={e => setMinConf(parseFloat(e.target.value))}
                            style={{ width: '100%' }}
                        />
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                            <span>5% (more rules)</span><span>90% (fewer, stronger)</span>
                        </div>
                    </div>
                    <div style={{ flex: 1, minWidth: 200 }}>
                        <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 6 }}>
                            Min lift: <strong style={{ color: 'var(--text-primary)' }}>{minLift.toFixed(1)}×</strong>
                        </div>
                        <input
                            type="range" min="1.0" max="5.0" step="0.1"
                            value={minLift}
                            onChange={e => setMinLift(parseFloat(e.target.value))}
                            style={{ width: '100%' }}
                        />
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                            <span>1.0× (random)</span><span>5.0× (very strong)</span>
                        </div>
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                        {loading ? '…' : <><strong style={{ color: 'var(--text-primary)' }}>{sortedRules.length}</strong> rules found</>}
                        {data && <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{data.total_orders_analysed?.toLocaleString()} orders analysed</div>}
                    </div>
                </div>
            </div>

            {/* ── Bundle suggestions ── */}
            <div className="card">
                <SectionHeader title="Bundle suggestions" />
                {loading
                    ? <div className="skeleton" style={{ height: 120 }} />
                    : (
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 12 }}>
                            {(data?.bundle_suggestions || []).map((b, i) => (
                                <BundleCard key={i} bundle={b} />
                            ))}
                            {!data?.bundle_suggestions?.length && (
                                <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                                    No bundles at current thresholds — try lowering confidence or lift.
                                </p>
                            )}
                        </div>
                    )
                }
            </div>

            {/* ── Rules table ── */}
            <div className="card">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                    <span className="section-title">Association rules</span>
                    <div style={{ display: 'flex', gap: 4 }}>
                        {['lift', 'confidence', 'support'].map(s => (
                            <button
                                key={s}
                                onClick={() => setSortBy(s)}
                                style={{
                                    padding: '4px 12px', borderRadius: 6, border: '1px solid var(--border)',
                                    background: sortBy === s ? '#0f172a' : 'transparent',
                                    color: sortBy === s ? '#fff' : 'var(--text-secondary)',
                                    fontSize: 11, fontWeight: 500, cursor: 'pointer',
                                    textTransform: 'capitalize',
                                }}
                            >
                                {s}
                            </button>
                        ))}
                    </div>
                </div>

                {loading
                    ? <div className="skeleton" style={{ height: 200 }} />
                    : sortedRules.length === 0
                        ? <p style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'center', padding: '30px 0' }}>
                            No rules match the current thresholds. Try lowering the sliders.
                        </p>
                        : (
                            <div style={{ overflowX: 'auto' }}>
                                <table className="data-table">
                                    <thead>
                                        <tr>
                                            <th style={{ color: 'black' }}>If customer orders…</th>
                                            <th style={{ color: 'black' }}>They also order…</th>
                                            <th style={{ width: 180 }, { color: 'black' }}>Confidence</th>
                                            <th style={{ color: 'black' }}>Lift</th>
                                            <th style={{ color: 'black' }}>Support</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {sortedRules.map((rule, i) => (
                                            <tr key={i}>
                                                <td>
                                                    <span style={{ fontWeight: 500, color: 'var(--text-primary)' }}>
                                                        {rule.antecedent}
                                                    </span>
                                                </td>
                                                <td>
                                                    <span style={{ color: '#8b5cf6', fontWeight: 500 }}>
                                                        {rule.consequent}
                                                    </span>
                                                </td>
                                                <td><ConfBar value={rule.confidence} /></td>
                                                <td><LiftBadge lift={rule.lift} /></td>
                                                <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                                                    {(rule.support * 100).toFixed(2)}%
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )
                }
            </div>

            {/* ── Product pair heatmap ── */}
            <div className="card">
                <SectionHeader title="Product pair co-occurrence heatmap">
                    <span style={{ fontSize: 12, color: 'black' }}>
                        How often any two items appear in the same order
                    </span>
                </SectionHeader>
                {pairsLoading
                    ? <div className="skeleton" style={{ height: 200 }} />
                    : <PairHeatmap pairs={pairsData} />
                }
            </div>
        </div>
    )
}