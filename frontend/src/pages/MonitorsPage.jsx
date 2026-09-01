import { Fragment, useEffect, useState } from 'react'
import { createMonitor, deleteMonitor, getMonitor, listMonitors } from '../api'
import { formatDate } from '../components/HistoryTable'
import { ErrorBlock, Loading } from '../components/StatusBlock'
import useAuth from '../hooks/useAuth'

const CHECK_LABELS = { http: 'HTTP', https: 'HTTPS', ping: 'Ping' }
const REFRESH_MS = 15000

function StatusDot({ status }) {
  const cls = status === 'up' ? 'status-ok' : status === 'down' ? 'status-bad' : ''
  return <span className={`status-dot ${cls}`} title={status || 'unknown'} />
}

function MonitorDetail({ token, monitorId }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getMonitor(token, monitorId)
      .then(setData)
      .catch((e) => setError(e.message))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [monitorId])

  if (error) return <ErrorBlock message={error} />
  if (!data) return <Loading />

  const results = data.results || []

  return (
    <div className="table-scroll" style={{ marginTop: '0.5rem' }}>
      <table>
        <thead>
          <tr>
            <th>Zaman</th>
            <th>Check</th>
            <th>Durum</th>
            <th>Yanıt Süresi</th>
            <th>Hata</th>
          </tr>
        </thead>
        <tbody>
          {results.length === 0 && (
            <tr>
              <td colSpan={5} className="muted">
                Henüz sonuç yok.
              </td>
            </tr>
          )}
          {results.map((r) => (
            <tr key={r.id}>
              <td className="muted">{formatDate(r.checked_at)}</td>
              <td className="mono">{CHECK_LABELS[r.check_type] || r.check_type}</td>
              <td>
                <span className={`badge ${r.ok ? 'badge-ok' : 'badge-bad'}`}>{r.ok ? 'OK' : 'Başarısız'}</span>
              </td>
              <td className="mono">{r.response_time_ms != null ? `${r.response_time_ms} ms` : '-'}</td>
              <td className="muted">{r.error || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function NewMonitorForm({ token, onCreated }) {
  const [target, setTarget] = useState('')
  const [checks, setChecks] = useState({ http: true, https: false, ping: false })
  const [interval, setIntervalValue] = useState(300)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  function toggleCheck(type) {
    setChecks((prev) => ({ ...prev, [type]: !prev[type] }))
  }

  function handleSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    createMonitor(token, { target: target.trim(), checks, interval_seconds: Number(interval) })
      .then(() => {
        setTarget('')
        onCreated()
      })
      .catch((err) => setError(err.message))
      .finally(() => setSubmitting(false))
  }

  return (
    <form className="search" onSubmit={handleSubmit} style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
      <input
        type="text"
        placeholder="Domain veya IP (örn. example.com)"
        value={target}
        onChange={(e) => setTarget(e.target.value)}
      />
      {Object.keys(CHECK_LABELS).map((type) => (
        <label key={type} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
          <input type="checkbox" checked={checks[type]} onChange={() => toggleCheck(type)} />
          {CHECK_LABELS[type]}
        </label>
      ))}
      <input
        type="number"
        min={60}
        step={30}
        value={interval}
        onChange={(e) => setIntervalValue(e.target.value)}
        style={{ width: '90px' }}
        title="Kontrol sıklığı (saniye)"
      />
      <span className="muted" style={{ fontSize: '0.8em' }}>
        sn
      </span>
      <button type="submit" disabled={submitting || !target.trim() || !Object.values(checks).some(Boolean)}>
        {submitting ? 'Ekleniyor...' : 'Monitor Ekle'}
      </button>
      <ErrorBlock message={error} />
    </form>
  )
}

export default function MonitorsPage() {
  const { token, isAuthenticated, logout } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [openId, setOpenId] = useState(null)
  const [deleting, setDeleting] = useState(null)

  function load() {
    listMonitors(token)
      .then(setData)
      .catch((e) => setError(e.message))
  }

  useEffect(() => {
    if (!isAuthenticated) return
    load()
    const interval = setInterval(load, REFRESH_MS)
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated])

  if (!isAuthenticated) {
    return (
      <section className="card">
        <p>Monitörlerinizi görmek için giriş yapmalısınız.</p>
      </section>
    )
  }

  function handleDelete(monitor) {
    if (!window.confirm(`"${monitor.target}" monitörü silinsin mi?`)) return
    setDeleting(monitor.id)
    deleteMonitor(token, monitor.id)
      .then(load)
      .catch((e) => setError(e.message))
      .finally(() => setDeleting(null))
  }

  const monitors = data?.monitors || []

  return (
    <>
      <section className="card">
        <div className="card-header">
          <h2>Yeni Monitör</h2>
        </div>
        <NewMonitorForm token={token} onCreated={load} />
      </section>

      <section className="card">
        <div className="card-header">
          <h2>Monitörlerim</h2>
          <button onClick={logout}>Çıkış</button>
        </div>
        <ErrorBlock message={error} />
        {!data ? (
          <Loading />
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th></th>
                  <th>Hedef</th>
                  <th>Check'ler</th>
                  <th>Sıklık</th>
                  <th>Son Kontrol</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {monitors.length === 0 && (
                  <tr>
                    <td colSpan={6} className="muted">
                      Henüz monitör eklemediniz.
                    </td>
                  </tr>
                )}
                {monitors.map((m) => (
                  <Fragment key={m.id}>
                    <tr>
                      <td>
                        <button onClick={() => setOpenId(openId === m.id ? null : m.id)}>
                          {openId === m.id ? '▾' : '▸'}
                        </button>
                      </td>
                      <td className="mono">{m.target}</td>
                      <td>
                        {Object.keys(CHECK_LABELS)
                          .filter((t) => m.checks?.[t])
                          .map((t) => (
                            <span key={t} style={{ marginRight: '0.5rem' }}>
                              <StatusDot status={m.current_status?.[t]} /> {CHECK_LABELS[t]}
                            </span>
                          ))}
                      </td>
                      <td className="muted">{m.interval_seconds} sn</td>
                      <td className="muted">{m.last_checked_at ? formatDate(m.last_checked_at) : 'Henüz yok'}</td>
                      <td>
                        <button onClick={() => handleDelete(m)} disabled={deleting === m.id}>
                          {deleting === m.id ? 'Siliniyor...' : 'Sil'}
                        </button>
                      </td>
                    </tr>
                    {openId === m.id && (
                      <tr>
                        <td colSpan={6}>
                          <MonitorDetail token={token} monitorId={m.id} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  )
}
