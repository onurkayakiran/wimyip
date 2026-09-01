import { createContext, useContext, useState } from 'react'
import { loginUser, registerUser } from '../api'

const STORAGE_KEY = 'authToken'

const AuthContext = createContext(null)

// Admin panelinin sessionStorage tabanli useAdminAuth'undan BAGIMSIZ - bu
// normal kullanici oturumu, farkli bir yetki alani. JWT localStorage'da
// tutulur (Authorization: Bearer header ile gonderilir, cookie/session degil).
// Context olarak tutulmasinin sebebi: hem site-header'daki giris/cikis
// linklerinin hem de /monitors sayfasinin AYNI oturum durumunu paylasmasi
// gerekiyor - context olmadan her useAuth() cagrisi kendi bagimsiz local
// state'ine sahip olur ve biri login olunca digeri bundan haberdar olmaz.
export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(STORAGE_KEY) || '')

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
  }

  const value = { token, isAuthenticated: !!token, login, register, logout }
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth() bir <AuthProvider> icinde kullanilmali')
  }
  return ctx
}
