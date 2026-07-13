import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getStats, getStatus } from '../api'
import { formatDate } from '../components/HistoryTable'
import { ErrorBlock, Loading } from '../components/StatusBlock'

function StatusDot({ healthy }) {
  return (
    <span className={`status-dot ${healthy ? 'status-ok' : 'status-bad'}`} title={healthy ? 'Sağlıklı' : 'Sorun var'} />
  )
}

function formatAge(seconds) {
  if (seconds == null) return '-'
  if (seconds < 60) return `${Math.round(seconds)} sn önce`
  if (seconds < 3600) return `${Math.round(seconds / 60)} dk önce`
  return `${Math.round(seconds / 3600)} sa önce`
}

export default function Home() {
  const [stats, setStats] = useState(null)
  const [status, setStatus] = useState(null)
  const [error, setError] = useState(null)

  function loadStatus() {
    getStatus()
      .then(setStatus)
      .catch(() => {})
  }

  useEffect(() => {
    getStats().then(setStats).catch((e) => setError(e.message))
    loadStatus()
    const interval = setInterval(loadStatus, 20000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div>
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

      <section className="card">
        <div className="card-header">
          <h2>Arka Plan Görevleri</h2>
          {status && (
            <span className={status.healthy_count === status.total_count ? 'badge badge-ok' : 'badge badge-bad'}>
              {status.healthy_count}/{status.total_count} sağlıklı
            </span>
          )}
        </div>
        <p className="muted">
          Sistem sürekli arka planda RIR/RDAP/BGP/PeeringDB/CT-log/PTR/DNS
          taramalarını yürütür; her görev kaldığı yerden devam eder. Bu panel
          20 saniyede bir kendini yeniler — bir görev beklenenden uzun süredir
          güncellenmemişse veya son turunda çoğunlukla hata aldıysa kırmızı
          işaretlenir.
        </p>
        {status ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th></th>
                  <th>Görev</th>
                  <th>Cursor</th>
                  <th>Son Çalışma</th>
                  <th>Son Batch (başarılı/başarısız)</th>
                  <th>Not</th>
                </tr>
              </thead>
              <tbody>
                {status.jobs.map((job) => (
                  <tr key={job.job}>
                    <td>
                      <StatusDot healthy={job.healthy} />
                    </td>
                    <td>{job.job}</td>
                    <td className="mono">{String(job.cursor ?? '-')}</td>
                    <td>{formatAge(job.age_seconds)}</td>
                    <td>
                      {job.last_batch_processed ?? '-'} / {job.last_batch_failed ?? 0}
                    </td>
                    <td className="muted">
                      {job.last_error
                        ? `Hata: ${job.last_error}`
                        : job.stale
                          ? 'Beklenenden uzun süredir güncellenmedi'
                          : ''}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Loading />
        )}
      </section>

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
