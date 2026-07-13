import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getNameserverDomains, getNameserverHistory } from '../api'
import HistoryTable, { formatDate } from '../components/HistoryTable'
import { ErrorBlock, Loading } from '../components/StatusBlock'

export default function NameserverDetail() {
  const { nameserver } = useParams()

  const [history, setHistory] = useState(null)
  const [domains, setDomains] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    setHistory(null)
    setDomains(null)
    setError(null)
    getNameserverHistory(nameserver)
      .then((h) => setHistory(h.ip_history))
      .catch((e) => setError(e.message))
    getNameserverDomains(nameserver)
      .then((d) => setDomains(d.items))
      .catch(() => {})
  }, [nameserver])

  if (error) return <ErrorBlock message={error} />
  if (history === null) return <Loading />

  return (
    <div>
      <h1 className="mono">{nameserver}</h1>

      <section className="card">
        <h2>IP Geçmişi</h2>
        <HistoryTable
          emptyText="Bu nameserver için henüz IP geçmişi toplanmadı."
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
          rows={history}
        />
      </section>

      <section className="card">
        <h2>Hizmet Verdiği Domainler</h2>
        <HistoryTable
          emptyText="Henüz eşleşen domain bulunamadı."
          columns={[
            {
              key: 'domain',
              label: 'Domain',
              render: (r) => <Link to={`/domain/${r.domain}`}>{r.domain}</Link>,
            },
            { key: 'first_seen', label: 'İlk Görülme', render: (r) => formatDate(r.first_seen) },
            { key: 'last_seen', label: 'Son Görülme', render: (r) => formatDate(r.last_seen) },
          ]}
          rows={domains}
        />
      </section>
    </div>
  )
}
