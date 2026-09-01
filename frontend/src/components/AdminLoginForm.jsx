import { useState } from 'react'
import { ErrorBlock } from './StatusBlock'

export default function AdminLoginForm({ onSubmit, submitting, error }) {
  const [password, setPassword] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    onSubmit(password)
  }

  return (
    <section className="card">
      <h2>Yönetim Paneli Girişi</h2>
      <form className="search" onSubmit={handleSubmit}>
        <input
          type="password"
          placeholder="Parola"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoFocus
        />
        <button type="submit" disabled={submitting || !password}>
          {submitting ? 'Kontrol ediliyor...' : 'Giriş'}
        </button>
      </form>
      <ErrorBlock message={error} />
    </section>
  )
}
