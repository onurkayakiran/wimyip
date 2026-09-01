import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { ErrorBlock } from '../components/StatusBlock'
import useAuth from '../hooks/useAuth'

export default function LoginPage() {
  const { t } = useTranslation()
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
      <h2>{t('auth.login_title')}</h2>
      <form className="search" onSubmit={handleSubmit} style={{ flexDirection: 'column', alignItems: 'stretch' }}>
        <input
          type="text"
          placeholder={t('auth.username_or_email')}
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoFocus
        />
        <input
          type="password"
          placeholder={t('auth.password')}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit" disabled={submitting || !username || !password}>
          {submitting ? t('auth.logging_in') : t('auth.login_button')}
        </button>
      </form>
      <ErrorBlock message={error} />
      <p className="muted" style={{ marginTop: '0.75rem' }}>
        {t('auth.no_account')} <Link to="/register">{t('auth.sign_up_link')}</Link>
      </p>
    </section>
  )
}
