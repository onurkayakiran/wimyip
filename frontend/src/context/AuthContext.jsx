import { createContext, useContext, useEffect, useState } from 'react'
import { getProfile, loginUser, registerUser } from '../api'

const STORAGE_KEY = 'authToken'

const AuthContext = createContext(null)

// Admin panelinin sessionStorage tabanli useAdminAuth'undan BAGIMSIZ - bu
// normal kullanici oturumu, farkli bir yetki alani. JWT localStorage'da
// tutulur (Authorization: Bearer header ile gonderilir, cookie/session degil).
// Context olarak tutulmasinin sebebi: hem site-header'daki giris/cikis
// linklerinin hem de dashboard sayfalarinin AYNI oturum durumunu (VE
// kullanici profilini - sidebar'daki ad/avatar, premium/free rozeti icin)
// paylasmasi gerekiyor.
export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(STORAGE_KEY) || '')
  const [user, setUser] = useState(null)

  function refreshProfile(authToken) {
    if (!authToken) {
      setUser(null)
      return
    }
    getProfile(authToken)
      .then(setUser)
      .catch(() => setUser(null))
  }

  useEffect(() => {
    refreshProfile(token)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  function login(username, password) {
    return loginUser(username, password).then((res) => {
      localStorage.setItem(STORAGE_KEY, res.access_token)
      setToken(res.access_token)
      return res
    })
  }

  function register(username, email, password) {
    return registerUser(username, email, password).then((res) => {
      localStorage.setItem(STORAGE_KEY, res.access_token)
      setToken(res.access_token)
      return res
    })
  }

  function logout() {
    localStorage.removeItem(STORAGE_KEY)
    setToken('')
    setUser(null)
  }

  const value = {
    token,
    user,
    isAuthenticated: !!token,
    isPremium: user?.plan === 'premium',
    refreshProfile: () => refreshProfile(token),
    login,
    register,
    logout,
  }
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth() bir <AuthProvider> icinde kullanilmali')
  }
  return ctx
}
