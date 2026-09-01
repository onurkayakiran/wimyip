import { useEffect, useState } from 'react'
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
  return (
    <span className={`status-dot ${healthy ? 'status-ok' : 'status-bad'}`} title={healthy ? 'Sağlıklı' : 'Sorun var'} />
  )
}

function formatAge(value) {
  if (!value) return '-'
  const seconds = (Date.now() - new Date(value).getTime()) / 1000
  if (seconds < 60) return `${Math.round(seconds)} sn önce`
  if (seconds < 3600) return `${Math.round(seconds / 60)} dk önce`
  return `${Math.round(seconds / 3600)} sa önce`
}

function isHealthy(lastSeenAt) {
  if (!lastSeenAt) return false
  return Date.now() - new Date(lastSeenAt).getTime() < 120000
}

function CreateTokenForm({ password, onCreated }) {
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
        placeholder="Lokasyon etiketi (örn. almanya-vps-1)"
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
        {submitting ? 'Oluşturuluyor...' : 'Token Oluştur'}
      </button>
      <ErrorBlock message={error} />
    </form>
  )
}

export default function RemoteWorkersPanel({ password, refreshMs = 20000 }) {
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
    if (!window.confirm(`"${token.label}" token'ı iptal edilsin mi? Bu, o worker'ın erişimini anında keser.`)) return
    setRevoking(token.id)
    revokeRemoteWorkerToken(password, token.id)
      .then(load)
      .catch((e) => setError(e.message))
      .finally(() => setRevoking(null))
  }

  return (
    <section className="card">
      <div className="card-header">
        <h2>Uzak Workerlar</h2>
      </div>
      <ErrorBlock message={error} />

      {newToken && (
        <div className="card" style={{ marginBottom: '0.75rem', border: '1px solid var(--accent, #888)' }}>
          <p>
            <strong>{newToken.label}</strong> için token oluşturuldu — bu token bir daha gösterilmeyecek, şimdi kopyalayın:
          </p>
          <pre className="log-viewer" style={{ userSelect: 'all' }}>
            {newToken.token}
          </pre>
          <button onClick={() => setNewToken(null)}>Kapat</button>
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
                  <th>Etiket</th>
                  <th>Kuyruk</th>
                  <th>Son Görülme</th>
                  <th>Son Batch (bulundu)</th>
                  <th>Toplam Claim/Submit</th>
                </tr>
              </thead>
              <tbody>
                {status.length === 0 && (
                  <tr>
                    <td colSpan={6} className="muted">
                      Henüz uzak worker görülmedi.
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
                    <td>{formatAge(w.last_seen_at)}</td>
                    <td>{w.last_batch_found ?? '-'}</td>
                    <td>
                      {w.total_claimed ?? 0} / {w.total_submitted ?? 0}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h3 style={{ marginTop: '1rem' }}>Token'lar</h3>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Etiket</th>
                  <th>İzinli Kuyruklar</th>
                  <th>Oluşturulma</th>
                  <th>Durum</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {tokens.length === 0 && (
                  <tr>
                    <td colSpan={5} className="muted">
                      Henüz token oluşturulmadı.
                    </td>
                  </tr>
                )}
                {tokens.map((t) => (
                  <tr key={t.id}>
                    <td className="mono">{t.label}</td>
                    <td className="mono">{(t.queues || []).join(', ')}</td>
                    <td>{formatAge(t.created_at)}</td>
                    <td>
                      <span className={`badge ${t.revoked_at ? 'badge-bad' : 'badge-ok'}`}>
                        {t.revoked_at ? 'İptal edildi' : 'Aktif'}
                      </span>
                    </td>
                    <td>
                      {!t.revoked_at && (
                        <button onClick={() => handleRevoke(t)} disabled={revoking === t.id}>
                          {revoking === t.id ? 'İptal ediliyor...' : 'İptal Et'}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h3 style={{ marginTop: '1rem' }}>Yeni Token</h3>
          <CreateTokenForm password={password} onCreated={(result) => { setNewToken(result); load() }} />
        </>
      )}
    </section>
  )
}
