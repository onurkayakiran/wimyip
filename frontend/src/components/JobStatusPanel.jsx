import { useEffect, useState } from 'react'
import { getStatus } from '../api'
import { Loading } from './StatusBlock'

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

export default function JobStatusPanel({ refreshMs = 20000 }) {
  const [status, setStatus] = useState(null)

  function load() {
    getStatus()
      .then(setStatus)
      .catch(() => {})
  }

  useEffect(() => {
    load()
    const interval = setInterval(load, refreshMs)
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <section className="card">
      <div className="card-header">
        <h2>Arka Plan Görevleri</h2>
        {status && (
          <span className={status.healthy_count === status.total_count ? 'badge badge-ok' : 'badge badge-bad'}>
            {status.healthy_count}/{status.total_count} sağlıklı
          </span>
        )}
      </div>
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
                  <td className="mono">{job.job}</td>
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
  )
}
