import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AdminLoginForm from '../components/AdminLoginForm'
import JobStatusPanel from '../components/JobStatusPanel'
import RemoteWorkersPanel from '../components/RemoteWorkersPanel'
import TrDomainsModal from '../components/TrDomainsModal'
import useAdminAuth from '../hooks/useAdminAuth'

export default function AdminPage() {
  const { password, loggedIn, loginError, loginSubmitting, tryLogin, logout } = useAdminAuth()
  const [showTrDomains, setShowTrDomains] = useState(false)
  const navigate = useNavigate()

  if (!loggedIn) {
    return <AdminLoginForm onSubmit={tryLogin} submitting={loginSubmitting} error={loginError} />
  }

  return (
    <div>
      <div className="card-header">
        <h1 style={{ fontSize: '1.2rem', margin: 0 }}>Yönetim Paneli</h1>
        <span>
          <button onClick={() => navigate('/admin/port-scans')}>IP Subnet Taraması</button>{' '}
          <button onClick={() => setShowTrDomains(true)}>Türkiye Domain Taraması</button>{' '}
          <button onClick={logout}>Çıkış</button>
        </span>
      </div>

      <JobStatusPanel />

      <RemoteWorkersPanel password={password} />

      {showTrDomains && <TrDomainsModal onClose={() => setShowTrDomains(false)} />}
    </div>
  )
}
