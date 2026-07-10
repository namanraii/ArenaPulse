import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ShieldCheck, LogIn, User } from 'lucide-react'
import { auth } from '../services/api'
import type { UserRole } from '../types'

export function LoginPage() {
  const navigate = useNavigate()
  const [role, setRole] = useState<UserRole>('organizer')
  const [username, setUsername] = useState('organizer')
  const [password, setPassword] = useState('password')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username.trim()) {
      setError('Please enter a username.')
      return
    }
    setLoading(true)
    setError('')
    try {
      const user = await auth.login(username.trim(), password, role)
      if (!user) {
        setError('Invalid credentials. Try organizer / password.')
        return
      }
      if (role === 'fan') {
        navigate('/')
      } else {
        navigate('/ops')
      }
    } catch {
      setError('Login failed. Demo credentials: organizer / password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <form onSubmit={submit} className="login-card" aria-labelledby="login-title">
        <div className="login-brand">
          <ShieldCheck size={32} />
          <h1 id="login-title">ArenaPulse</h1>
          <p>FIFA World Cup 2026 Operations</p>
        </div>

        <label>
          <span>Username</span>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="organizer"
            autoComplete="username"
            autoFocus
          />
        </label>

        <label>
          <span>Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="password"
            autoComplete="current-password"
          />
        </label>

        <label>
          <span>Role</span>
          <select value={role} onChange={(e) => setRole(e.target.value as UserRole)}>
            <option value="fan">Fan</option>
            <option value="volunteer">Volunteer</option>
            <option value="organizer">Organizer</option>
          </select>
        </label>

        {error && (
          <p className="error-text" role="alert">
            {error}
          </p>
        )}

        <button type="submit" disabled={loading}>
          <LogIn size={16} /> {loading ? 'Signing in...' : 'Sign In'}
        </button>

        <p className="demo-hint">
          <User size={14} /> Demo: organizer / volunteer / fan — password: password
        </p>
      </form>
    </div>
  )
}
