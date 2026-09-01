import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
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
  const { t } = useTranslation()
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
        <h2>{t('common_detail.rir_allocation')}</h2>
        <table>
          <tbody>
            <tr>
              <th>{t('common_detail.rir')}</th>
              <td>{info.rir}</td>
            </tr>
            <tr>
              <th>{t('common_detail.country')}</th>
              <td>{info.country || '-'}</td>
            </tr>
            <tr>
              <th>{t('common_detail.alloc_date')}</th>
              <td>{info.alloc_date || '-'}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section className="card">
        <div className="card-header">
          <h2>{t('common_detail.ownership_history')}</h2>
          <button onClick={() => runRefresh('whois', refreshAsnWhois)} disabled={busy === 'whois'}>
            {busy === 'whois' ? t('common_detail.querying') : t('common_detail.query_now')}
          </button>
        </div>
        <HistoryTable
          emptyText={t('common_detail.no_whois_data')}
          columns={[
            { key: 'org_name', label: t('common_detail.org') },
            { key: 'handle', label: t('common_detail.handle') },
            { key: 'first_seen', label: t('common_detail.first_seen'), render: (r) => formatDate(r.first_seen) },
            { key: 'last_seen', label: t('common_detail.last_seen'), render: (r) => formatDate(r.last_seen) },
          ]}
          rows={history}
        />
      </section>

      <section className="card">
        <div className="card-header">
          <h2>{t('asn.peeringdb_profile')}</h2>
          <button
            onClick={() => runRefresh('peeringdb', refreshAsnPeeringDb)}
            disabled={busy === 'peeringdb'}
          >
            {busy === 'peeringdb' ? t('common_detail.querying') : t('common_detail.query_now')}
          </button>
        </div>
        {peeringdb?.found ? (
          <table>
            <tbody>
              <tr>
                <th>{t('asn.name')}</th>
                <td>{peeringdb.name}</td>
              </tr>
              <tr>
                <th>{t('common_detail.org')}</th>
                <td>{peeringdb.org_name || '-'}</td>
              </tr>
              <tr>
                <th>{t('asn.city_country')}</th>
                <td>
                  {peeringdb.city || '-'} / {peeringdb.country || '-'}
                </td>
              </tr>
              <tr>
                <th>{t('asn.website')}</th>
                <td>{peeringdb.website || '-'}</td>
              </tr>
            </tbody>
          </table>
        ) : (
          <p className="muted">{t('asn.no_peeringdb')}</p>
        )}
      </section>

      <section className="card">
        <div className="card-header">
          <h2>{t('asn.announced_prefixes')}</h2>
          <button onClick={() => runRefresh('bgp', refreshAsnBgp)} disabled={busy === 'bgp'}>
            {busy === 'bgp' ? t('common_detail.querying') : t('common_detail.query_now')}
          </button>
        </div>
        <HistoryTable
          emptyText={t('asn.no_bgp_data')}
          columns={[
            {
              key: 'prefix',
              label: t('common_detail.cidr'),
              render: (r) => <Link to={`/prefix/${r.prefix}`}>{r.prefix}</Link>,
            },
            { key: 'active', label: t('ip.active'), render: (r) => (r.active ? t('common.yes') : t('common.no')) },
            { key: 'first_seen', label: t('common_detail.first_seen'), render: (r) => formatDate(r.first_seen) },
            { key: 'last_seen', label: t('common_detail.last_seen'), render: (r) => formatDate(r.last_seen) },
          ]}
          rows={prefixes}
        />
      </section>

      <section className="card">
        <h2>{t('asn.bgp_neighbours')}</h2>
        <p className="muted">{t('asn.bgp_neighbours_desc')}</p>
        <HistoryTable
          emptyText={t('asn.no_peering_data')}
          columns={[
            {
              key: 'neighbour_asn',
              label: t('asn.neighbour_asn'),
              render: (r) => <Link to={`/asn/${r.neighbour_asn}`}>AS{r.neighbour_asn}</Link>,
            },
            {
              key: 'direction',
              label: t('asn.direction'),
              render: (r) =>
                r.direction === 'left'
                  ? t('asn.direction_prev')
                  : r.direction === 'right'
                    ? t('asn.direction_next')
                    : t('asn.direction_unclear'),
            },
            { key: 'power', label: t('asn.power'), render: (r) => r.power ?? '-' },
            { key: 'first_seen', label: t('common_detail.first_seen'), render: (r) => formatDate(r.first_seen) },
            { key: 'last_seen', label: t('common_detail.last_seen'), render: (r) => formatDate(r.last_seen) },
          ]}
          rows={peers}
        />
      </section>
    </div>
  )
}
