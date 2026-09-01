import { Fragment, useEffect, useRef, useState } from 'react'
import { getPortScanJob, listPortScanJobs, listPrefixes, resetPortScanJob } from '../api'
import PortScanTriggerModal from './PortScanTriggerModal'
import { ErrorBlock, Loading } from './StatusBlock'

const PREFIX_LIMIT = 50
const JOBS_LIMIT = 20
const ACTIVE_REFRESH_MS = 4000
const IDLE_REFRESH_MS = 20000

const STATUS_LABELS = {
  pending: 'Bekliyor',
  claimed: 'Alındı',
  running: 'Taranıyor',
  completed: 'Tamamlandı',
  failed: 'Başarısız',
}

function StatusBadge({ status }) {
  const ok = status === 'completed'
  const bad = status === 'failed'
  const cls = ok ? 'badge-ok' : bad ? 'badge-bad' : 'badge'
  return <span className={`badge ${cls}`}>{STATUS_LABELS[status] || status}</span>
}

function ProgressBar({ scanned, total }) {
  const scannedCount = scanned ?? 0
  const pct = total > 0 ? Math.min(100, Math.round((scannedCount / total) * 100)) : 0
  return (
    <div style={{ minWidth: '120px' }}>
      <div style={{ background: 'var(--border, #444)', borderRadius: '4px', height: '8px', overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, background: 'var(--accent, #4a9)', height: '100%' }} />
      </div>
      <span className="muted" style={{ fontSize: '0.8em' }}>
        {scanned ?? 0}/{total ?? 0} ({pct}%)
      </span>
    </div>
  )
}

function JobDetail({ password, jobId }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  function load() {
    getPortScanJob(password, jobId)
      .then((res) => {
        setData(res)
        setError(null)
      })
      .catch((e) => setError(e.message))
  }

  useEffect(() => {
    load()
    const interval = setInterval(load, ACTIVE_REFRESH_MS)
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId])

  if (error) return <ErrorBlock message={error} />
  if (!data) return <Loading />

  const results = data.results || []
  const withPorts = results.filter((r) => (r.open_ports || []).length > 0)

  return (
    <div className="table-scroll" style={{ marginTop: '0.5rem' }}>
      <table>
        <thead>
          <tr>
            <th>IP</th>
            <th>Açık Portlar</th>
            <th>Servisler</th>
          </tr>
        </thead>
        <tbody>
          {withPorts.length === 0 && (
            <tr>
              <td colSpan={3} className="muted">
                {results.length === 0 ? 'Henüz sonuç yok.' : 'Açık port bulunan host yok (şimdiye kadar).'}
              </td>
            </tr>
          )}
          {withPorts.map((r) => (
            <tr key={r.ip}>
              <td className="mono">{r.ip}</td>
              <td className="mono">{(r.open_ports || []).join(', ')}</td>
              <td className="muted">
                {(r.services || [])
                  .map((s) => `${s.port}: ${(s.services || []).join(', ')}${s.http_title ? ` — ${s.http_title}` : ''}`)
                  .join(' | ')}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function JobsTable({ password }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [openJobId, setOpenJobId] = useState(null)
  const [resetting, setResetting] = useState(null)
  const timerRef = useRef(null)

  function load() {
    listPortScanJobs(password, { limit: JOBS_LIMIT })
      .then((res) => {
        setData(res)
        setError(null)
      })
      .catch((e) => setError(e.message))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const items = data?.items || []
    const hasActive = items.some((j) => j.status === 'claimed' || j.status === 'running')
    const ms = hasActive ? ACTIVE_REFRESH_MS : IDLE_REFRESH_MS
    if (timerRef.current) clearInterval(timerRef.current)
    timerRef.current = setInterval(load, ms)
    return () => clearInterval(timerRef.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data])

  function handleReset(job) {
    if (!window.confirm(`"${job.target}" taraması sıfırlanıp tekrar sıraya alınsın mı?`)) return
    setResetting(job.id)
    resetPortScanJob(password, job.id)
      .then(load)
      .catch((e) => setError(e.message))
      .finally(() => setResetting(null))
  }

  const items = data?.items || []

  return (
    <div style={{ marginTop: '1rem' }}>
      <h3>Taramalar</h3>
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
                <th>Durum</th>
                <th>İlerleme</th>
                <th>Şu an</th>
                <th>Sonuç</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {items.length === 0 && (
                <tr>
                  <td colSpan={7} className="muted">
                    Henüz tarama başlatılmadı.
                  </td>
                </tr>
              )}
              {items.map((job) => (
                <Fragment key={job.id}>
                  <tr>
                    <td>
                      <button onClick={() => setOpenJobId(openJobId === job.id ? null : job.id)}>
                        {openJobId === job.id ? '▾' : '▸'}
                      </button>
                    </td>
                    <td className="mono">{job.target}</td>
                    <td>
                      <StatusBadge status={job.status} />
                    </td>
                    <td>
                      <ProgressBar scanned={job.scanned_count} total={job.host_count} />
                    </td>
                    <td className="mono muted">{job.current_ip || '-'}</td>
                    <td className="muted">
                      {job.result_summary
                        ? `${job.result_summary.hosts_with_open_ports ?? 0} açık portlu host`
                        : '-'}
                    </td>
                    <td>
                      {(job.status === 'claimed' || job.status === 'running') && (
                        <button onClick={() => handleReset(job)} disabled={resetting === job.id}>
                          {resetting === job.id ? 'Sıfırlanıyor...' : 'Sıfırla'}
                        </button>
                      )}
                    </td>
                  </tr>
                  {openJobId === job.id && (
                    <tr>
                      <td colSpan={7}>
                        <JobDetail password={password} jobId={job.id} />
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default function PortScanPanel({ password }) {
  const [inputValue, setInputValue] = useState('')
  const [submittedQuery, setSubmittedQuery] = useState('')
  const [offset, setOffset] = useState(0)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [searching, setSearching] = useState(false)
  const requestId = useRef(0)

  const [quickTarget, setQuickTarget] = useState('')
  const [scanTarget, setScanTarget] = useState(null)
  const [jobsVersion, setJobsVersion] = useState(0)

  function load() {
    const id = ++requestId.current
    setSearching(true)
    listPrefixes({ q: submittedQuery, limit: PREFIX_LIMIT, offset })
      .then((res) => {
        if (id !== requestId.current) return
        setData(res)
        setError(null)
      })
      .catch((e) => {
        if (id !== requestId.current) return
        setError(e.message)
      })
      .finally(() => {
        if (id === requestId.current) setSearching(false)
      })
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [submittedQuery, offset])

  function handleSubmit(e) {
    e.preventDefault()
    setOffset(0)
    setSubmittedQuery(inputValue)
  }

  function handleQuickScan(e) {
    e.preventDefault()
    if (!quickTarget.trim()) return
    setScanTarget(quickTarget.trim())
  }

  const total = data?.total ?? 0
  const items = data?.items ?? []
  const hasPrev = offset > 0
  const hasNext = offset + PREFIX_LIMIT < total

  return (
    <section className="card">
      <div className="card-header">
        <h2>IP Subnet Taraması</h2>
      </div>

      <form onSubmit={handleQuickScan} className="search">
        <input
          type="text"
          placeholder="Hızlı Tara: bir IP veya CIDR yazın (örn. 8.8.8.8)"
          value={quickTarget}
          onChange={(e) => setQuickTarget(e.target.value)}
        />
        <button type="submit" disabled={!quickTarget.trim()}>
          Tara
        </button>
      </form>

      <form onSubmit={handleSubmit} className="search" style={{ marginTop: '0.5rem' }}>
        <input
          type="text"
          placeholder="Subnet ara (CIDR alt-dizesi veya tam IP)..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
        />
        <button type="submit" disabled={searching}>
          {searching ? 'Aranıyor...' : 'Ara'}
        </button>
      </form>

      <ErrorBlock message={error} />

      {!data ? (
        <Loading />
      ) : (
        <>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>CIDR</th>
                  <th>RIR</th>
                  <th>Ülke</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {items.length === 0 && (
                  <tr>
                    <td colSpan={4} className="muted">
                      Sonuç bulunamadı.
                    </td>
                  </tr>
                )}
                {items.map((p) => (
                  <tr key={p.cidr}>
                    <td className="mono">{p.cidr}</td>
                    <td className="muted">{p.rir}</td>
                    <td className="muted">{p.country || '-'}</td>
                    <td>
                      <button onClick={() => setScanTarget(p.cidr)}>Tara</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card-header">
            <span className="muted">
              {total > 0 ? `${offset + 1}-${Math.min(offset + PREFIX_LIMIT, total)} / ${total}` : '0 sonuç'}
            </span>
            <span>
              <button onClick={() => setOffset(offset - PREFIX_LIMIT)} disabled={!hasPrev}>
                Önceki
              </button>{' '}
              <button onClick={() => setOffset(offset + PREFIX_LIMIT)} disabled={!hasNext}>
                Sonraki
              </button>
            </span>
          </div>
        </>
      )}

      <JobsTable key={jobsVersion} password={password} />

      {scanTarget && (
        <PortScanTriggerModal
          password={password}
          initialTarget={scanTarget}
          onClose={() => setScanTarget(null)}
          onCreated={() => setJobsVersion((v) => v + 1)}
        />
      )}
    </section>
  )
}
