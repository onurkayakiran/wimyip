import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'
import { getPrefix, getPrefixHistory, refreshPrefixWhois } from '../api'
import HistoryTable, { formatDate } from '../components/HistoryTable'
import { ErrorBlock, Loading } from '../components/StatusBlock'

export default function PrefixDetail() {
  const { t } = useTranslation()
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
          {t('prefix.not_exact_match_notice')} <span className="mono">{prefix.cidr}</span>
        </p>
      )}

      <section className="card">
        <h2>{t('common_detail.rir_allocation')}</h2>
        <table>
          <tbody>
            <tr>
              <th>{t('common_detail.cidr')}</th>
              <td className="mono">{prefix.cidr}</td>
            </tr>
            <tr>
              <th>{t('common_detail.rir')}</th>
              <td>{prefix.rir}</td>
            </tr>
            <tr>
              <th>{t('common_detail.country')}</th>
              <td>{prefix.country || '-'}</td>
            </tr>
            <tr>
              <th>{t('common_detail.status')}</th>
              <td>{prefix.status}</td>
            </tr>
            <tr>
              <th>{t('common_detail.alloc_date')}</th>
              <td>{prefix.alloc_date || '-'}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section className="card">
        <div className="card-header">
          <h2>{t('common_detail.ownership_history')}</h2>
          <button onClick={handleRefresh} disabled={refreshing}>
            {refreshing ? t('common_detail.querying') : t('common_detail.query_now')}
          </button>
        </div>
        <HistoryTable
          emptyText={t('common_detail.no_whois_data_query_now')}
          columns={[
            { key: 'org_name', label: t('common_detail.org') },
            { key: 'handle', label: t('common_detail.handle') },
            { key: 'first_seen', label: t('common_detail.first_seen'), render: (r) => formatDate(r.first_seen) },
            { key: 'last_seen', label: t('common_detail.last_seen'), render: (r) => formatDate(r.last_seen) },
          ]}
          rows={history}
        />
      </section>
    </div>
  )
}
