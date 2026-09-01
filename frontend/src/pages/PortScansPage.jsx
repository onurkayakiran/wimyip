import { useNavigate } from 'react-router-dom'
import AdminLoginForm from '../components/AdminLoginForm'
import PortScanPanel from '../components/PortScanPanel'
import useAdminAuth from '../hooks/useAdminAuth'

export default function PortScansPage() {
  const { password, loggedIn, loginError, loginSubmitting, tryLogin } = useAdminAuth()
  const navigate = useNavigate()

  if (!loggedIn) {
    return <AdminLoginForm onSubmit={tryLogin} submitting={loginSubmitting} error={loginError} />
  }

  return (
    <div>
      <div className="card-header">
        <h1 style={{ fontSize: '1.2rem', margin: 0 }}>IP Subnet Taraması</h1>
        <button onClick={() => navigate('/admin')}>← Yönetim Paneline Dön</button>
      </div>

      <PortScanPanel password={password} />
    </div>
  )
}
