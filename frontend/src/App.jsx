import { Route, Routes } from 'react-router-dom'
import DashboardLayout from './layouts/DashboardLayout'
import PublicLayout from './layouts/PublicLayout'
import AdminPage from './pages/AdminPage'
import AsnDetail from './pages/AsnDetail'
import DomainDetail from './pages/DomainDetail'
import Home from './pages/Home'
import IpLookup from './pages/IpLookup'
import LoginPage from './pages/LoginPage'
import MonitorsPage from './pages/MonitorsPage'
import NameserverDetail from './pages/NameserverDetail'
import PrefixDetail from './pages/PrefixDetail'
import ProfilePage from './pages/ProfilePage'
import RegisterPage from './pages/RegisterPage'
import ScansPage from './pages/ScansPage'
import SearchResults from './pages/SearchResults'

export default function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<Home />} />
        <Route path="/ip/:ip" element={<IpLookup />} />
        <Route path="/asn/:asn" element={<AsnDetail />} />
        <Route path="/domain/:domain" element={<DomainDetail />} />
        <Route path="/nameserver/:nameserver" element={<NameserverDetail />} />
        <Route path="/prefix/*" element={<PrefixDetail />} />
        <Route path="/search" element={<SearchResults />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Route>

      <Route element={<DashboardLayout />}>
        <Route path="/monitors" element={<MonitorsPage />} />
        <Route path="/scans" element={<ScansPage />} />
        <Route path="/profile" element={<ProfilePage />} />
      </Route>
    </Routes>
  )
}
