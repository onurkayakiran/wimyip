export function Loading() {
  return <p className="muted">Yükleniyor...</p>
}

export function ErrorBlock({ message }) {
  if (!message) return null
  return <p className="error">{message}</p>
}
