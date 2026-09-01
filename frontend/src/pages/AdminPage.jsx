import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import AdminLoginForm from '../components/AdminLoginForm'
import JobStatusPanel from '../components/JobStatusPanel'
import RemoteWorkersPanel from '../components/RemoteWorkersPanel'
import TrDomainsModal from '../components/TrDomainsModal'
import UsersPanel from '../components/UsersPanel'
import useAdminAuth from '../hooks/useAdminAuth'

export default function AdminPage() {
  const { t } = useTranslation()
  const { password, loggedIn, loginError, loginSubmitting, tryLogin, logout } = useAdminAuth()
  const [showTrDomains, setShowTrDomains] = useState(false)

  if (!loggedIn) {
    return <AdminLoginForm onSubmit={tryLogin} submitting={loginSubmitting} error={loginError} />
  }

  return (
    <div>
      <div className="card-header">
        <h1 style={{ fontSize: '1.2rem', margin: 0 }}>{t('admin.title')}</h1>
        <span>
          <button onClick={() => setShowTrDomains(true)}>{t('admin.tr_domain_scan')}</button>{' '}
          <button onClick={logout}>{t('admin.logout')}</button>
        </span>
      </div>

      <JobStatusPanel />

      <UsersPanel password={password} />

      <RemoteWorkersPanel password={password} />

      {showTrDomains && <TrDomainsModal onClose={() => setShowTrDomains(false)} />}
    </div>
  )
}
