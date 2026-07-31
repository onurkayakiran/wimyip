import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getMyIp, getStats } from '../api'
import JobStatusPanel from '../components/JobStatusPanel'
import { ErrorBlock, Loading } from '../components/StatusBlock'

export default function Home() {
  const [stats, setStats] = useState(null)
  const [myIp, setMyIp] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getStats().then(setStats).catch((e) => setError(e.message))
    getMyIp().then((r) => setMyIp(r.ip)).catch(() => {})
  }, [])

  return (
    <div>
      {myIp && (
        <Link to={`/ip/${myIp}`} className="my-ip-banner">
          <span className="muted">IP Adresiniz</span>
          <span className="my-ip-value mono">{myIp}</span>
        </Link>
      )}

      <section className="stats">
        {stats ? (
          <>
            <div className="stat">
              <span>{stats.prefixes.toLocaleString()}</span>IP Bloğu
            </div>
            <div className="stat">
              <span>{stats.asns.toLocaleString()}</span>ASN
            </div>
            <div className="stat">
              <span>{stats.domains.toLocaleString()}</span>Domain
            </div>
          </>
        ) : (
          <Loading />
        )}
      </section>

      <ErrorBlock message={error} />

      <JobStatusPanel />

      <section className="card">
        <h2>Hızlı Bağlantılar</h2>
        <p>
          <Link to="/ip/8.8.8.8">Örnek IP sorgusu</Link> ·{' '}
          <Link to="/asn/15169">Örnek ASN (Google)</Link> ·{' '}
          <Link to="/domain/google.com">Örnek domain</Link>
        </p>
      </section>

      <footer className="site-footer">
        © {new Date().getFullYear()} wimyip.net - What Is My Ip
      </footer>
    </div>
  )
}
