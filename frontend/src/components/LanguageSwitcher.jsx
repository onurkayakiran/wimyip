import { useTranslation } from 'react-i18next'

const LANGUAGES = [
  { code: 'en', label: 'EN' },
  { code: 'de', label: 'DE' },
  { code: 'tr', label: 'TR' },
  { code: 'ru', label: 'RU' },
  { code: 'fr', label: 'FR' },
]

export default function LanguageSwitcher({ className }) {
  const { i18n } = useTranslation()
  const current = i18n.resolvedLanguage || i18n.language || 'en'

  return (
    <select
      className={className}
      value={LANGUAGES.some((l) => l.code === current) ? current : 'en'}
      onChange={(e) => i18n.changeLanguage(e.target.value)}
      aria-label="Language"
    >
      {LANGUAGES.map((l) => (
        <option key={l.code} value={l.code}>
          {l.label}
        </option>
      ))}
    </select>
  )
}
