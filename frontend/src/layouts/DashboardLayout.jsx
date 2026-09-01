import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { NavLink, Navigate, Outlet, useNavigate } from 'react-router-dom'
import LanguageSwitcher from '../components/LanguageSwitcher'
import useAuth from '../hooks/useAuth'

export default function DashboardLayout() {
  const { isAuthenticated, user, logout } = useAuth()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  const NAV_ITEMS = [
    { to: '/monitors', icon: '◎', label: t('monitors.title') },
    { to: '/scans', icon: '⌕', label: t('scans.title') },
  ]

  const displayName = user?.first_name || user?.username || ''
  const initial = displayName ? displayName.charAt(0).toUpperCase() : '?'

  return (
    <div className="dashboard-shell">
      <aside className="dashboard-sidebar">
        <NavLink to="/" className="dashboard-logo">
          <span className="dashboard-logo-dot" />
          wimyip
        </NavLink>

        <nav className="dashboard-nav">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `dashboard-nav-item${isActive ? ' active' : ''}`}
            >
              <span className="dashboard-nav-icon">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <LanguageSwitcher className="lang-switcher dashboard-lang-switcher" />

        <div className="dashboard-profile">
          <button className="dashboard-profile-trigger" onClick={() => setMenuOpen((v) => !v)}>
            <span className="dashboard-avatar">{initial}</span>
            <span className="dashboard-profile-name">{displayName || '...'}</span>
            <span className="muted">⋯</span>
          </button>
          {menuOpen && (
            <div className="dropdown-menu dashboard-profile-menu">
              <button
                onClick={() => {
                  setMenuOpen(false)
                  navigate('/profile')
                }}
              >
                {t('profile.title')}
              </button>
              <button onClick={logout}>{t('nav.logout')}</button>
            </div>
          )}
        </div>
      </aside>

      <main className="dashboard-content">
        <Outlet />
      </main>
    </div>
  )
}
