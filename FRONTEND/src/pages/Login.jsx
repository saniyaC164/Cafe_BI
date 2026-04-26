import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { loginUser } from '../api'

export default function Login() {
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState(null)
    const [loading, setLoading] = useState(false)
    const navigate = useNavigate()

    async function handleSubmit(e) {
        e.preventDefault()
        setError(null)
        setLoading(true)
        try {
            await loginUser(email, password)
            navigate('/')
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div style={{
            minHeight: '100vh', background: '#0f172a',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
            <div style={{
                background: '#fff', borderRadius: 16, padding: '40px 36px',
                width: '100%', maxWidth: 400, boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
            }}>
                <div style={{ marginBottom: 28, textAlign: 'center' }}>
                    <div style={{ fontFamily: 'var(--font-heading)', fontSize: 22, fontWeight: 700, color: '#0f172a' }}>
                        Brew Analytics
                    </div>
                    <div style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>
                        Sign in to your dashboard
                    </div>
                </div>

                <form onSubmit={handleSubmit}>
                    <div style={{ marginBottom: 16 }}>
                        <label style={{ fontSize: 12, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 6 }}>
                            Email
                        </label>
                        <input
                            type="email" value={email} required
                            onChange={e => setEmail(e.target.value)}
                            placeholder="admin@brewanalytics.com"
                            style={{
                                width: '100%', padding: '10px 12px', borderRadius: 8,
                                border: '1px solid #e2e8f0', fontSize: 14,
                                outline: 'none', boxSizing: 'border-box',
                            }}
                        />
                    </div>

                    <div style={{ marginBottom: 24 }}>
                        <label style={{ fontSize: 12, fontWeight: 600, color: '#374151', display: 'block', marginBottom: 6 }}>
                            Password
                        </label>
                        <input
                            type="password" value={password} required
                            onChange={e => setPassword(e.target.value)}
                            placeholder="••••••••"
                            style={{
                                width: '100%', padding: '10px 12px', borderRadius: 8,
                                border: '1px solid #e2e8f0', fontSize: 14,
                                outline: 'none', boxSizing: 'border-box',
                            }}
                        />
                    </div>

                    {error && (
                        <div style={{
                            background: '#fff5f5', border: '1px solid #fecaca',
                            borderRadius: 8, padding: '10px 12px', marginBottom: 16,
                            fontSize: 13, color: '#b91c1c',
                        }}>
                            {error}
                        </div>
                    )}

                    <button
                        type="submit" disabled={loading}
                        style={{
                            width: '100%', padding: '11px', borderRadius: 8,
                            background: loading ? '#94a3b8' : '#0f172a',
                            color: '#fff', border: 'none', fontSize: 14,
                            fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer',
                            transition: 'background 0.15s',
                        }}
                    >
                        {loading ? 'Signing in…' : 'Sign in'}
                    </button>
                </form>
                {/* 
                <div style={{ marginTop: 20, padding: '12px', background: '#f8fafc', borderRadius: 8, fontSize: 12, color: '#64748b', textAlign: 'center' }}>
                    Default: admin@brewanalytics.com / admin123
                </div> */}
            </div>
        </div>
    )
}