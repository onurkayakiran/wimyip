import { useTranslation } from 'react-i18next'
import { Link, Outlet } from 'react-router-dom'
import LanguageSwitcher from '../components/LanguageSwitcher'
import SearchBar from '../components/SearchBar'
import useAuth from '../hooks/useAuth'

function AuthNav() {
  const { isAuthenticated, logout } = useAuth()
  const { t } = useTranslation()
  if (isAuthenticated) {
    return (
      <span style={{ display: 'flex', gap: '0.75rem', whiteSpace: 'nowrap' }}>
        <Link to="/monitors">{t('nav.my_panel')}</Link>
        <button onClick={logout}>{t('nav.logout')}</button>
      </span>
    )
  }
  return (
    <span style={{ display: 'flex', gap: '0.75rem', whiteSpace: 'nowrap' }}>
      <Link to="/login">{t('nav.login')}</Link>
      <Link to="/register">{t('nav.register')}</Link>
    </span>
  )
}

export default function PublicLayout() {
  const { t } = useTranslation()
  return (
    <div className="container">
      <header className="site-header">
        <Link to="/" className="brand">
          {t('nav.home')}
        </Link>
        <SearchBar />
        <AuthNav />
        <LanguageSwitcher className="lang-switcher" />
      </header>

      <main>
        <Outlet />
      </main>
    </div>
  )
}
