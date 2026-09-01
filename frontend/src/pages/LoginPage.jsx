import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ErrorBlock } from '../components/StatusBlock'
import useAuth from '../hooks/useAuth'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  function handleSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    login(username, password)
      .then(() => navigate('/monitors'))
      .catch((err) => setError(err.message))
      .finally(() => setSubmitting(false))
  }

  return (
    <section className="card">
      <h2>Giriş Yap</h2>
      <form className="search" onSubmit={handleSubmit} style={{ flexDirection: 'column', alignItems: 'stretch' }}>
        <input
          type="text"
          placeholder="Kullanıcı adı"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoFocus
        />
        <input
          type="password"
          placeholder="Parola"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit" disabled={submitting || !username || !password}>
          {submitting ? 'Giriş yapılıyor...' : 'Giriş Yap'}
        </button>
      </form>
      <ErrorBlock message={error} />
      <p className="muted" style={{ marginTop: '0.75rem' }}>
        Hesabınız yok mu? <Link to="/register">Kayıt olun</Link>
      </p>
    </section>
  )
}
