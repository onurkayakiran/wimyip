import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import { getDomain, getDomainHistory, refreshDomainDns } from '../api'
import HistoryTable, { formatDate } from '../components/HistoryTable'
import { ErrorBlock, Loading } from '../components/StatusBlock'
import useSeoMeta from '../hooks/useSeoMeta'

export default function DomainDetail() {
  const { t } = useTranslation()
  const { domain } = useParams()

  const [info, setInfo] = useState(null)
  const [history, setHistory] = useState(null)
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  useSeoMeta({
    title: domain,
    description: `DNS record history (A/AAAA, NS, MX, TXT) and archive metadata for the domain ${domain}.`,
    path: `/domain/${domain}`,
  })

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
          <h2>{t('domain.general_info')}</h2>
          <button onClick={handleRefresh} disabled={refreshing}>
            {refreshing ? t('domain.querying') : t('domain.query_dns_now')}
          </button>
        </div>
        {info.notFound ? (
          <p className="muted">{t('domain.not_found_notice')}</p>
        ) : (
          <table>
            <tbody>
              <tr>
                <th>{t('domain.sources')}</th>
                <td>{(info.sources || []).join(', ') || '-'}</td>
              </tr>
              <tr>
                <th>{t('common_detail.first_seen')}</th>
                <td>{formatDate(info.first_seen)}</td>
              </tr>
              <tr>
                <th>{t('common_detail.last_seen')}</th>
                <td>{formatDate(info.last_seen)}</td>
              </tr>
            </tbody>
          </table>
        )}
      </section>

      <section className="card">
        <h2>{t('domain.ip_history')}</h2>
        <HistoryTable
          emptyText={t('domain.no_ip_history')}
          columns={[
            {
              key: 'ip',
              label: 'IP',
              render: (r) => <Link to={`/ip/${r.ip}`}>{r.ip}</Link>,
            },
            { key: 'ip_version', label: t('domain.version'), render: (r) => `IPv${r.ip_version}` },
            { key: 'first_seen', label: t('common_detail.first_seen'), render: (r) => formatDate(r.first_seen) },
            { key: 'last_seen', label: t('common_detail.last_seen'), render: (r) => formatDate(r.last_seen) },
          ]}
          rows={history?.ip_history}
        />
      </section>

      <section className="card">
        <h2>{t('domain.ns_history')}</h2>
        <HistoryTable
          emptyText={t('domain.no_ns_history')}
          columns={[
            {
              key: 'nameserver',
              label: t('ip.nameserver'),
              render: (r) => <Link to={`/nameserver/${r.nameserver}`}>{r.nameserver}</Link>,
            },
            { key: 'first_seen', label: t('common_detail.first_seen'), render: (r) => formatDate(r.first_seen) },
            { key: 'last_seen', label: t('common_detail.last_seen'), render: (r) => formatDate(r.last_seen) },
          ]}
          rows={history?.ns_history}
        />
      </section>

      <section className="card">
        <h2>{t('domain.mx_history')}</h2>
        <HistoryTable
          emptyText={t('domain.no_mx_history')}
          columns={[
            { key: 'priority', label: t('domain.priority'), render: (r) => r.priority },
            { key: 'exchange', label: t('domain.server'), render: (r) => <span className="mono">{r.exchange}</span> },
            { key: 'first_seen', label: t('common_detail.first_seen'), render: (r) => formatDate(r.first_seen) },
            { key: 'last_seen', label: t('common_detail.last_seen'), render: (r) => formatDate(r.last_seen) },
          ]}
          rows={history?.mx_history}
        />
      </section>

      <section className="card">
        <h2>{t('domain.txt_history')}</h2>
        <HistoryTable
          emptyText={t('domain.no_txt_history')}
          columns={[
            {
              key: 'value',
              label: t('domain.value'),
              render: (r) => (
                <span className="mono" title={r.value}>
                  {r.value.length > 60 ? `${r.value.slice(0, 60)}…` : r.value}
                </span>
              ),
            },
            { key: 'first_seen', label: t('common_detail.first_seen'), render: (r) => formatDate(r.first_seen) },
            { key: 'last_seen', label: t('common_detail.last_seen'), render: (r) => formatDate(r.last_seen) },
          ]}
          rows={history?.txt_history}
        />
      </section>

      {info.ptr_records?.length > 0 && (
        <section className="card">
          <h2>{t('domain.ptr_pointing_title')}</h2>
          <HistoryTable
            columns={[
              {
                key: 'ip',
                label: 'IP',
                render: (r) => <Link to={`/ip/${r.ip}`}>{r.ip}</Link>,
              },
              { key: 'first_seen', label: t('common_detail.first_seen'), render: (r) => formatDate(r.first_seen) },
            ]}
            rows={info.ptr_records}
          />
        </section>
      )}
    </div>
  )
}
