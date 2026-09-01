import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useSearchParams } from 'react-router-dom'
import { search } from '../api'
import { ErrorBlock, Loading } from '../components/StatusBlock'

export default function SearchResults() {
  const { t } = useTranslation()
  const [params] = useSearchParams()
  const q = params.get('q') || ''

  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    setResults(null)
    setError(null)
    if (!q) return
    search(q).then(setResults).catch((e) => setError(e.message))
  }, [q])

  return (
    <div>
      <h1>{t('searchResults.title', { q })}</h1>
      <ErrorBlock message={error} />
      {!results && !error && <Loading />}

      {results && (
        <>
          <section className="card">
            <h2>{t('searchResults.asn_org')}</h2>
            {results.asns.length === 0 ? (
              <p className="muted">{t('searchResults.no_asn_match')}</p>
            ) : (
              <ul>
                {results.asns.map((a) => (
                  <li key={a.asn}>
                    <Link to={`/asn/${a.asn}`}>
                      AS{a.asn} — {a.org_name || t('common.unknown')}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="card">
            <h2>{t('searchResults.domains')}</h2>
            {results.domains.length === 0 ? (
              <p className="muted">{t('searchResults.no_domain_match')}</p>
            ) : (
              <ul>
                {results.domains.map((d) => (
                  <li key={d.domain}>
                    <Link to={`/domain/${d.domain}`}>{d.domain}</Link>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  )
}
