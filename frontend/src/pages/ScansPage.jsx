import { Trans, useTranslation } from 'react-i18next'
import PortScanPanel from '../components/PortScanPanel'
import useAuth from '../hooks/useAuth'

export default function ScansPage() {
  const { t } = useTranslation()
  const { token, user, isPremium } = useAuth()

  if (!user) {
    return null
  }

  if (!isPremium) {
    return (
      <section className="card">
        <h2>{t('scans.title')}</h2>
        <p>
          <Trans i18nKey="scans.premium_required" components={{ bold: <strong /> }} />
        </p>
      </section>
    )
  }

  return (
    <div>
      <div className="card-header">
        <h1 style={{ fontSize: '1.2rem', margin: 0 }}>{t('scans.title')}</h1>
      </div>
      <PortScanPanel token={token} />
    </div>
  )
}
