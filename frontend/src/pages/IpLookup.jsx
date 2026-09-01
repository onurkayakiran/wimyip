import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import { lookupIp, refreshIpBgp } from '../api'
import HistoryTable, { formatDate } from '../components/HistoryTable'
import { ErrorBlock, Loading } from '../components/StatusBlock'

export default function IpLookup() {
  const { t } = useTranslation()
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
        setRefreshNote(t('ip.bgp_no_asn_found'))
      } else {
        setRefreshNote(t('ip.bgp_updated', { asns: result.asns.join(', AS') }))
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
        <h2>{t('common_detail.rir_allocation')}</h2>
        <table>
          <tbody>
            <tr>
              <th>{t('common_detail.cidr')}</th>
              <td>
                <Link to={`/prefix/${data.prefix.cidr}`}>{data.prefix.cidr}</Link>
              </td>
            </tr>
            <tr>
              <th>{t('common_detail.rir')}</th>
              <td>{data.prefix.rir}</td>
            </tr>
            <tr>
              <th>{t('common_detail.country')}</th>
              <td>{data.prefix.country || '-'}</td>
            </tr>
            <tr>
              <th>{t('common_detail.status')}</th>
              <td>{data.prefix.status}</td>
            </tr>
            <tr>
              <th>{t('common_detail.alloc_date')}</th>
              <td>{data.prefix.alloc_date || '-'}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section className="card">
        <div className="card-header">
          <h2>{t('ip.bgp_history')}</h2>
          <button onClick={handleRefreshBgp} disabled={refreshing}>
            {refreshing ? t('ip.collecting') : t('ip.bgp_collect_now')}
          </button>
        </div>
        {refreshNote && <p className="muted">{refreshNote}</p>}
        <HistoryTable
          emptyText={t('ip.no_bgp_data')}
          columns={[
            { key: 'asn', label: t('ip.asn'), render: (r) => <Link to={`/asn/${r.asn}`}>AS{r.asn}</Link> },
            { key: 'prefix', label: t('ip.announced_prefix') },
            { key: 'active', label: t('ip.active'), render: (r) => (r.active ? t('common.yes') : t('common.no')) },
            { key: 'first_seen', label: t('common_detail.first_seen'), render: (r) => formatDate(r.first_seen) },
            { key: 'last_seen', label: t('common_detail.last_seen'), render: (r) => formatDate(r.last_seen) },
          ]}
          rows={data.bgp}
        />
      </section>

      <section className="card">
        <h2>{t('ip.ptr_record')}</h2>
        <HistoryTable
          emptyText={t('ip.no_ptr_data')}
          columns={[
            {
              key: 'ptr_hostname',
              label: t('ip.hostname'),
              render: (r) => <Link to={`/domain/${r.ptr_hostname}`}>{r.ptr_hostname}</Link>,
            },
            { key: 'first_seen', label: t('common_detail.first_seen'), render: (r) => formatDate(r.first_seen) },
            { key: 'last_seen', label: t('common_detail.last_seen'), render: (r) => formatDate(r.last_seen) },
          ]}
          rows={data.ptr}
        />
      </section>

      {data.nameserver_domains?.length > 0 && (
        <section className="card">
          <h2>{t('ip.nameserver_domains_title')}</h2>
          <HistoryTable
            columns={[
              { key: 'nameserver', label: t('ip.nameserver') },
              {
                key: 'domain',
                label: t('ip.domain'),
                render: (r) => <Link to={`/domain/${r.domain}`}>{r.domain}</Link>,
              },
              { key: 'last_seen', label: t('common_detail.last_seen'), render: (r) => formatDate(r.last_seen) },
            ]}
            rows={data.nameserver_domains}
          />
        </section>
      )}
    </div>
  )
}
