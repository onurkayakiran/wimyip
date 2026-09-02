import { useEffect } from 'react'

const SITE_NAME = 'wimyip.net'
const SITE_ORIGIN = 'https://wimyip.net'

function upsertMeta(selector, createEl) {
  let el = document.head.querySelector(selector)
  if (!el) {
    el = createEl()
    document.head.appendChild(el)
  }
  return el
}

function setMetaByName(name, content) {
  const el = upsertMeta(`meta[name="${name}"]`, () => {
    const m = document.createElement('meta')
    m.setAttribute('name', name)
    return m
  })
  el.setAttribute('content', content)
}

function setMetaByProperty(property, content) {
  const el = upsertMeta(`meta[property="${property}"]`, () => {
    const m = document.createElement('meta')
    m.setAttribute('property', property)
    return m
  })
  el.setAttribute('content', content)
}

function setCanonical(href) {
  const el = upsertMeta('link[rel="canonical"]', () => {
    const l = document.createElement('link')
    l.setAttribute('rel', 'canonical')
    return l
  })
  el.setAttribute('href', href)
}

// Bir tarayicida (ve JS calistiran Googlebot/Bingbot'ta) sayfa basi
// title/description/OG/Twitter/canonical etiketlerini gunceller. Bot'lar
// icin asil kaynak backend'deki /api/seo/* dinamik render katmani (bkz.
// nginx.conf'taki bot yonlendirmesi) - bu hook sadece gercek
// tarayicilarda ve JS render eden crawler'larda dogru meta gostermek
// icin, react-helmet gibi ek bir bagimliliga gerek kalmadan.
export default function useSeoMeta({ title, description, path, ogType = 'website' }) {
  useEffect(() => {
    if (!title) return
    const fullTitle = `${title} | ${SITE_NAME}`
    const url = `${SITE_ORIGIN}${path || ''}`

    document.title = fullTitle
    if (description) setMetaByName('description', description)
    setCanonical(url)

    setMetaByProperty('og:title', fullTitle)
    if (description) setMetaByProperty('og:description', description)
    setMetaByProperty('og:type', ogType)
    setMetaByProperty('og:url', url)
    setMetaByProperty('og:site_name', SITE_NAME)
    setMetaByProperty('og:image', `${SITE_ORIGIN}/og-image.svg`)

    setMetaByName('twitter:card', 'summary_large_image')
    setMetaByName('twitter:title', fullTitle)
    if (description) setMetaByName('twitter:description', description)
  }, [title, description, path, ogType])
}
