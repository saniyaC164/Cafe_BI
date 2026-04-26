import { NavLink } from 'react-router-dom'
import { logoutUser } from '../api'

const NAV = [
    { to: '/', label: 'Overview', icon: '▦' },
    { to: '/kpi', label: 'KPI Dashboard', icon: '◈' },
    { to: '/market-basket', label: 'Market Basket', icon: '⬡' },
    { to: '/sentiment', label: 'Sentiment', icon: '◉' },
    { to: '/forecasting', label: 'Forecasting', icon: '◎' },
    { to: '/inventory', label: 'Inventory', icon: '◫' },
]

const sidebarStyle = {
    width: 220,
    minHeight: '100vh',
    background: 'var(--sidebar-bg)',
    display: 'flex',
    flexDirection: 'column',
    flexShrink: 0,
    position: 'sticky',
    top: 0,
    height: '100vh',
    overflowY: 'auto',
}

const logoStyle = {
    padding: '24px 20px 20px',
    borderBottom: '1px solid #1e293b',
}

const brandStyle = {
    fontFamily: 'var(--font-heading)',
    fontSize: 16,
    fontWeight: 600,
    color: '#f1f5f9',
    letterSpacing: '-0.01em',
}

const taglineStyle = {
    fontSize: 11,
    color: 'var(--sidebar-text)',
    marginTop: 2,
}

const navStyle = {
    padding: '12px 10px',
    flex: 1,
}

const linkBase = {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '9px 12px',
    borderRadius: 8,
    textDecoration: 'none',
    fontSize: 13,
    fontWeight: 500,
    color: 'var(--sidebar-text)',
    marginBottom: 2,
    transition: 'all 0.15s',
}

const footerStyle = {
    padding: '16px 20px',
    borderTop: '1px solid #1e293b',
    fontSize: 11,
    color: '#334155',
}

export default function Sidebar() {
    return (
        <aside style={sidebarStyle}>
            <div style={logoStyle}>
                <div style={brandStyle}>Brew Analytics</div>
                <div style={taglineStyle}>Cafe business intelligence</div>
            </div>

            <nav style={navStyle}>
                {NAV.map(({ to, label, icon }) => (
                    <NavLink
                        key={to}
                        to={to}
                        end={to === '/'}
                        style={({ isActive }) => ({
                            ...linkBase,
                            background: isActive ? '#1e293b' : 'transparent',
                            color: isActive ? '#f1f5f9' : 'var(--sidebar-text)',
                            borderLeft: isActive ? '3px solid var(--sidebar-active)' : '3px solid transparent',
                        })}
                    >
                        <span style={{ fontSize: 14 }}>{icon}</span>
                        {label}
                    </NavLink>
                ))}
            </nav>

            <div style={{ padding: '16px 10px', borderTop: '1px solid #1e293b' }}>
                {(() => {
                    const user = JSON.parse(localStorage.getItem('user') || '{}')
                    return (
                        <div style={{ marginBottom: 10, padding: '0 8px' }}>
                            <div style={{ fontSize: 12, fontWeight: 500, color: '#f1f5f9' }}>{user.name}</div>
                            <div style={{ fontSize: 11, color: '#475569' }}>{user.email}</div>
                        </div>
                    )
                })()}
                <button
                    onClick={logoutUser}
                    style={{
                        width: '100%', padding: '8px 12px', borderRadius: 8,
                        background: 'transparent', border: '1px solid #295aa7',
                        color: '#c5ccd5', fontSize: 12, cursor: 'pointer',
                        textAlign: 'left', transition: 'all 0.15s',
                    }}
                    onMouseEnter={e => e.target.style.background = '#1e293b'}
                    onMouseLeave={e => e.target.style.background = 'transparent'}
                >
                    Sign out
                </button>
            </div>
        </aside>
    )
}