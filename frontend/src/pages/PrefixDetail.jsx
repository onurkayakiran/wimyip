import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getPrefix, getPrefixHistory, refreshPrefixWhois } from '../api'
import HistoryTable, { formatDate } from '../components/HistoryTable'
import { ErrorBlock, Loading } from '../components/StatusBlock'

export default function PrefixDetail() {
  const params = useParams()
  const cidr = params['*']

  const [prefix, setPrefix] = useState(null)
  const [history, setHistory] = useState(null)
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  function load() {
    setError(null)
    getPrefix(cidr).then(setPrefix).catch((e) => setError(e.message))
    getPrefixHistory(cidr)
      .then((h) => setHistory(h.history))
      .catch(() => {})
  }

  useEffect(() => {
    setPrefix(null)
    setHistory(null)
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cidr])

  async function handleRefresh() {
    setRefreshing(true)
    try {
      await refreshPrefixWhois(cidr)
      load()
    } catch (e) {
      setError(e.message)
    } finally {
      setRefreshing(false)
    }
  }

  if (error) return <ErrorBlock message={error} />
  if (!prefix) return <Loading />

  return (
    <div>
      <h1 className="mono">{prefix.queried_cidr || prefix.cidr}</h1>

      {!prefix.exact_match && (
        <p className="muted">
          Bu tam aralık için ayrı bir RIR kaydı yok (muhtemelen BGP'de görülen daha
          spesifik bir alt-blok) — içinde bulunduğu RIR bloğu gösteriliyor:{' '}
          <span className="mono">{prefix.cidr}</span>
        </p>
      )}

      <section className="card">
        <h2>RIR Tahsisi</h2>
        <table>
          <tbody>
            <tr>
              <th>CIDR</th>
              <td className="mono">{prefix.cidr}</td>
            </tr>
            <tr>
              <th>RIR</th>
              <td>{prefix.rir}</td>
            </tr>
            <tr>
              <th>Ülke</th>
              <td>{prefix.country || '-'}</td>
            </tr>
            <tr>
              <th>Durum</th>
              <td>{prefix.status}</td>
            </tr>
            <tr>
              <th>Tahsis Tarihi</th>
              <td>{prefix.alloc_date || '-'}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section className="card">
        <div className="card-header">
          <h2>Sahiplik Geçmişi (RDAP)</h2>
          <button onClick={handleRefresh} disabled={refreshing}>
            {refreshing ? 'Sorgulanıyor...' : 'Şimdi Sorgula'}
          </button>
        </div>
        <HistoryTable
          emptyText="Henüz whois verisi toplanmadı — 'Şimdi Sorgula' ile hemen çekebilirsiniz."
          columns={[
            { key: 'org_name', label: 'Organizasyon' },
            { key: 'handle', label: 'Handle' },
            { key: 'first_seen', label: 'İlk Görülme', render: (r) => formatDate(r.first_seen) },
            { key: 'last_seen', label: 'Son Görülme', render: (r) => formatDate(r.last_seen) },
          ]}
          rows={history}
        />
      </section>
    </div>
  )
}
