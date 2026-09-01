import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { changePassword, updateProfile } from '../api'
import { ErrorBlock } from '../components/StatusBlock'
import useAuth from '../hooks/useAuth'

function ProfileForm({ token, user, onUpdated }) {
  const { t } = useTranslation()
  const [email, setEmail] = useState(user.email || '')
  const [firstName, setFirstName] = useState(user.first_name || '')
  const [lastName, setLastName] = useState(user.last_name || '')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [saved, setSaved] = useState(false)

  function handleSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    setSaved(false)
    updateProfile(token, { email, first_name: firstName, last_name: lastName })
      .then(() => {
        setSaved(true)
        onUpdated()
      })
      .catch((err) => setError(err.message))
      .finally(() => setSubmitting(false))
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem', maxWidth: '420px' }}>
      <label className="form-field muted">
        {t('profile.username')}
        <input type="text" value={user.username} disabled />
      </label>
      <label className="form-field muted">
        {t('profile.email')}
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      </label>
      <label className="form-field muted">
        {t('profile.first_name')}
        <input type="text" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
      </label>
      <label className="form-field muted">
        {t('profile.last_name')}
        <input type="text" value={lastName} onChange={(e) => setLastName(e.target.value)} />
      </label>
      <button type="submit" disabled={submitting || !email}>
        {submitting ? t('profile.saving') : t('profile.save')}
      </button>
      {saved && <span style={{ color: '#3ecf6e' }}>{t('profile.saved')}</span>}
      <ErrorBlock message={error} />
    </form>
  )
}

function PasswordForm({ token }) {
  const { t } = useTranslation()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [saved, setSaved] = useState(false)

  function handleSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    setSaved(false)
    changePassword(token, currentPassword, newPassword)
      .then(() => {
        setSaved(true)
        setCurrentPassword('')
        setNewPassword('')
      })
      .catch((err) => setError(err.message))
      .finally(() => setSubmitting(false))
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.9rem', maxWidth: '420px' }}>
      <label className="form-field muted">
        {t('profile.current_password')}
        <input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} />
      </label>
      <label className="form-field muted">
        {t('profile.new_password')}
        <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
      </label>
      <button type="submit" disabled={submitting || !currentPassword || !newPassword}>
        {submitting ? t('profile.changing_password') : t('profile.change_password_button')}
      </button>
      {saved && <span style={{ color: '#3ecf6e' }}>{t('profile.password_changed')}</span>}
      <ErrorBlock message={error} />
    </form>
  )
}

export default function ProfilePage() {
  const { t } = useTranslation()
  const { token, user, refreshProfile } = useAuth()
  const [localUser, setLocalUser] = useState(user)

  useEffect(() => {
    setLocalUser(user)
  }, [user])

  if (!localUser) {
    return null
  }

  const planLabel = localUser.plan === 'premium' ? t('profile.plan_premium') : t('profile.plan_free')

  return (
    <div>
      <div className="card-header">
        <h1 style={{ fontSize: '1.2rem', margin: 0 }}>{t('profile.title')}</h1>
        <span className={`badge ${localUser.plan === 'premium' ? 'badge-ok' : 'badge'}`}>{planLabel}</span>
      </div>

      <section className="card">
        <h2>{t('profile.account_info')}</h2>
        <ProfileForm token={token} user={localUser} onUpdated={refreshProfile} />
      </section>

      <section className="card">
        <h2>{t('profile.change_password')}</h2>
        <PasswordForm token={token} />
      </section>
    </div>
  )
}
