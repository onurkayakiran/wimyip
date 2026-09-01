import { Fragment, useEffect, useMemo, useState } from 'react'
import { createMonitor, deleteMonitor, getMonitor, listMonitors } from '../api'
import { formatDate } from '../components/HistoryTable'
import { ErrorBlock, Loading } from '../components/StatusBlock'
import useAuth from '../hooks/useAuth'

const CHECK_LABELS = { http: 'HTTP', https: 'HTTPS', ping: 'PING' }
const STATUS_LABELS = { up: 'Çalışıyor', down: 'Kesintide', unknown: 'Bilinmiyor' }
const REFRESH_MS = 15000

function formatDuration(sinceIso) {
  if (!sinceIso) return null
  const ms = Date.now() - new Date(sinceIso).getTime()
  if (ms < 0) return null
  const totalMinutes = Math.floor(ms / 60000)
  const days = Math.floor(totalMinutes / 1440)
  const hours = Math.floor((totalMinutes % 1440) / 60)
  const minutes = totalMinutes % 60
  if (days > 0) return `${days} gün, ${hours} sa`
  if (hours > 0) return `${hours} sa, ${minutes} dk`
  return `${minutes} dk`
}

function StatusIcon({ status }) {
  const glyph = status === 'up' ? '✓' : status === 'down' ? '!' : '?'
  return <span className={`monitor-status-icon status-${status}`}>{glyph}</span>
}

function UptimeBars({ results }) {
  const bars = results && results.length ? results : []
  return (
    <div className="uptime-bars">
      {bars.length === 0 && <span className="muted" style={{ fontSize: '0.8em' }}>Henüz veri yok</span>}
      {bars.map((ok, i) => (
        <span key={i} className={`uptime-bar ${ok ? 'bar-ok' : 'bar-bad'}`} />
      ))}
    </div>
  )
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

function NewMonitorForm({ token, onCreated, onClose }) {
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
        onCreated()
        onClose()
      })
      .catch((err) => setError(err.message))
      .finally(() => setSubmitting(false))
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="card-header">
          <h2>Yeni Monitör</h2>
          <button onClick={onClose}>Kapat</button>
        </div>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <input
            type="text"
            placeholder="Domain veya IP (örn. example.com)"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            autoFocus
          />
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            {Object.keys(CHECK_LABELS).map((type) => (
              <label key={type} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                <input type="checkbox" checked={checks[type]} onChange={() => toggleCheck(type)} />
                {CHECK_LABELS[type]}
              </label>
            ))}
          </div>
          <label className="muted" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            Kontrol sıklığı:
            <input
              type="number"
              min={60}
              step={30}
              value={interval}
              onChange={(e) => setIntervalValue(e.target.value)}
              style={{ width: '90px' }}
            />
            sn
          </label>
          <button type="submit" disabled={submitting || !target.trim() || !Object.values(checks).some(Boolean)}>
            {submitting ? 'Ekleniyor...' : 'Monitör Ekle'}
          </button>
          <ErrorBlock message={error} />
        </form>
      </div>
    </div>
  )
}

export default function MonitorsPage() {
  const { token, isAuthenticated, logout } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [search, setSearch] = useState('')
  const [downFirst, setDownFirst] = useState(false)
  const [expandedRowId, setExpandedRowId] = useState(null)
  const [openMenuId, setOpenMenuId] = useState(null)
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

  // Her (monitor, check tipi) kombinasyonunu ayrı bir satıra düzleştiriyoruz.
  const rows = useMemo(() => {
    const monitors = data?.monitors || []
    const flat = monitors.flatMap((m) =>
      (m.checks_detail || []).map((c) => ({
        rowId: `${m.id}:${c.type}`,
        monitorId: m.id,
        target: m.target,
        interval_seconds: m.interval_seconds,
        type: c.type,
        status: c.status,
        status_since: c.status_since,
        uptime_pct: c.uptime_pct,
        recent_results: c.recent_results,
      })),
    )
    const filtered = search.trim()
      ? flat.filter((r) => r.target.toLowerCase().includes(search.trim().toLowerCase()))
      : flat
    if (!downFirst) return filtered
    const rank = { down: 0, unknown: 1, up: 2 }
    return [...filtered].sort((a, b) => (rank[a.status] ?? 1) - (rank[b.status] ?? 1))
  }, [data, search, downFirst])

  if (!isAuthenticated) {
    return (
      <section className="card">
        <p>Monitörlerinizi görmek için giriş yapmalısınız.</p>
      </section>
    )
  }

  function handleDelete(row) {
    if (!window.confirm(`"${row.target}" monitörü (tüm check'leriyle birlikte) silinsin mi?`)) return
    setOpenMenuId(null)
    setDeleting(row.monitorId)
    deleteMonitor(token, row.monitorId)
      .then(load)
      .catch((e) => setError(e.message))
      .finally(() => setDeleting(null))
  }

  return (
    <>
      <div className="card-header">
        <h1 style={{ fontSize: '1.4rem', margin: 0 }}>
          Monitörler<span style={{ color: '#4f7cff' }}>.</span>
        </h1>
        <span>
          <button onClick={() => setShowAddForm(true)}>+ Yeni Monitör</button>{' '}
          <button onClick={logout}>Çıkış</button>
        </span>
      </div>

      <section className="card">
        <div className="monitors-toolbar">
          <input
            type="text"
            placeholder="Hedefe göre ara..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button onClick={() => setDownFirst((v) => !v)}>
            {downFirst ? '✓ Önce Kesintide Olanlar' : 'Sırala: Önce Kesintide Olanlar'}
          </button>
        </div>

        <ErrorBlock message={error} />

        {!data ? (
          <Loading />
        ) : (
          <div className="monitor-list">
            {rows.length === 0 && <p className="muted">Henüz monitör eklemediniz.</p>}
            {rows.map((row) => {
              const duration = formatDuration(row.status_since)
              return (
                <Fragment key={row.rowId}>
                  <div
                    className="monitor-row"
                    onClick={() => setExpandedRowId(expandedRowId === row.rowId ? null : row.rowId)}
                  >
                    <StatusIcon status={row.status} />
                    <div className="monitor-row-main">
                      <div className="monitor-row-title">
                        <span className="mono">{row.target}</span>
                        <span className="badge">{CHECK_LABELS[row.type]}</span>
                      </div>
                      <div className="muted monitor-row-sub">
                        {STATUS_LABELS[row.status]}
                        {duration ? ` — ${duration}` : ''}
                      </div>
                    </div>
                    <div className="muted monitor-row-interval">↻ {row.interval_seconds} sn</div>
                    <UptimeBars results={row.recent_results} />
                    <div className="monitor-row-pct">
                      {row.uptime_pct != null ? `${row.uptime_pct}%` : '-'}
                    </div>
                    <div className="monitor-row-menu" onClick={(e) => e.stopPropagation()}>
                      <button onClick={() => setOpenMenuId(openMenuId === row.rowId ? null : row.rowId)}>
                        ⋯
                      </button>
                      {openMenuId === row.rowId && (
                        <div className="dropdown-menu">
                          <button onClick={() => handleDelete(row)} disabled={deleting === row.monitorId}>
                            {deleting === row.monitorId ? 'Siliniyor...' : 'Sil'}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                  {expandedRowId === row.rowId && (
                    <div className="monitor-row-detail">
                      <MonitorDetail token={token} monitorId={row.monitorId} />
                    </div>
                  )}
                </Fragment>
              )
            })}
          </div>
        )}
      </section>

      {showAddForm && <NewMonitorForm token={token} onCreated={load} onClose={() => setShowAddForm(false)} />}
    </>
  )
}
