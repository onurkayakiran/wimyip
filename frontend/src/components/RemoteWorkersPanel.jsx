import { useEffect, useState } from 'react'
import { Trans, useTranslation } from 'react-i18next'
import {
  createRemoteWorkerToken,
  getRemoteWorkerStatus,
  getRemoteWorkerTokens,
  revokeRemoteWorkerToken,
} from '../api'
import { ErrorBlock, Loading } from './StatusBlock'

// remote-api'de uygulanmis kuyruklar (bkz. remote-api/app/registry.py) -
// yeni bir kuyruk eklendiginde buraya da eklenmeli.
const AVAILABLE_QUEUES = ['ptr_sweep', 'dns_history', 'dns_history_apex', 'port_scan']

function StatusDot({ healthy }) {
  const { t } = useTranslation()
  return (
    <span
      className={`status-dot ${healthy ? 'status-ok' : 'status-bad'}`}
      title={healthy ? t('remoteWorkers.healthy') : t('remoteWorkers.unhealthy')}
    />
  )
}

function formatAge(value, t) {
  if (!value) return '-'
  const seconds = (Date.now() - new Date(value).getTime()) / 1000
  if (seconds < 60) return t('jobStatus.seconds_ago', { count: Math.round(seconds) })
  if (seconds < 3600) return t('jobStatus.minutes_ago', { count: Math.round(seconds / 60) })
  return t('jobStatus.hours_ago', { count: Math.round(seconds / 3600) })
}

function isHealthy(lastSeenAt) {
  if (!lastSeenAt) return false
  return Date.now() - new Date(lastSeenAt).getTime() < 120000
}

function CreateTokenForm({ password, onCreated }) {
  const { t } = useTranslation()
  const [label, setLabel] = useState('')
  const [queues, setQueues] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  function toggleQueue(q) {
    setQueues((prev) => (prev.includes(q) ? prev.filter((x) => x !== q) : [...prev, q]))
  }

  function handleSubmit(e) {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    createRemoteWorkerToken(password, label, queues)
      .then((result) => {
        onCreated(result)
        setLabel('')
        setQueues([])
      })
      .catch((err) => setError(err.message))
      .finally(() => setSubmitting(false))
  }

  return (
    <form className="search" onSubmit={handleSubmit} style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
      <input
        type="text"
        placeholder={t('remoteWorkers.location_label_placeholder')}
        value={label}
        onChange={(e) => setLabel(e.target.value)}
      />
      {AVAILABLE_QUEUES.map((q) => (
        <label key={q} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
          <input type="checkbox" checked={queues.includes(q)} onChange={() => toggleQueue(q)} />
          {q}
        </label>
      ))}
      <button type="submit" disabled={submitting || !label || queues.length === 0}>
        {submitting ? t('remoteWorkers.creating') : t('remoteWorkers.create_token')}
      </button>
      <ErrorBlock message={error} />
    </form>
  )
}

export default function RemoteWorkersPanel({ password, refreshMs = 20000 }) {
  const { t } = useTranslation()
  const [status, setStatus] = useState(null)
  const [tokens, setTokens] = useState(null)
  const [error, setError] = useState(null)
  const [newToken, setNewToken] = useState(null)
  const [revoking, setRevoking] = useState(null)

  function load() {
    Promise.all([getRemoteWorkerStatus(password), getRemoteWorkerTokens(password)])
      .then(([statusRes, tokensRes]) => {
        setStatus(statusRes.workers)
        setTokens(tokensRes.tokens)
        setError(null)
      })
      .catch((e) => setError(e.message))
  }

  useEffect(() => {
    load()
    const interval = setInterval(load, refreshMs)
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function handleRevoke(token) {
    if (!window.confirm(t('remoteWorkers.confirm_revoke', { label: token.label }))) return
    setRevoking(token.id)
    revokeRemoteWorkerToken(password, token.id)
      .then(load)
      .catch((e) => setError(e.message))
      .finally(() => setRevoking(null))
  }

  return (
    <section className="card">
      <div className="card-header">
        <h2>{t('remoteWorkers.title')}</h2>
      </div>
      <ErrorBlock message={error} />

      {newToken && (
        <div className="card" style={{ marginBottom: '0.75rem', border: '1px solid var(--accent, #888)' }}>
          <p>
            <Trans i18nKey="remoteWorkers.token_created_notice" values={{ label: newToken.label }} components={{ bold: <strong /> }} />
          </p>
          <pre className="log-viewer" style={{ userSelect: 'all' }}>
            {newToken.token}
          </pre>
          <button onClick={() => setNewToken(null)}>{t('common.close')}</button>
        </div>
      )}

      {!status || !tokens ? (
        <Loading />
      ) : (
        <>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th></th>
                  <th>{t('remoteWorkers.label')}</th>
                  <th>{t('remoteWorkers.queue')}</th>
                  <th>{t('remoteWorkers.last_seen')}</th>
                  <th>{t('remoteWorkers.last_batch_found')}</th>
                  <th>{t('remoteWorkers.total_claim_submit')}</th>
                </tr>
              </thead>
              <tbody>
                {status.length === 0 && (
                  <tr>
                    <td colSpan={6} className="muted">
                      {t('remoteWorkers.no_workers_yet')}
                    </td>
                  </tr>
                )}
                {status.map((w) => (
                  <tr key={w.id}>
                    <td>
                      <StatusDot healthy={isHealthy(w.last_seen_at)} />
                    </td>
                    <td className="mono">{w.label}</td>
                    <td className="mono">{w.queue}</td>
                    <td>{formatAge(w.last_seen_at, t)}</td>
                    <td>{w.last_batch_found ?? '-'}</td>
                    <td>
                      {w.total_claimed ?? 0} / {w.total_submitted ?? 0}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h3 style={{ marginTop: '1rem' }}>{t('remoteWorkers.tokens')}</h3>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>{t('remoteWorkers.label')}</th>
                  <th>{t('remoteWorkers.allowed_queues')}</th>
                  <th>{t('remoteWorkers.created')}</th>
                  <th>{t('remoteWorkers.status')}</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {tokens.length === 0 && (
                  <tr>
                    <td colSpan={5} className="muted">
                      {t('remoteWorkers.no_tokens_yet')}
                    </td>
                  </tr>
                )}
                {tokens.map((tok) => (
                  <tr key={tok.id}>
                    <td className="mono">{tok.label}</td>
                    <td className="mono">{(tok.queues || []).join(', ')}</td>
                    <td>{formatAge(tok.created_at, t)}</td>
                    <td>
                      <span className={`badge ${tok.revoked_at ? 'badge-bad' : 'badge-ok'}`}>
                        {tok.revoked_at ? t('remoteWorkers.revoked') : t('remoteWorkers.active')}
                      </span>
                    </td>
                    <td>
                      {!tok.revoked_at && (
                        <button onClick={() => handleRevoke(tok)} disabled={revoking === tok.id}>
                          {revoking === tok.id ? t('remoteWorkers.revoking') : t('remoteWorkers.revoke')}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h3 style={{ marginTop: '1rem' }}>{t('remoteWorkers.new_token')}</h3>
          <CreateTokenForm password={password} onCreated={(result) => { setNewToken(result); load() }} />
        </>
      )}
    </section>
  )
}
