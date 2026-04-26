const BASE = 'http://localhost:8000/api'

function getToken() {
    return localStorage.getItem('token')
}

async function get(path) {
    const token = getToken()
    const res = await fetch(`${BASE}${path}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (res.status === 401) {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        window.location.href = '/login'
        return
    }
    if (!res.ok) throw new Error(`API error ${res.status}: ${path}`)
    return res.json()
}

export async function loginUser(email, password) {
    const form = new URLSearchParams()
    form.append('username', email)
    form.append('password', password)

    const res = await fetch(`${BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: form,
    })
    if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Login failed')
    }
    const data = await res.json()
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('user', JSON.stringify({ name: data.name, email: data.email, role: data.role }))
    return data
}

export function logoutUser() {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    window.location.href = '/login'
}

// ── KPI ───────────────────────────────────────────────
export const kpi = {
    dashboard: (period = '30d') => get(`/kpi/dashboard?period=${period}`),
    summary: (period = '30d') => get(`/kpi/summary?period=${period}`),
    revenueTrend: (period = '30d') => get(`/kpi/revenue-trend?period=${period}`),
    topItems: (period = '30d') => get(`/kpi/top-items?period=${period}`),
    channelSplit: (period = '30d') => get(`/kpi/channel-split?period=${period}`),
    hourlyHeatmap: (period = '30d') => get(`/kpi/hourly-heatmap?period=${period}`),
    customerStats: (period = '30d') => get(`/kpi/customer-stats?period=${period}`),
    paymentSplit: (period = '30d') => get(`/kpi/payment-split?period=${period}`),
}

// ── MBA ───────────────────────────────────────────────
export const mba = {
    results: (conf = 0.2, lift = 1.0) =>
        get(`/mba/results?min_confidence=${conf}&min_lift=${lift}&min_support=0.01`),
    productPairs: () => get('/mba/product-pairs'),
    bundles: () => get('/mba/bundle-suggestions'),
    rules: (conf = 0.2, lift = 1.0) =>
        get(`/mba/rules?min_confidence=${conf}&min_lift=${lift}&min_support=0.01`),
}

// ── Inventory ─────────────────────────────────────────
export const inventory = {
    dashboard: () => get('/inventory/dashboard'),
    stockStatus: () => get('/inventory/stock-status'),
    depletionRates: () => get('/inventory/depletion-rates'),
    reorderSuggestions: () => get('/inventory/reorder-suggestions'),
    wastageTrend: (days = 60) => get(`/inventory/wastage-trend?days=${days}`),
    wastageByWeekday: () => get('/inventory/wastage-by-weekday'),
}

// ── Sentiment ─────────────────────────────────────────
export const sentiment = {
    dashboard: (source = 'all') => get(`/sentiment/dashboard?source=${source}`),
    summary: (source = 'all') => get(`/sentiment/summary?source=${source}`),
    trend: (source = 'all') => get(`/sentiment/trend?source=${source}`),
    aspects: () => get('/sentiment/aspects'),
    reviews: (sentiment = 'all', source = 'all', limit = 20) =>
        get(`/sentiment/reviews?sentiment=${sentiment}&source=${source}&limit=${limit}`),
    items: () => get('/sentiment/items'),
    positiveWords: () => get('/sentiment/words/positive'),
    negativeWords: () => get('/sentiment/words/negative'),
}

// ── Forecasting ───────────────────────────────────────
export const forecast = {
    dashboard: (horizon = 30) => get(`/forecast/dashboard?horizon=${horizon}`),
    forecastPoints: (horizon = 30) => get(`/forecast/forecast?horizon=${horizon}`),
    summary: (horizon = 30) => get(`/forecast/summary?horizon=${horizon}`),
    weatherCorrelation: () => get('/forecast/weather-correlation'),
    holidayEffects: (horizon = 30) => get(`/forecast/holiday-effects?horizon=${horizon}`),
}