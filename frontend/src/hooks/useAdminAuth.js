import { useEffect, useState } from 'react'
import { adminLogin } from '../api'

const STORAGE_KEY = 'adminPassword'

// AdminPage ve /admin/port-scans gibi diger admin sayfalari ayni
// sessionStorage anahtarini paylasir - birinde giris yapilinca digeri
// tekrar parola sormaz.
export default function useAdminAuth() {
  const [password, setPassword] = useState(() => sessionStorage.getItem(STORAGE_KEY) || '')
  const [loggedIn, setLoggedIn] = useState(false)
  const [loginError, setLoginError] = useState(null)
  const [loginSubmitting, setLoginSubmitting] = useState(false)

  function tryLogin(pw) {
    setLoginSubmitting(true)
    setLoginError(null)
    return adminLogin(pw)
      .then(() => {
        sessionStorage.setItem(STORAGE_KEY, pw)
        setPassword(pw)
        setLoggedIn(true)
      })
      .catch((e) => setLoginError(e.message))
      .finally(() => setLoginSubmitting(false))
  }

  useEffect(() => {
    if (password) {
      tryLogin(password)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function logout() {
    sessionStorage.removeItem(STORAGE_KEY)
    setLoggedIn(false)
  }

  return { password, loggedIn, loginError, loginSubmitting, tryLogin, logout }
}
