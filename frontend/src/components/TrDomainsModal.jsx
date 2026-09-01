import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { listDomains } from '../api'
import { formatDate } from './HistoryTable'
import { ErrorBlock, Loading } from './StatusBlock'

const LIMIT = 50

export default function TrDomainsModal({ onClose }) {
  const { t } = useTranslation()
  const [inputValue, setInputValue] = useState('')
  const [submittedQuery, setSubmittedQuery] = useState('')
  const [offset, setOffset] = useState(0)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [searching, setSearching] = useState(false)
  const requestId = useRef(0)

  function load() {
    const id = ++requestId.current
    setSearching(true)
    listDomains({ source: 'tr_apex_scan', q: submittedQuery, limit: LIMIT, offset })
      .then((res) => {
        if (id !== requestId.current) return // gec kalmis/eski cevap - yok say
        setData(res)
        setError(null)
      })
      .catch((e) => {
        if (id !== requestId.current) return
        setError(e.message)
      })
      .finally(() => {
        if (id === requestId.current) setSearching(false)
      })
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [submittedQuery, offset])

  function handleSubmit(e) {
    e.preventDefault()
    setOffset(0)
    setSubmittedQuery(inputValue)
  }

  const total = data?.total ?? 0
  const items = data?.items ?? []
  const hasPrev = offset > 0
  const hasNext = offset + LIMIT < total

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="card-header">
          <h2>{t('admin.tr_domain_modal_title')}</h2>
          <button onClick={onClose}>{t('common.close')}</button>
        </div>

        <form onSubmit={handleSubmit} className="search">
          <input
            type="text"
            placeholder={t('admin.search_domain_placeholder')}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            autoFocus
          />
          <button type="submit" disabled={searching}>
            {searching ? t('admin.searching') : t('admin.search')}
          </button>
        </form>

        <ErrorBlock message={error} />

        {!data ? (
          <Loading />
        ) : (
          <>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>{t('admin.domain')}</th>
                    <th>{t('admin.first_seen')}</th>
                    <th>{t('admin.last_seen')}</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.domain}>
                      <td className="mono">
                        <Link to={`/domain/${item.domain}`}>{item.domain}</Link>
                      </td>
                      <td>{formatDate(item.first_seen)}</td>
                      <td>{formatDate(item.last_seen)}</td>
                    </tr>
                  ))}
                  {items.length === 0 && (
                    <tr>
                      <td colSpan={3} className="muted">
                        {t('admin.no_results')}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="card-header">
              <span className="muted">
                {total > 0 ? t('common.results_range', { from: offset + 1, to: Math.min(offset + LIMIT, total), total }) : t('common.results_count', { count: 0 })}
              </span>
              <span>
                <button onClick={() => setOffset(offset - LIMIT)} disabled={!hasPrev}>
                  {t('common.previous')}
                </button>{' '}
                <button onClick={() => setOffset(offset + LIMIT)} disabled={!hasNext}>
                  {t('common.next')}
                </button>
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
