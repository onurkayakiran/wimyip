import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listDomains } from '../api'
import { formatDate } from './HistoryTable'
import { ErrorBlock, Loading } from './StatusBlock'

const LIMIT = 50

export default function TrDomainsModal({ onClose }) {
  const [query, setQuery] = useState('')
  const [offset, setOffset] = useState(0)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  function load() {
    listDomains({ source: 'tr_apex_scan', q: query, limit: LIMIT, offset })
      .then((res) => {
        setData(res)
        setError(null)
      })
      .catch((e) => setError(e.message))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, offset])

  function handleSearchChange(e) {
    setOffset(0)
    setQuery(e.target.value)
  }

  const total = data?.total ?? 0
  const items = data?.items ?? []
  const hasPrev = offset > 0
  const hasNext = offset + LIMIT < total

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="card-header">
          <h2>Türkiye Apex Domain Taraması</h2>
          <button onClick={onClose}>Kapat</button>
        </div>

        <input
          type="text"
          placeholder="Domain ara..."
          value={query}
          onChange={handleSearchChange}
          autoFocus
        />

        <ErrorBlock message={error} />

        {!data ? (
          <Loading />
        ) : (
          <>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Domain</th>
                    <th>İlk Görülme</th>
                    <th>Son Görülme</th>
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
                        Sonuç bulunamadı.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="card-header">
              <span className="muted">
                {total > 0 ? `${offset + 1}-${Math.min(offset + LIMIT, total)} / ${total}` : '0 sonuç'}
              </span>
              <span>
                <button onClick={() => setOffset(offset - LIMIT)} disabled={!hasPrev}>
                  Önceki
                </button>{' '}
                <button onClick={() => setOffset(offset + LIMIT)} disabled={!hasNext}>
                  Sonraki
                </button>
              </span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
