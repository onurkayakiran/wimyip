import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { ErrorBlock } from '../components/StatusBlock'
import useAuth from '../hooks/useAuth'

export default function RegisterPage() {
  const { t } = useTranslation()
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
      <h2>{t('auth.register_title')}</h2>
      <form className="search" onSubmit={handleSubmit} style={{ flexDirection: 'column', alignItems: 'stretch' }}>
        <input
          type="text"
          placeholder={t('auth.username_hint')}
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoFocus
        />
        <input type="email" placeholder={t('auth.email')} value={email} onChange={(e) => setEmail(e.target.value)} />
        <input
          type="password"
          placeholder={t('auth.password_hint')}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit" disabled={submitting || !username || !email || !password}>
          {submitting ? t('auth.registering') : t('auth.register_button')}
        </button>
      </form>
      <ErrorBlock message={error} />
      <p className="muted" style={{ marginTop: '0.75rem' }}>
        {t('auth.have_account')} <Link to="/login">{t('auth.login_link')}</Link>
      </p>
    </section>
  )
}
