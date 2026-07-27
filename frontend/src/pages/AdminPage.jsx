import { useEffect, useState } from 'react'
import { adminLogin, getAdminServiceLogs, getAdminServices, restartAdminService } from '../api'
import { formatDate } from '../components/HistoryTable'
import JobStatusPanel from '../components/JobStatusPanel'
import { ErrorBlock, Loading } from '../components/StatusBlock'
import TrDomainsModal from '../components/TrDomainsModal'

const STORAGE_KEY = 'adminPassword'

function StatusBadge({ status }) {
  const ok = status === 'running'
  return <span className={`badge ${ok ? 'badge-ok' : 'badge-bad'}`}>{status}</span>
}

function LoginForm({ onSubmit, submitting, error }) {
  const [password, setPassword] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    onSubmit(password)
  }

  return (
    <section className="card">
      <h2>Yönetim Paneli Girişi</h2>
      <form className="search" onSubmit={handleSubmit}>
        <input
          type="password"
          placeholder="Parola"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoFocus
        />
        <button type="submit" disabled={submitting || !password}>
          {submitting ? 'Kontrol ediliyor...' : 'Giriş'}
        </button>
      </form>
      <ErrorBlock message={error} />
    </section>
  )
}

function ServiceLogs({ password, service }) {
  const [logs, setLogs] = useState(null)
  const [error, setError] = useState(null)

  function load() {
    setError(null)
    getAdminServiceLogs(password, service, 200)
      .then(setLogs)
      .catch((e) => setError(e.message))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [service])

  return (
    <div className="card" style={{ marginTop: '0.75rem' }}>
      <div className="card-header">
        <h2 style={{ fontSize: '0.95rem' }}>
          {service} — son {logs?.lines?.length ?? 0} satır
          {logs && (
            <span className={`badge ${logs.error_count > 0 ? 'badge-bad' : 'badge-ok'}`} style={{ marginLeft: '0.5rem' }}>
              {logs.error_count} hata izi
            </span>
          )}
        </h2>
        <button onClick={load}>Yenile</button>
      </div>
      <ErrorBlock message={error} />
      {!logs && !error ? (
        <Loading />
      ) : (
        logs && (
          <pre className="log-viewer">
            {logs.lines.length ? logs.lines.join('\n') : 'Log bulunamadı.'}
          </pre>
        )
      )}
    </div>
  )
}

export default function AdminPage() {
  const [password, setPassword] = useState(() => sessionStorage.getItem(STORAGE_KEY) || '')
  const [loggedIn, setLoggedIn] = useState(false)
  const [loginError, setLoginError] = useState(null)
  const [loginSubmitting, setLoginSubmitting] = useState(false)

  const [services, setServices] = useState(null)
  const [servicesError, setServicesError] = useState(null)
  const [restarting, setRestarting] = useState(null)
  const [openLogs, setOpenLogs] = useState(null)
  const [showTrDomains, setShowTrDomains] = useState(false)

  function tryLogin(pw) {
    setLoginSubmitting(true)
    setLoginError(null)
    adminLogin(pw)
      .then(() => {
        sessionStorage.setItem(STORAGE_KEY, pw)
        setPassword(pw)
        setLoggedIn(true)
      })
      .catch((e) => setLoginError(e.message))
      .finally(() => setLoginSubmitting(false))
  }

  function loadServices(pw) {
    getAdminServices(pw)
      .then((data) => {
        setServices(data.services)
        setServicesError(null)
      })
      .catch((e) => {
        if (e.message.includes('401')) {
          sessionStorage.removeItem(STORAGE_KEY)
          setLoggedIn(false)
        } else {
          setServicesError(e.message)
        }
      })
  }

  useEffect(() => {
    if (password) {
      tryLogin(password)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!loggedIn) return
    loadServices(password)
    const interval = setInterval(() => loadServices(password), 15000)
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loggedIn])

  function handleLogout() {
    sessionStorage.removeItem(STORAGE_KEY)
    setLoggedIn(false)
    setServices(null)
    setOpenLogs(null)
  }

  function handleRestart(service) {
    if (!window.confirm(`"${service}" servisi yeniden başlatılsın mı?`)) return
    setRestarting(service)
    restartAdminService(password, service)
      .then(() => new Promise((resolve) => setTimeout(resolve, 1500)))
      .then(() => loadServices(password))
      .catch((e) => setServicesError(e.message))
      .finally(() => setRestarting(null))
  }

  if (!loggedIn) {
    return <LoginForm onSubmit={tryLogin} submitting={loginSubmitting} error={loginError} />
  }

  return (
    <div>
      <section className="card">
        <div className="card-header">
          <h2>Servis Durumu</h2>
          <span>
            <button onClick={() => setShowTrDomains(true)}>Türkiye Domain Taraması</button>{' '}
            <button onClick={handleLogout}>Çıkış</button>
          </span>
        </div>
        <ErrorBlock message={servicesError} />
        {!services ? (
          <Loading />
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Servis</th>
                  <th>Durum</th>
                  <th>Sağlık</th>
                  <th>Başladığı An</th>
                  <th>Restart Sayısı</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {services.map((s) => (
                  <tr key={s.container_name}>
                    <td className="mono">{s.service}</td>
                    <td>
                      <StatusBadge status={s.status} />
                    </td>
                    <td className="muted">{s.health || '-'}</td>
                    <td>{formatDate(s.started_at)}</td>
                    <td>{s.restart_count}</td>
                    <td>
                      <button onClick={() => setOpenLogs(openLogs === s.service ? null : s.service)}>
                        {openLogs === s.service ? 'Logları Gizle' : 'Loglar'}
                      </button>{' '}
                      <button onClick={() => handleRestart(s.service)} disabled={restarting === s.service}>
                        {restarting === s.service ? 'Başlatılıyor...' : 'Yeniden Başlat'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {openLogs && <ServiceLogs password={password} service={openLogs} />}

      <JobStatusPanel />

      {showTrDomains && <TrDomainsModal onClose={() => setShowTrDomains(false)} />}
    </div>
  )
}
