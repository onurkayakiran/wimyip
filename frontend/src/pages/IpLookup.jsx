import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { lookupIp, refreshIpBgp } from '../api'
import HistoryTable, { formatDate } from '../components/HistoryTable'
import { ErrorBlock, Loading } from '../components/StatusBlock'

export default function IpLookup() {
  const { ip } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const [refreshNote, setRefreshNote] = useState(null)

  function load() {
    setError(null)
    return lookupIp(ip).then(setData).catch((e) => setError(e.message))
  }

  useEffect(() => {
    setData(null)
    setError(null)
    setRefreshNote(null)
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ip])

  async function handleRefreshBgp() {
    setRefreshing(true)
    setRefreshNote(null)
    try {
      const result = await refreshIpBgp(ip)
      if (!result.asns?.length) {
        setRefreshNote('RIPEstat bu IP için şu an duyuran bir ASN bulamadı.')
      } else {
        setRefreshNote(`Güncellendi: AS${result.asns.join(', AS')} tarandı.`)
      }
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setRefreshing(false)
    }
  }

  if (error) return <ErrorBlock message={error} />
  if (!data) return <Loading />

  return (
    <div>
      <h1 className="mono">{data.ip}</h1>

      <section className="card">
        <h2>RIR Tahsisi</h2>
        <table>
          <tbody>
            <tr>
              <th>CIDR</th>
              <td>
                <Link to={`/prefix/${data.prefix.cidr}`}>{data.prefix.cidr}</Link>
              </td>
            </tr>
            <tr>
              <th>RIR</th>
              <td>{data.prefix.rir}</td>
            </tr>
            <tr>
              <th>Ülke</th>
              <td>{data.prefix.country || '-'}</td>
            </tr>
            <tr>
              <th>Durum</th>
              <td>{data.prefix.status}</td>
            </tr>
            <tr>
              <th>Tahsis Tarihi</th>
              <td>{data.prefix.alloc_date || '-'}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section className="card">
        <div className="card-header">
          <h2>BGP Duyuru Geçmişi</h2>
          <button onClick={handleRefreshBgp} disabled={refreshing}>
            {refreshing ? 'Toplanıyor...' : 'BGP Verisini Şimdi Topla'}
          </button>
        </div>
        {refreshNote && <p className="muted">{refreshNote}</p>}
        <HistoryTable
          emptyText="Bu IP için henüz BGP verisi toplanmadı — 'BGP Verisini Şimdi Topla' ile hemen çekebilirsiniz."
          columns={[
            { key: 'asn', label: 'ASN', render: (r) => <Link to={`/asn/${r.asn}`}>AS{r.asn}</Link> },
            { key: 'prefix', label: 'Duyurulan Prefix' },
            { key: 'active', label: 'Aktif', render: (r) => (r.active ? 'evet' : 'hayır') },
            { key: 'first_seen', label: 'İlk Görülme', render: (r) => formatDate(r.first_seen) },
            { key: 'last_seen', label: 'Son Görülme', render: (r) => formatDate(r.last_seen) },
          ]}
          rows={data.bgp}
        />
      </section>

      <section className="card">
        <h2>PTR Kaydı</h2>
        <HistoryTable
          emptyText="Bu IP için henüz PTR kaydı bulunamadı."
          columns={[
            {
              key: 'ptr_hostname',
              label: 'Hostname',
              render: (r) => <Link to={`/domain/${r.ptr_hostname}`}>{r.ptr_hostname}</Link>,
            },
            { key: 'first_seen', label: 'İlk Görülme', render: (r) => formatDate(r.first_seen) },
            { key: 'last_seen', label: 'Son Görülme', render: (r) => formatDate(r.last_seen) },
          ]}
          rows={data.ptr}
        />
      </section>

      {data.nameserver_domains?.length > 0 && (
        <section className="card">
          <h2>Bu IP Bir Nameserver — Hizmet Verdiği Domainler</h2>
          <HistoryTable
            columns={[
              { key: 'nameserver', label: 'Nameserver' },
              {
                key: 'domain',
                label: 'Domain',
                render: (r) => <Link to={`/domain/${r.domain}`}>{r.domain}</Link>,
              },
              { key: 'last_seen', label: 'Son Görülme', render: (r) => formatDate(r.last_seen) },
            ]}
            rows={data.nameserver_domains}
          />
        </section>
      )}
    </div>
  )
}
