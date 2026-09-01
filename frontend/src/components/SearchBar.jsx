import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'

function detectDestination(raw) {
  const q = raw.trim()
  if (!q) return null

  if (q.includes('/')) return `/prefix/${q}`

  if (/^\d{1,3}(\.\d{1,3}){3}$/.test(q)) return `/ip/${q}`

  const asnMatch = q.match(/^AS?(\d+)$/i)
  if (asnMatch) return `/asn/${asnMatch[1]}`

  if (/^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)+$/.test(q)) {
    return `/domain/${q}`
  }

  return `/search?q=${encodeURIComponent(q)}`
}

export default function SearchBar({ autoFocus = false }) {
  const [value, setValue] = useState('')
  const navigate = useNavigate()
  const { t } = useTranslation()

  function handleSubmit(e) {
    e.preventDefault()
    const dest = detectDestination(value)
    if (dest) navigate(dest)
  }

  return (
    <form onSubmit={handleSubmit} className="search">
      <input
        type="text"
        autoFocus={autoFocus}
        placeholder={t('common.search_placeholder')}
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      <button type="submit">{t('common.search')}</button>
    </form>
  )
}
