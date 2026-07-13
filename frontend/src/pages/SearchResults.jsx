import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { search } from '../api'
import { ErrorBlock, Loading } from '../components/StatusBlock'

export default function SearchResults() {
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
      <h1>"{q}" için arama sonuçları</h1>
      <ErrorBlock message={error} />
      {!results && !error && <Loading />}

      {results && (
        <>
          <section className="card">
            <h2>ASN / Organizasyon</h2>
            {results.asns.length === 0 ? (
              <p className="muted">Eşleşen ASN bulunamadı.</p>
            ) : (
              <ul>
                {results.asns.map((a) => (
                  <li key={a.asn}>
                    <Link to={`/asn/${a.asn}`}>
                      AS{a.asn} — {a.org_name || 'bilinmiyor'}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="card">
            <h2>Domainler</h2>
            {results.domains.length === 0 ? (
              <p className="muted">Eşleşen domain bulunamadı.</p>
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
