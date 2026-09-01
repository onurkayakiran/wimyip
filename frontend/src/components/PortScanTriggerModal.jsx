import { useState } from 'react'
import { createPortScanJob } from '../api'
import { ErrorBlock } from './StatusBlock'

export default function PortScanTriggerModal({ password, initialTarget, onClose, onCreated }) {
  const [target, setTarget] = useState(initialTarget || '')
  const [portMode, setPortMode] = useState('custom')
  const [customPorts, setCustomPorts] = useState('')
  const [delaySeconds, setDelaySeconds] = useState(5)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    const ports = customPorts
      .split(',')
      .map((p) => parseInt(p.trim(), 10))
      .filter((p) => Number.isInteger(p) && p > 0 && p <= 65535)

    if (portMode === 'custom' && ports.length === 0) {
      setError('En az bir port girin (virgülle ayırarak).')
      return
    }

    setSubmitting(true)
    createPortScanJob(password, {
      target,
      port_mode: portMode,
      custom_ports: ports,
      delay_seconds: Number(delaySeconds) || 5,
    })
      .then((job) => {
        onCreated(job)
        onClose()
      })
      .catch((err) => setError(err.message))
      .finally(() => setSubmitting(false))
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="card-header">
          <h2>Port Taraması Başlat</h2>
          <button onClick={onClose}>Kapat</button>
        </div>

        <form onSubmit={handleSubmit} className="search" style={{ flexDirection: 'column', alignItems: 'stretch', gap: '0.75rem' }}>
          <label>
            Hedef (IP veya CIDR)
            <input
              type="text"
              placeholder="örn. 8.8.8.8 veya 203.0.113.0/24"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              autoFocus
            />
          </label>

          <label>
            Port modu
            <select value={portMode} onChange={(e) => setPortMode(e.target.value)}>
              <option value="custom">Özel port listesi</option>
              <option value="popular">Popüler portlar</option>
              <option value="all">Tüm portlar (1-65535, yavaş)</option>
            </select>
          </label>

          {portMode === 'custom' && (
            <label>
              Portlar (virgülle ayırın)
              <input
                type="text"
                placeholder="örn. 22,80,443,3306"
                value={customPorts}
                onChange={(e) => setCustomPorts(e.target.value)}
              />
            </label>
          )}

          <label>
            IP'ler arası gecikme (saniye)
            <input
              type="number"
              min="0"
              step="0.5"
              value={delaySeconds}
              onChange={(e) => setDelaySeconds(e.target.value)}
            />
          </label>

          <ErrorBlock message={error} />

          <button type="submit" disabled={submitting || !target}>
            {submitting ? 'Başlatılıyor...' : 'Taramayı Başlat'}
          </button>
        </form>
      </div>
    </div>
  )
}
