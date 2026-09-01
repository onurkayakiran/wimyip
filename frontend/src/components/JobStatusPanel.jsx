import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getStatus } from '../api'
import { Loading } from './StatusBlock'

function StatusDot({ healthy }) {
  return <span className={`status-dot ${healthy ? 'status-ok' : 'status-bad'}`} />
}

export default function JobStatusPanel({ refreshMs = 20000 }) {
  const { t } = useTranslation()
  const [status, setStatus] = useState(null)

  function formatAge(seconds) {
    if (seconds == null) return '-'
    if (seconds < 60) return t('jobStatus.seconds_ago', { count: Math.round(seconds) })
    if (seconds < 3600) return t('jobStatus.minutes_ago', { count: Math.round(seconds / 60) })
    return t('jobStatus.hours_ago', { count: Math.round(seconds / 3600) })
  }

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
        <h2>{t('jobStatus.title')}</h2>
        {status && (
          <span className={status.healthy_count === status.total_count ? 'badge badge-ok' : 'badge badge-bad'}>
            {t('jobStatus.healthy', { healthy: status.healthy_count, total: status.total_count })}
          </span>
        )}
      </div>
      {status ? (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th></th>
                <th>{t('jobStatus.task')}</th>
                <th>{t('jobStatus.cursor')}</th>
                <th>{t('jobStatus.last_run')}</th>
                <th>{t('jobStatus.last_batch')}</th>
                <th>{t('jobStatus.note')}</th>
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
                      ? t('jobStatus.note_error', { error: job.last_error })
                      : job.stale
                        ? t('jobStatus.note_stale')
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
