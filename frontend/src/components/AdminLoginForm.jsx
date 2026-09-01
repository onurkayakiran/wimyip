import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ErrorBlock } from './StatusBlock'

export default function AdminLoginForm({ onSubmit, submitting, error }) {
  const { t } = useTranslation()
  const [password, setPassword] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    onSubmit(password)
  }

  return (
    <section className="card">
      <h2>{t('admin.login_title')}</h2>
      <form className="search" onSubmit={handleSubmit}>
        <input
          type="password"
          placeholder={t('admin.password_placeholder')}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoFocus
        />
        <button type="submit" disabled={submitting || !password}>
          {submitting ? t('admin.checking') : t('admin.login')}
        </button>
      </form>
      <ErrorBlock message={error} />
    </section>
  )
}
