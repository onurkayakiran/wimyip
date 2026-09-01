import { useTranslation } from 'react-i18next'

export function Loading() {
  const { t } = useTranslation()
  return <p className="muted">{t('common.loading')}</p>
}

export function ErrorBlock({ message }) {
  if (!message) return null
  return <p className="error">{message}</p>
}
