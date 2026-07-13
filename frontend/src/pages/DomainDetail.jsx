import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getDomain, getDomainHistory, refreshDomainDns } from '../api'
import HistoryTable, { formatDate } from '../components/HistoryTable'
import { ErrorBlock, Loading } from '../components/StatusBlock'

export default function DomainDetail() {
  const { domain } = useParams()

  const [info, setInfo] = useState(null)
  const [history, setHistory] = useState(null)
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  function load() {
    setError(null)
    getDomain(domain)
      .then(setInfo)
      .catch(() => setInfo({ domain, sources: [], ptr_records: [], notFound: true }))
    getDomainHistory(domain).then(setHistory).catch(() => {})
  }

  useEffect(() => {
    setInfo(null)
    setHistory(null)
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [domain])

  async function handleRefresh() {
    setRefreshing(true)
    try {
      await refreshDomainDns(domain)
      load()
    } catch (e) {
      setError(e.message)
    } finally {
      setRefreshing(false)
    }
  }

  if (error) return <ErrorBlock message={error} />
  if (!info) return <Loading />

  return (
    <div>
      <h1 className="mono">{domain}</h1>

      <section className="card">
        <div className="card-header">
          <h2>Genel Bilgi</h2>
          <button onClick={handleRefresh} disabled={refreshing}>
            {refreshing ? 'Sorgulanıyor...' : 'DNS Şimdi Sorgula'}
          </button>
        </div>
        {info.notFound ? (
          <p className="muted">Bu domain henüz arşivde keşfedilmedi; "DNS Şimdi Sorgula" ile ekleyebilirsiniz.</p>
        ) : (
          <table>
            <tbody>
              <tr>
                <th>Kaynaklar</th>
                <td>{(info.sources || []).join(', ') || '-'}</td>
              </tr>
              <tr>
                <th>İlk Görülme</th>
                <td>{formatDate(info.first_seen)}</td>
              </tr>
              <tr>
                <th>Son Görülme</th>
                <td>{formatDate(info.last_seen)}</td>
              </tr>
            </tbody>
          </table>
        )}
      </section>

      <section className="card">
        <h2>IP Geçmişi (A/AAAA)</h2>
        <HistoryTable
          emptyText="Henüz IP geçmişi toplanmadı."
          columns={[
            {
              key: 'ip',
              label: 'IP',
              render: (r) => <Link to={`/ip/${r.ip}`}>{r.ip}</Link>,
            },
            { key: 'ip_version', label: 'Versiyon', render: (r) => `IPv${r.ip_version}` },
            { key: 'first_seen', label: 'İlk Görülme', render: (r) => formatDate(r.first_seen) },
            { key: 'last_seen', label: 'Son Görülme', render: (r) => formatDate(r.last_seen) },
          ]}
          rows={history?.ip_history}
        />
      </section>

      <section className="card">
        <h2>Nameserver Geçmişi (NS)</h2>
        <HistoryTable
          emptyText="Henüz NS geçmişi toplanmadı."
          columns={[
            {
              key: 'nameserver',
              label: 'Nameserver',
              render: (r) => <Link to={`/nameserver/${r.nameserver}`}>{r.nameserver}</Link>,
            },
            { key: 'first_seen', label: 'İlk Görülme', render: (r) => formatDate(r.first_seen) },
            { key: 'last_seen', label: 'Son Görülme', render: (r) => formatDate(r.last_seen) },
          ]}
          rows={history?.ns_history}
        />
      </section>

      {info.ptr_records?.length > 0 && (
        <section className="card">
          <h2>Bu Hostname'e İşaret Eden PTR Kayıtları</h2>
          <HistoryTable
            columns={[
              {
                key: 'ip',
                label: 'IP',
                render: (r) => <Link to={`/ip/${r.ip}`}>{r.ip}</Link>,
              },
              { key: 'first_seen', label: 'İlk Görülme', render: (r) => formatDate(r.first_seen) },
            ]}
            rows={info.ptr_records}
          />
        </section>
      )}
    </div>
  )
}
