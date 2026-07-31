const API_BASE = '/api'

async function request(path, options) {
  const res = await fetch(`${API_BASE}${path}`, options)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `İstek başarısız: ${res.status}`)
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

export const getAdminServices = (password) =>
  request('/admin/services', { headers: { 'X-Admin-Password': password } })

export const getAdminServiceLogs = (password, service, tail = 200) =>
  request(`/admin/services/${encodeURIComponent(service)}/logs?tail=${tail}`, {
    headers: { 'X-Admin-Password': password },
  })

export const restartAdminService = (password, service) =>
  request(`/admin/services/${encodeURIComponent(service)}/restart`, {
    method: 'POST',
    headers: { 'X-Admin-Password': password },
  })
