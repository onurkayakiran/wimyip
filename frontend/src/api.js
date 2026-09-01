import i18n from './i18n'

const API_BASE = '/api'

async function request(path, options) {
  const res = await fetch(`${API_BASE}${path}`, options)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || i18n.t('common.request_failed', { status: res.status }))
  }
  return res.json()
}

export const getStats = () => request('/stats')
export const getStatus = () => request('/status')
export const getMyIp = () => request('/whoami')

export const lookupIp = (ip) => request(`/lookup/ip/${encodeURIComponent(ip)}`)
export const refreshIpBgp = (ip) =>
  request(`/lookup/ip/${encodeURIComponent(ip)}/refresh-bgp`, { method: 'POST' })

// NOT: cidr zaten "/" iceriyor (orn. "8.8.8.0/24") - encodeURIComponent
// bunu %2F'ye cevirir ve backend'in {cidr:path} yakalayicisiyla uyusmaz,
// bu yuzden cidr'i OLDUGU GIBI path'e gomuyoruz.
export const getPrefix = (cidr) => request(`/prefixes/${cidr}`)
export const getPrefixHistory = (cidr) => request(`/prefixes/${cidr}/history`)
export const refreshPrefixWhois = (cidr) => request(`/prefixes/${cidr}/refresh`, { method: 'POST' })
export const listPrefixes = (params = {}) =>
  request(`/prefixes?${new URLSearchParams(params).toString()}`)

export const getAsn = (asn) => request(`/asns/${asn}`)
export const getAsnHistory = (asn) => request(`/asns/${asn}/history`)
export const getAsnPrefixes = (asn, limit = 200) => request(`/asns/${asn}/prefixes?limit=${limit}`)
export const getAsnPeers = (asn, limit = 200) => request(`/asns/${asn}/peers?limit=${limit}`)
export const getAsnPeeringDb = (asn) => request(`/asns/${asn}/peeringdb`).catch(() => null)
export const refreshAsnWhois = (asn) => request(`/asns/${asn}/refresh`, { method: 'POST' })
export const refreshAsnBgp = (asn) => request(`/asns/${asn}/refresh-bgp`, { method: 'POST' })
export const refreshAsnPeeringDb = (asn) => request(`/asns/${asn}/refresh-peeringdb`, { method: 'POST' })

export const getDomain = (domain) => request(`/domains/${encodeURIComponent(domain)}`)
export const getDomainHistory = (domain) => request(`/domains/${encodeURIComponent(domain)}/history`)
export const refreshDomainDns = (domain) =>
  request(`/domains/${encodeURIComponent(domain)}/refresh-dns`, { method: 'POST' })
export const listDomains = (params = {}) =>
  request(`/domains?${new URLSearchParams(params).toString()}`)

export const getNameserverHistory = (ns) => request(`/nameservers/${encodeURIComponent(ns)}/history`)
export const getNameserverDomains = (ns) => request(`/nameservers/${encodeURIComponent(ns)}/domains`)

export const search = (q) => request(`/search?q=${encodeURIComponent(q)}`)

export const adminLogin = (password) =>
  request('/admin/login', { method: 'POST', headers: { 'X-Admin-Password': password } })

export const getRemoteWorkerStatus = (password) =>
  request('/admin/remote-workers/status', { headers: { 'X-Admin-Password': password } })

export const getRemoteWorkerTokens = (password) =>
  request('/admin/remote-workers/tokens', { headers: { 'X-Admin-Password': password } })

export const createRemoteWorkerToken = (password, label, queues) =>
  request('/admin/remote-workers/tokens', {
    method: 'POST',
    headers: { 'X-Admin-Password': password, 'Content-Type': 'application/json' },
    body: JSON.stringify({ label, queues }),
  })

export const revokeRemoteWorkerToken = (password, tokenId) =>
  request(`/admin/remote-workers/tokens/${encodeURIComponent(tokenId)}/revoke`, {
    method: 'POST',
    headers: { 'X-Admin-Password': password },
  })

export const registerUser = (username, email, password) =>
  request('/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password }),
  })

export const loginUser = (username, password) =>
  request('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })

const authHeaders = (token) => ({ Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' })

export const listMonitors = (token) => request('/monitors', { headers: authHeaders(token) })

export const getMonitor = (token, monitorId) =>
  request(`/monitors/${encodeURIComponent(monitorId)}`, { headers: authHeaders(token) })

export const createMonitor = (token, body) =>
  request('/monitors', { method: 'POST', headers: authHeaders(token), body: JSON.stringify(body) })

export const updateMonitor = (token, monitorId, body) =>
  request(`/monitors/${encodeURIComponent(monitorId)}`, {
    method: 'PATCH',
    headers: authHeaders(token),
    body: JSON.stringify(body),
  })

export const deleteMonitor = (token, monitorId) =>
  request(`/monitors/${encodeURIComponent(monitorId)}`, { method: 'DELETE', headers: authHeaders(token) })

export const getProfile = (token) => request('/auth/me', { headers: authHeaders(token) })

export const updateProfile = (token, body) =>
  request('/auth/me', { method: 'PATCH', headers: authHeaders(token), body: JSON.stringify(body) })

export const changePassword = (token, currentPassword, newPassword) =>
  request('/auth/change-password', {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  })

// IP Tarama - premium kullanicilara acik (bkz. backend/app/api/routes/scans.py)
export const createScanJob = (token, body) =>
  request('/scans', { method: 'POST', headers: authHeaders(token), body: JSON.stringify(body) })

export const listScanJobs = (token, params = {}) =>
  request(`/scans?${new URLSearchParams(params).toString()}`, { headers: authHeaders(token) })

export const getScanJob = (token, jobId) =>
  request(`/scans/${encodeURIComponent(jobId)}`, { headers: authHeaders(token) })

export const resetScanJob = (token, jobId) =>
  request(`/scans/${encodeURIComponent(jobId)}/reset`, { method: 'POST', headers: authHeaders(token) })

export const getAdminUsers = (password) =>
  request('/admin/users', { headers: { 'X-Admin-Password': password } })

export const setUserPlan = (password, userId, plan) =>
  request(`/admin/users/${encodeURIComponent(userId)}/plan`, {
    method: 'POST',
    headers: { 'X-Admin-Password': password, 'Content-Type': 'application/json' },
    body: JSON.stringify({ plan }),
  })
