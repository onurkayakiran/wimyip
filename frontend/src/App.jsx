import { Link, Route, Routes } from 'react-router-dom'
import SearchBar from './components/SearchBar'
import AdminPage from './pages/AdminPage'
import AsnDetail from './pages/AsnDetail'
import DomainDetail from './pages/DomainDetail'
import Home from './pages/Home'
import IpLookup from './pages/IpLookup'
import NameserverDetail from './pages/NameserverDetail'
import PrefixDetail from './pages/PrefixDetail'
import SearchResults from './pages/SearchResults'

export default function App() {
  return (
    <div className="container">
      <header className="site-header">
        <Link to="/" className="brand">
          Anasayfa
        </Link>
        <SearchBar />
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
          <Route path="/admin" element={<AdminPage />} />
        </Routes>
      </main>
    </div>
  )
}
