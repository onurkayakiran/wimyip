import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { createScanJob } from '../api'
import { ErrorBlock } from './StatusBlock'

export default function PortScanTriggerModal({ token, initialTarget, onClose, onCreated }) {
  const { t } = useTranslation()
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
      setError(t('scans.ports_required'))
      return
    }

    setSubmitting(true)
    createScanJob(token, {
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
          <h2>{t('scans.trigger_title')}</h2>
          <button onClick={onClose}>{t('common.close')}</button>
        </div>

        <form onSubmit={handleSubmit} className="search" style={{ flexDirection: 'column', alignItems: 'stretch', gap: '0.75rem' }}>
          <label>
            {t('scans.target_label')}
            <input
              type="text"
              placeholder={t('scans.target_hint')}
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              autoFocus
            />
          </label>

          <label>
            {t('scans.port_mode')}
            <select value={portMode} onChange={(e) => setPortMode(e.target.value)}>
              <option value="custom">{t('scans.port_mode_custom')}</option>
              <option value="popular">{t('scans.port_mode_popular')}</option>
              <option value="all">{t('scans.port_mode_all')}</option>
            </select>
          </label>

          {portMode === 'custom' && (
            <label>
              {t('scans.ports_label')}
              <input
                type="text"
                placeholder={t('scans.ports_hint')}
                value={customPorts}
                onChange={(e) => setCustomPorts(e.target.value)}
              />
            </label>
          )}

          <label>
            {t('scans.delay_label')}
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
            {submitting ? t('scans.starting') : t('scans.start')}
          </button>
        </form>
      </div>
    </div>
  )
}
