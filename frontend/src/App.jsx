import { Link, Route, Routes } from 'react-router-dom'
import SearchBar from './components/SearchBar'
import useAuth from './hooks/useAuth'
import AdminPage from './pages/AdminPage'
import AsnDetail from './pages/AsnDetail'
import DomainDetail from './pages/DomainDetail'
import Home from './pages/Home'
import IpLookup from './pages/IpLookup'
import LoginPage from './pages/LoginPage'
import MonitorsPage from './pages/MonitorsPage'
import NameserverDetail from './pages/NameserverDetail'
import PortScansPage from './pages/PortScansPage'
import PrefixDetail from './pages/PrefixDetail'
import RegisterPage from './pages/RegisterPage'
import SearchResults from './pages/SearchResults'

function AuthNav() {
  const { isAuthenticated, logout } = useAuth()
  if (isAuthenticated) {
    return (
      <span style={{ display: 'flex', gap: '0.75rem', whiteSpace: 'nowrap' }}>
        <Link to="/monitors">Monitörlerim</Link>
        <button onClick={logout}>Çıkış</button>
      </span>
    )
  }
  return (
    <span style={{ display: 'flex', gap: '0.75rem', whiteSpace: 'nowrap' }}>
      <Link to="/login">Giriş Yap</Link>
      <Link to="/register">Kayıt Ol</Link>
    </span>
  )
}

export default function App() {
  return (
    <div className="container">
      <header className="site-header">
        <Link to="/" className="brand">
          Anasayfa
        </Link>
        <SearchBar />
        <AuthNav />
      </header>

      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/ip/:ip" element={<IpLookup />} />
          <Route path="/asn/:asn" element={<AsnDetail />} />
          <Route path="/domain/:domain" element={<DomainDetail />} />
          <Route path="/nameserver/:nameserver" element={<NameserverDetail />} />
          <Route path="/prefix/*" element={<PrefixDetail />} />
          <Route path="/search" element={<SearchResults />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/monitors" element={<MonitorsPage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/admin/port-scans" element={<PortScansPage />} />
        </Routes>
      </main>
    </div>
  )
}
