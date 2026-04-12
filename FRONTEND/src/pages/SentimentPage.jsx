import { useState } from 'react'
import {
    LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'
import { useFetch } from '../hooks/useFetch'
import { sentiment as sentApi } from '../api'
import { LoadingCard, LoadingTiles, ErrorCard, SectionHeader, fmt } from '../components/UI'

const SENTIMENT_COLORS = {
    positive: { bg: '#dcfce7', text: '#15803d', bar: '#22c55e' },
    negative: { bg: '#fee2e2', text: '#b91c1c', bar: '#ef4444' },
    neutral: { bg: '#f1f5f9', text: '#475569', bar: '#94a3b8' },
}
const ASPECT_COLORS = { positive: '#14b8a6', negative: '#f97316' }
const PIE_COLORS = ['#22c55e', '#94a3b8', '#ef4444']
const SOURCE_OPTS = ['all', 'Google', 'Zomato']
const SENT_FILTERS = ['all', 'positive', 'negative', 'neutral']

function StarRating({ rating }) {
    return (
        <span style={{ color: '#fbbf24', fontSize: 12, letterSpacing: 1 }}>
            {'★'.repeat(rating)}
            <span style={{ color: '#e2e8f0' }}>{'★'.repeat(5 - rating)}</span>
        </span>
    )
}

function SentBadge({ type }) {
    const c = SENTIMENT_COLORS[type] || SENTIMENT_COLORS.neutral
    return (
        <span style={{ background: c.bg, color: c.text, padding: '2px 9px', borderRadius: 99, fontSize: 11, fontWeight: 600 }}>
            {type}
        </span>
    )
}

function SourceBadge({ source }) {
    const styles = {
        Google: { bg: '#dbeafe', text: '#1d4ed8' },
        Zomato: { bg: '#fce7f3', text: '#9d174d' },
    }
    const s = styles[source] || { bg: '#f1f5f9', text: '#475569' }
    return (
        <span style={{ background: s.bg, color: s.text, padding: '2px 9px', borderRadius: 99, fontSize: 11, fontWeight: 600 }}>
            {source}
        </span>
    )
}

function WordCloud({ words, color }) {
    if (!words?.length) return null
    const max = Math.max(...words.map(w => w.count), 1)
    return (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', padding: '4px 0' }}>
            {words.map((w, i) => {
                const size = 11 + Math.round((w.count / max) * 14)
                const opacity = 0.4 + (w.count / max) * 0.6
                return (
                    <span key={i} style={{
                        fontSize: size, fontWeight: size > 18 ? 600 : 500,
                        color, opacity,
                        padding: '1px 4px',
                        cursor: 'default',
                    }}>
                        {w.word}
                    </span>
                )
            })}
        </div>
    )
}

function ReviewCard({ review }) {
    return (
        <div style={{
            background: '#fff', border: '1px solid var(--border)',
            borderRadius: 10, padding: '14px 16px',
            borderLeft: `3px solid ${SENTIMENT_COLORS[review.sentiment]?.bar || '#94a3b8'}`,
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
                <SourceBadge source={review.source} />
                <StarRating rating={review.rating} />
                <SentBadge type={review.sentiment} />
                <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>{review.date}</span>
            </div>
            <p style={{ fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.6, margin: '0 0 8px' }}>
                {review.review_text}
            </p>
            {review.aspect_tags?.length > 0 && (
                <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {review.aspect_tags.map((tag, i) => (
                        <span key={i} style={{
                            background: '#f8fafc', border: '1px solid var(--border)',
                            borderRadius: 99, padding: '1px 8px', fontSize: 10, color: 'var(--text-secondary)',
                        }}>
                            {tag.replace(/_/g, ' ')}
                        </span>
                    ))}
                </div>
            )}
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
                <div key={i} style={{ color: p.color }}>{p.name}: {p.value}</div>
            ))}
        </div>
    )
}

export default function SentimentPage() {
    const [source, setSource] = useState('all')
    const [sentFilter, setSentFilter] = useState('all')
    const [reviewLimit, setReviewLimit] = useState(10)

    const { data, loading, error } = useFetch(
        () => sentApi.dashboard(source), [source]
    )

    const { data: reviews, loading: revLoading } = useFetch(
        () => sentApi.reviews(sentFilter, source, reviewLimit),
        [sentFilter, source, reviewLimit]
    )

    if (error) return (
        <div className="page-wrapper">
            <div className="page-title-row"><h1>Sentiment Analysis</h1></div>
            <ErrorCard message={error} />
        </div>
    )

    const summary = data?.summary
    const trend = (data?.trend || []).map(t => ({
        week: t.week?.slice(0, 10),
        score: parseFloat(t.avg_score?.toFixed(2)),
        positive: t.positive_count,
        negative: t.negative_count,
        neutral: t.neutral_count,
    }))
    const aspects = data?.aspect_scores || []
    const items = data?.item_sentiment || []
    const posWords = data?.top_positive_words || []
    const negWords = data?.top_negative_words || []

    const pieData = summary ? [
        { name: 'Positive', value: parseFloat(summary.positive_pct) },
        { name: 'Neutral', value: parseFloat(summary.neutral_pct) },
        { name: 'Negative', value: parseFloat(summary.negative_pct) },
    ] : []

    const aspectChart = aspects.map(a => ({
        name: a.aspect.charAt(0).toUpperCase() + a.aspect.slice(1),
        positive: parseFloat(a.positive_pct.toFixed(1)),
        negative: parseFloat(a.negative_pct.toFixed(1)),
        mentions: a.mention_count,
    }))

    return (
        <div className="page-wrapper gap-16">
            {/* ── Header + source filter ── */}
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
                <div className="page-title-row" style={{ marginBottom: 0 }}>
                    <h1>Sentiment Analysis</h1>
                    <p>Customer review insights from Google and Zomato</p>
                </div>
                <div style={{ display: 'flex', gap: 4, background: 'var(--border)', padding: 3, borderRadius: 8 }}>
                    {SOURCE_OPTS.map(s => (
                        <button key={s}
                            onClick={() => setSource(s)}
                            className={`period-btn${source === s ? ' active' : ''}`}
                        >
                            {s === 'all' ? 'All sources' : s}
                        </button>
                    ))}
                </div>
            </div>

            {/* ── Summary tiles ── */}
            <div className="grid-4">
                {loading ? <LoadingTiles count={4} /> : summary ? (
                    <>
                        <div className="metric-tile" style={{ borderTop: '3px solid #22c55e' }}>
                            <div className="label">Total reviews</div>
                            <div className="value">{summary.total_reviews.toLocaleString()}</div>
                            <div className="sub">{summary.google_count} Google · {summary.zomato_count} Zomato</div>
                        </div>
                        <div className="metric-tile" style={{ borderTop: '3px solid #fbbf24' }}>
                            <div className="label">Avg rating</div>
                            <div className="value" style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                                {summary.avg_rating}
                                <span style={{ fontSize: 16, color: '#fbbf24' }}>★</span>
                            </div>
                            <div className="sub">Out of 5.0</div>
                        </div>
                        <div className="metric-tile" style={{ borderTop: '3px solid #22c55e' }}>
                            <div className="label">Positive</div>
                            <div className="value" style={{ color: '#15803d' }}>{summary.positive_pct}%</div>
                            <div className="sub">{Math.round(summary.total_reviews * summary.positive_pct / 100)} reviews</div>
                        </div>
                        <div className="metric-tile" style={{ borderTop: '3px solid #ef4444' }}>
                            <div className="label">Negative</div>
                            <div className="value" style={{ color: '#b91c1c' }}>{summary.negative_pct}%</div>
                            <div className="sub">{Math.round(summary.total_reviews * summary.negative_pct / 100)} reviews</div>
                        </div>
                    </>
                ) : null}
            </div>

            {/* ── Trend + donut ── */}
            <div className="grid-2-1">
                <div className="card">
                    <SectionHeader title="Weekly sentiment trend" />
                    {loading
                        ? <div className="skeleton" style={{ height: 240 }} />
                        : (
                            <div className="chart-wrap">
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={trend} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                        <XAxis dataKey="week" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                                        <YAxis tick={{ fontSize: 11 }} domain={[1, 5]} />
                                        <Tooltip content={<CustomTooltip />} />
                                        <Line type="monotone" dataKey="score" name="Avg rating"
                                            stroke="#14b8a6" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        )
                    }
                </div>

                <div className="card">
                    <SectionHeader title="Sentiment split" />
                    {loading
                        ? <div className="skeleton" style={{ height: 240 }} />
                        : (
                            <>
                                <div style={{ height: 180 }}>
                                    <ResponsiveContainer width="100%" height="100%">
                                        <PieChart>
                                            <Pie data={pieData} dataKey="value" cx="50%" cy="50%"
                                                innerRadius={50} outerRadius={75} paddingAngle={3}>
                                                {pieData.map((_, i) => (
                                                    <Cell key={i} fill={PIE_COLORS[i]} />
                                                ))}
                                            </Pie>
                                            <Tooltip formatter={(v) => `${v}%`} />
                                        </PieChart>
                                    </ResponsiveContainer>
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 4 }}>
                                    {pieData.map((d, i) => (
                                        <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                                <div style={{ width: 10, height: 10, borderRadius: 2, background: PIE_COLORS[i] }} />
                                                {d.name}
                                            </div>
                                            <strong>{d.value}%</strong>
                                        </div>
                                    ))}
                                </div>
                            </>
                        )
                    }
                </div>
            </div>

            {/* ── Aspect breakdown ── */}
            <div className="card">
                <SectionHeader title="Sentiment by aspect">
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                        Teal = positive %, Orange = negative %
                    </span>
                </SectionHeader>
                {loading
                    ? <div className="skeleton" style={{ height: 200 }} />
                    : (
                        <div className="chart-wrap">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={aspectChart} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                    <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                                    <YAxis tick={{ fontSize: 11 }} unit="%" domain={[0, 100]} />
                                    <Tooltip formatter={(v) => `${v}%`} />
                                    <Legend />
                                    <Bar dataKey="positive" name="Positive %" fill={ASPECT_COLORS.positive} radius={[4, 4, 0, 0]} />
                                    <Bar dataKey="negative" name="Negative %" fill={ASPECT_COLORS.negative} radius={[4, 4, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    )
                }
            </div>

            {/* ── Review feed + Item sentiment ── */}
            <div className="grid-2">
                <div className="card">
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
                        <span className="section-title">Recent reviews</span>
                        <div style={{ display: 'flex', gap: 3 }}>
                            {SENT_FILTERS.map(f => (
                                <button key={f}
                                    onClick={() => setSentFilter(f)}
                                    style={{
                                        padding: '3px 10px', borderRadius: 6,
                                        border: '1px solid var(--border)',
                                        background: sentFilter === f ? '#0f172a' : 'transparent',
                                        color: sentFilter === f ? '#fff' : 'var(--text-secondary)',
                                        fontSize: 11, fontWeight: 500, cursor: 'pointer',
                                        textTransform: 'capitalize',
                                    }}
                                >
                                    {f}
                                </button>
                            ))}
                        </div>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxHeight: 520, overflowY: 'auto' }}>
                        {revLoading
                            ? [1, 2, 3].map(i => <div key={i} className="skeleton" style={{ height: 90, borderRadius: 8 }} />)
                            : (reviews || []).map((r, i) => <ReviewCard key={i} review={r} />)
                        }
                        {!revLoading && reviews?.length === 0 && (
                            <p style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'center', padding: '20px 0' }}>
                                No reviews match this filter.
                            </p>
                        )}
                    </div>
                    {reviews?.length >= reviewLimit && (
                        <button
                            onClick={() => setReviewLimit(l => l + 10)}
                            style={{
                                width: '100%', marginTop: 12, padding: '8px',
                                border: '1px solid var(--border)', borderRadius: 8,
                                background: 'transparent', cursor: 'pointer',
                                fontSize: 12, color: 'var(--text-secondary)',
                            }}
                        >
                            Load more reviews
                        </button>
                    )}
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    {/* Item sentiment table */}
                    <div className="card">
                        <SectionHeader title="Item-level sentiment" />
                        {loading
                            ? <div className="skeleton" style={{ height: 160 }} />
                            : (
                                <table className="data-table">
                                    <thead>
                                        <tr>
                                            <th>Item</th>
                                            <th>Mentions</th>
                                            <th>Avg rating</th>
                                            <th>Sentiment</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {items.slice(0, 8).map((item, i) => (
                                            <tr key={i}>
                                                <td style={{ fontWeight: 500 }}>{item.item_name}</td>
                                                <td style={{ color: 'var(--text-secondary)' }}>{item.mention_count}</td>
                                                <td>
                                                    <span style={{ color: '#fbbf24' }}>★</span> {item.avg_rating}
                                                </td>
                                                <td><SentBadge type={item.sentiment} /></td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )
                        }
                    </div>

                    {/* Word clouds */}
                    <div className="card">
                        <SectionHeader title="What customers say" />
                        {loading
                            ? <div className="skeleton" style={{ height: 120 }} />
                            : (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                                    <div>
                                        <div style={{ fontSize: 11, fontWeight: 600, color: '#15803d', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                            Positive reviews
                                        </div>
                                        <WordCloud words={posWords} color="#15803d" />
                                    </div>
                                    <div style={{ borderTop: '1px solid var(--border)', paddingTop: 14 }}>
                                        <div style={{ fontSize: 11, fontWeight: 600, color: '#b91c1c', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                            Negative reviews
                                        </div>
                                        <WordCloud words={negWords} color="#b91c1c" />
                                    </div>
                                </div>
                            )
                        }
                    </div>
                </div>
            </div>
        </div>
    )
}