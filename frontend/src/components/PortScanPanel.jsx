import { Fragment, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getScanJob, listPrefixes, listScanJobs, resetScanJob } from '../api'
import PortScanTriggerModal from './PortScanTriggerModal'
import { ErrorBlock, Loading } from './StatusBlock'

const PREFIX_LIMIT = 10
const JOBS_LIMIT = 20
const ACTIVE_REFRESH_MS = 4000
const IDLE_REFRESH_MS = 20000

function StatusBadge({ status }) {
  const { t } = useTranslation()
  const STATUS_LABELS = {
    pending: t('scans.status_pending'),
    claimed: t('scans.status_claimed'),
    running: t('scans.status_running'),
    completed: t('scans.status_completed'),
    failed: t('scans.status_failed'),
  }
  const ok = status === 'completed'
  const bad = status === 'failed'
  const cls = ok ? 'badge-ok' : bad ? 'badge-bad' : 'badge'
  return <span className={`badge ${cls}`}>{STATUS_LABELS[status] || status}</span>
}

function ProgressBar({ scanned, total }) {
  const scannedCount = scanned ?? 0
  const pct = total > 0 ? Math.min(100, Math.round((scannedCount / total) * 100)) : 0
  return (
    <div className="progress-bar-wrap">
      <div className="progress-bar">
        <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="muted" style={{ fontSize: '0.8em' }}>
        {scanned ?? 0}/{total ?? 0} ({pct}%)
      </span>
    </div>
  )
}

function JobDetail({ token, jobId }) {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  function load() {
    getScanJob(token, jobId)
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
            <th>{t('scans.detail_ip')}</th>
            <th>{t('scans.detail_open_ports')}</th>
            <th>{t('scans.detail_services')}</th>
          </tr>
        </thead>
        <tbody>
          {withPorts.length === 0 && (
            <tr>
              <td colSpan={3} className="muted">
                {results.length === 0 ? t('scans.no_detail_results_yet') : t('scans.no_open_ports_yet')}
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

function JobsTable({ token }) {
  const { t } = useTranslation()
  const [offset, setOffset] = useState(0)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [openJobId, setOpenJobId] = useState(null)
  const [resetting, setResetting] = useState(null)
  const timerRef = useRef(null)

  function load() {
    listScanJobs(token, { limit: JOBS_LIMIT, offset })
      .then((res) => {
        setData(res)
        setError(null)
      })
      .catch((e) => setError(e.message))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [offset])

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
    if (!window.confirm(t('scans.confirm_reset', { target: job.target }))) return
    setResetting(job.id)
    resetScanJob(token, job.id)
      .then(load)
      .catch((e) => setError(e.message))
      .finally(() => setResetting(null))
  }

  const items = data?.items || []
  const total = data?.total ?? 0
  const hasPrev = offset > 0
  const hasNext = offset + JOBS_LIMIT < total

  return (
    <>
      <ErrorBlock message={error} />
      {!data ? (
        <Loading />
      ) : (
        <>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th></th>
                  <th>{t('scans.target')}</th>
                  <th>{t('scans.status')}</th>
                  <th>{t('scans.progress')}</th>
                  <th>{t('scans.current')}</th>
                  <th>{t('scans.result')}</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {items.length === 0 && (
                  <tr>
                    <td colSpan={7} className="muted">
                      {t('scans.no_scans_yet')}
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
                          ? t('scans.result_open_ports', { count: job.result_summary.hosts_with_open_ports ?? 0 })
                          : '-'}
                      </td>
                      <td>
                        {(job.status === 'claimed' || job.status === 'running') && (
                          <button onClick={() => handleReset(job)} disabled={resetting === job.id}>
                            {resetting === job.id ? t('scans.resetting') : t('scans.reset')}
                          </button>
                        )}
                      </td>
                    </tr>
                    {openJobId === job.id && (
                      <tr>
                        <td colSpan={7}>
                          <JobDetail token={token} jobId={job.id} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card-header">
            <span className="muted">
              {total > 0 ? t('common.results_range', { from: offset + 1, to: Math.min(offset + JOBS_LIMIT, total), total }) : t('common.results_count', { count: 0 })}
            </span>
            <span>
              <button onClick={() => setOffset(offset - JOBS_LIMIT)} disabled={!hasPrev}>
                {t('common.previous')}
              </button>{' '}
              <button onClick={() => setOffset(offset + JOBS_LIMIT)} disabled={!hasNext}>
                {t('common.next')}
              </button>
            </span>
          </div>
        </>
      )}
    </>
  )
}

export default function PortScanPanel({ token }) {
  const { t } = useTranslation()
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
    <>
      <div className="scans-columns">
        <section className="card scans-column-new">
          <div className="card-header">
            <h2>{t('scans.new_scan')}</h2>
          </div>

          <form onSubmit={handleQuickScan} className="search">
            <input
              type="text"
              placeholder={t('scans.quick_scan_placeholder')}
              value={quickTarget}
              onChange={(e) => setQuickTarget(e.target.value)}
            />
            <button type="submit" disabled={!quickTarget.trim()}>
              {t('scans.scan')}
            </button>
          </form>
        </section>

        <section className="card scans-column-cidrs">
          <div className="card-header">
            <h2>{t('scans.cidr_list_title')}</h2>
          </div>

          <form onSubmit={handleSubmit} className="search">
            <input
              type="text"
              placeholder={t('scans.subnet_search_placeholder')}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
            />
            <button type="submit" disabled={searching}>
              {searching ? t('scans.searching') : t('scans.search')}
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
                      <th>{t('common_detail.cidr')}</th>
                      <th>{t('common_detail.rir')}</th>
                      <th>{t('common_detail.country')}</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.length === 0 && (
                      <tr>
                        <td colSpan={4} className="muted">
                          {t('scans.no_results')}
                        </td>
                      </tr>
                    )}
                    {items.map((p) => (
                      <tr key={p.cidr}>
                        <td className="mono">{p.cidr}</td>
                        <td className="muted">{p.rir}</td>
                        <td className="muted">{p.country || '-'}</td>
                        <td>
                          <button onClick={() => setScanTarget(p.cidr)}>{t('scans.scan')}</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="card-header">
                <span className="muted">
                  {total > 0 ? t('common.results_range', { from: offset + 1, to: Math.min(offset + PREFIX_LIMIT, total), total }) : t('common.results_count', { count: 0 })}
                </span>
                <span>
                  <button onClick={() => setOffset(offset - PREFIX_LIMIT)} disabled={!hasPrev}>
                    {t('common.previous')}
                  </button>{' '}
                  <button onClick={() => setOffset(offset + PREFIX_LIMIT)} disabled={!hasNext}>
                    {t('common.next')}
                  </button>
                </span>
              </div>
            </>
          )}
        </section>
      </div>

      <section className="card">
        <div className="card-header">
          <h2>{t('scans.scans_list')}</h2>
        </div>
        <JobsTable key={jobsVersion} token={token} />
      </section>

      {scanTarget && (
        <PortScanTriggerModal
          token={token}
          initialTarget={scanTarget}
          onClose={() => setScanTarget(null)}
          onCreated={() => setJobsVersion((v) => v + 1)}
        />
      )}
    </>
  )
}
