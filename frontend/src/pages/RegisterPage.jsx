import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ErrorBlock } from '../components/StatusBlock'
import useAuth from '../hooks/useAuth'

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  function handleSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    register(username, email, password)
      .then(() => navigate('/monitors'))
      .catch((err) => setError(err.message))
      .finally(() => setSubmitting(false))
  }

  return (
    <section className="card">
      <h2>Kayıt Ol</h2>
      <form className="search" onSubmit={handleSubmit} style={{ flexDirection: 'column', alignItems: 'stretch' }}>
        <input
          type="text"
          placeholder="Kullanıcı adı (3-32 karakter)"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoFocus
        />
        <input type="email" placeholder="E-posta" value={email} onChange={(e) => setEmail(e.target.value)} />
        <input
          type="password"
          placeholder="Parola (en az 8 karakter)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit" disabled={submitting || !username || !email || !password}>
          {submitting ? 'Kayıt olunuyor...' : 'Kayıt Ol'}
        </button>
      </form>
      <ErrorBlock message={error} />
      <p className="muted" style={{ marginTop: '0.75rem' }}>
        Zaten hesabınız var mı? <Link to="/login">Giriş yapın</Link>
      </p>
    </section>
  )
}
