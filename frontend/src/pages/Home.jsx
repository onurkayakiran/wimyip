import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { getMyIp, getStats } from '../api'
import JobStatusPanel from '../components/JobStatusPanel'
import { ErrorBlock, Loading } from '../components/StatusBlock'
import useSeoMeta from '../hooks/useSeoMeta'

export default function Home() {
  const { t } = useTranslation()
  const [stats, setStats] = useState(null)
  const [myIp, setMyIp] = useState(null)
  const [error, setError] = useState(null)

  useSeoMeta({
    title: 'IP / ASN / Domain / WHOIS History Archive',
    description:
      'Free, searchable archive of IP addresses, ASNs, IP prefixes, domains and nameservers with WHOIS ownership history, BGP announcement history, PeeringDB profiles and DNS record history.',
    path: '/',
  })

  useEffect(() => {
    getStats().then(setStats).catch((e) => setError(e.message))
    getMyIp().then((r) => setMyIp(r.ip)).catch(() => {})
  }, [])

  return (
    <div>
      {myIp && (
        <Link to={`/ip/${myIp}`} className="my-ip-banner">
          <span className="muted">{t('home.your_ip')}</span>
          <span className="my-ip-value mono">{myIp}</span>
        </Link>
      )}

      <section className="stats">
        {stats ? (
          <>
            <div className="stat">
              <span>{stats.prefixes.toLocaleString()}</span>
              {t('home.ip_blocks')}
            </div>
            <div className="stat">
              <span>{stats.asns.toLocaleString()}</span>
              {t('home.asns')}
            </div>
            <div className="stat">
              <span>{stats.domains.toLocaleString()}</span>
              {t('home.domains')}
            </div>
          </>
        ) : (
          <Loading />
        )}
      </section>

      <ErrorBlock message={error} />

      <JobStatusPanel />

      <section className="card">
        <h2>{t('home.quick_links')}</h2>
        <p>
          <Link to="/ip/8.8.8.8">{t('home.example_ip')}</Link> ·{' '}
          <Link to="/asn/15169">{t('home.example_asn')}</Link> ·{' '}
          <Link to="/domain/google.com">{t('home.example_domain')}</Link>
        </p>
      </section>

      <footer className="site-footer">{t('home.footer', { year: new Date().getFullYear() })}</footer>
    </div>
  )
}
