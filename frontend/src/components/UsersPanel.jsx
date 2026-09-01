import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { getAdminUsers, setUserPlan } from '../api'
import { formatDate } from './HistoryTable'
import { ErrorBlock, Loading } from './StatusBlock'

export default function UsersPanel({ password }) {
  const { t } = useTranslation()
  const [users, setUsers] = useState(null)
  const [error, setError] = useState(null)
  const [updating, setUpdating] = useState(null)

  function load() {
    getAdminUsers(password)
      .then((res) => setUsers(res.users))
      .catch((e) => setError(e.message))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function togglePlan(user) {
    const nextPlan = user.plan === 'premium' ? 'free' : 'premium'
    setUpdating(user.id)
    setUserPlan(password, user.id, nextPlan)
      .then(load)
      .catch((e) => setError(e.message))
      .finally(() => setUpdating(null))
  }

  return (
    <section className="card">
      <div className="card-header">
        <h2>{t('admin.users')}</h2>
      </div>
      <ErrorBlock message={error} />
      {!users ? (
        <Loading />
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>{t('admin.username')}</th>
                <th>{t('admin.email')}</th>
                <th>{t('admin.plan')}</th>
                <th>{t('admin.monitor_count')}</th>
                <th>{t('admin.registered')}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {users.length === 0 && (
                <tr>
                  <td colSpan={6} className="muted">
                    {t('admin.no_users_yet')}
                  </td>
                </tr>
              )}
              {users.map((u) => (
                <tr key={u.id}>
                  <td className="mono">{u.username}</td>
                  <td className="muted">{u.email}</td>
                  <td>
                    <span className={`badge ${u.plan === 'premium' ? 'badge-ok' : 'badge'}`}>{u.plan}</span>
                  </td>
                  <td className="muted">{u.monitor_count}</td>
                  <td className="muted">{formatDate(u.created_at)}</td>
                  <td>
                    <button onClick={() => togglePlan(u)} disabled={updating === u.id}>
                      {updating === u.id
                        ? t('admin.updating')
                        : u.plan === 'premium'
                          ? t('admin.downgrade_to_free')
                          : t('admin.upgrade_to_premium')}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
