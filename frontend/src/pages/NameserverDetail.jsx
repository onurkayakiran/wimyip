import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import { getNameserverDomains, getNameserverHistory } from '../api'
import HistoryTable, { formatDate } from '../components/HistoryTable'
import { ErrorBlock, Loading } from '../components/StatusBlock'
import useSeoMeta from '../hooks/useSeoMeta'

export default function NameserverDetail() {
  const { t } = useTranslation()
  const { nameserver } = useParams()

  const [history, setHistory] = useState(null)
  const [domains, setDomains] = useState(null)
  const [error, setError] = useState(null)

  useSeoMeta({
    title: nameserver,
    description: `Nameserver history for ${nameserver}: IP address history and the domains it serves.`,
    path: `/nameserver/${nameserver}`,
  })

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
        <h2>{t('nameserver.ip_history')}</h2>
        <HistoryTable
          emptyText={t('nameserver.no_ip_history')}
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
          rows={history}
        />
      </section>

      <section className="card">
        <h2>{t('nameserver.served_domains')}</h2>
        <HistoryTable
          emptyText={t('nameserver.no_domains')}
          columns={[
            {
              key: 'domain',
              label: t('ip.domain'),
              render: (r) => <Link to={`/domain/${r.domain}`}>{r.domain}</Link>,
            },
            { key: 'first_seen', label: t('common_detail.first_seen'), render: (r) => formatDate(r.first_seen) },
            { key: 'last_seen', label: t('common_detail.last_seen'), render: (r) => formatDate(r.last_seen) },
          ]}
          rows={domains}
        />
      </section>
    </div>
  )
}
