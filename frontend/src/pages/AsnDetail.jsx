import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  getAsn,
  getAsnHistory,
  getAsnPeeringDb,
  getAsnPeers,
  getAsnPrefixes,
  refreshAsnBgp,
  refreshAsnPeeringDb,
  refreshAsnWhois,
} from '../api'
import HistoryTable, { formatDate } from '../components/HistoryTable'
import { ErrorBlock, Loading } from '../components/StatusBlock'

export default function AsnDetail() {
  const { asn } = useParams()

  const [info, setInfo] = useState(null)
  const [history, setHistory] = useState(null)
  const [prefixes, setPrefixes] = useState(null)
  const [peers, setPeers] = useState(null)
  const [peeringdb, setPeeringdb] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(null)

  function load() {
    setError(null)
    getAsn(asn).then(setInfo).catch((e) => setError(e.message))
    getAsnHistory(asn).then((h) => setHistory(h.history)).catch(() => {})
    getAsnPrefixes(asn).then((p) => setPrefixes(p.items)).catch(() => {})
    getAsnPeers(asn).then((p) => setPeers(p.items)).catch(() => {})
    getAsnPeeringDb(asn).then(setPeeringdb).catch(() => {})
  }

  useEffect(() => {
    setInfo(null)
    setHistory(null)
    setPrefixes(null)
    setPeers(null)
    setPeeringdb(null)
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [asn])

  async function runRefresh(name, fn) {
    setBusy(name)
    try {
      await fn(asn)
      load()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(null)
    }
  }

  if (error) return <ErrorBlock message={error} />
  if (!info) return <Loading />

  return (
    <div>
      <h1>AS{info.asn}</h1>

      <section className="card">
        <h2>RIR Tahsisi</h2>
        <table>
          <tbody>
            <tr>
              <th>RIR</th>
              <td>{info.rir}</td>
            </tr>
            <tr>
              <th>Ülke</th>
              <td>{info.country || '-'}</td>
            </tr>
            <tr>
              <th>Tahsis Tarihi</th>
              <td>{info.alloc_date || '-'}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section className="card">
        <div className="card-header">
          <h2>Sahiplik Geçmişi (RDAP)</h2>
          <button onClick={() => runRefresh('whois', refreshAsnWhois)} disabled={busy === 'whois'}>
            {busy === 'whois' ? 'Sorgulanıyor...' : 'Şimdi Sorgula'}
          </button>
        </div>
        <HistoryTable
          emptyText="Henüz whois verisi toplanmadı."
          columns={[
            { key: 'org_name', label: 'Organizasyon' },
            { key: 'handle', label: 'Handle' },
            { key: 'first_seen', label: 'İlk Görülme', render: (r) => formatDate(r.first_seen) },
            { key: 'last_seen', label: 'Son Görülme', render: (r) => formatDate(r.last_seen) },
          ]}
          rows={history}
        />
      </section>

      <section className="card">
        <div className="card-header">
          <h2>PeeringDB Profili</h2>
          <button
            onClick={() => runRefresh('peeringdb', refreshAsnPeeringDb)}
            disabled={busy === 'peeringdb'}
          >
            {busy === 'peeringdb' ? 'Sorgulanıyor...' : 'Şimdi Sorgula'}
          </button>
        </div>
        {peeringdb?.found ? (
          <table>
            <tbody>
              <tr>
                <th>Ad</th>
                <td>{peeringdb.name}</td>
              </tr>
              <tr>
                <th>Organizasyon</th>
                <td>{peeringdb.org_name || '-'}</td>
              </tr>
              <tr>
                <th>Şehir / Ülke</th>
                <td>
                  {peeringdb.city || '-'} / {peeringdb.country || '-'}
                </td>
              </tr>
              <tr>
                <th>Web Sitesi</th>
                <td>{peeringdb.website || '-'}</td>
              </tr>
            </tbody>
          </table>
        ) : (
          <p className="muted">PeeringDB profili henüz toplanmadı.</p>
        )}
      </section>

      <section className="card">
        <div className="card-header">
          <h2>BGP Duyurulan Prefixler</h2>
          <button onClick={() => runRefresh('bgp', refreshAsnBgp)} disabled={busy === 'bgp'}>
            {busy === 'bgp' ? 'Sorgulanıyor...' : 'Şimdi Sorgula'}
          </button>
        </div>
        <HistoryTable
          emptyText="Henüz BGP verisi toplanmadı."
          columns={[
            {
              key: 'prefix',
              label: 'Prefix',
              render: (r) => <Link to={`/prefix/${r.prefix}`}>{r.prefix}</Link>,
            },
            { key: 'active', label: 'Aktif', render: (r) => (r.active ? 'evet' : 'hayır') },
            { key: 'first_seen', label: 'İlk Görülme', render: (r) => formatDate(r.first_seen) },
            { key: 'last_seen', label: 'Son Görülme', render: (r) => formatDate(r.last_seen) },
          ]}
          rows={prefixes}
        />
      </section>

      <section className="card">
        <h2>BGP Komşuları (Peering)</h2>
        <p className="muted">
          RIPE NCC'nin RIS route collector'larının BGP tablolarında gözlemlediği komşu ASN'ler — gerçek
          peering'in herkese açık, kimlik doğrulama gerektirmeyen yaklaşık karşılığı. "Önceki hop"
          genelde upstream/transit ya da peer, "sonraki hop" genelde müşteri ya da peer ilişkisine işaret
          eder. "Güç" değeri kaç farklı gözlem noktasının bu komşuluğu gördüğünü gösterir.
        </p>
        <HistoryTable
          emptyText="Henüz peering verisi toplanmadı."
          columns={[
            {
              key: 'neighbour_asn',
              label: 'Komşu ASN',
              render: (r) => <Link to={`/asn/${r.neighbour_asn}`}>AS{r.neighbour_asn}</Link>,
            },
            {
              key: 'direction',
              label: 'Yön',
              render: (r) =>
                r.direction === 'left' ? 'Önceki hop' : r.direction === 'right' ? 'Sonraki hop' : 'Belirsiz',
            },
            { key: 'power', label: 'Güç', render: (r) => r.power ?? '-' },
            { key: 'first_seen', label: 'İlk Görülme', render: (r) => formatDate(r.first_seen) },
            { key: 'last_seen', label: 'Son Görülme', render: (r) => formatDate(r.last_seen) },
          ]}
          rows={peers}
        />
      </section>
    </div>
  )
}
