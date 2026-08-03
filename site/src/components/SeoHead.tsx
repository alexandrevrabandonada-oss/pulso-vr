import { useEffect, useMemo } from 'react'
import { useLocation } from 'wouter'
import { usePortal } from '../context/usePortal'
import { buildSeoMetadata, seoContextFromBrowser } from '../lib/seo'
import { municipalProperties } from '../lib/municipalities'

function setMeta(attribute: 'name' | 'property', key: string, content: string) {
  let element = document.head.querySelector<HTMLMetaElement>(`meta[${attribute}="${key}"]`)
  if (!element) {
    element = document.createElement('meta')
    element.setAttribute(attribute, key)
    element.dataset.observatorioSeo = 'true'
    document.head.appendChild(element)
  }
  element.content = content
}

function setLink(rel: string, href: string) {
  let element = document.head.querySelector<HTMLLinkElement>(`link[rel="${rel}"][data-observatorio-seo]`)
  if (!element) {
    element = document.createElement('link')
    element.rel = rel
    element.dataset.observatorioSeo = 'true'
    document.head.appendChild(element)
  }
  element.href = href
}

export function SeoHead() {
  const [location] = useLocation()
  const { catalog, release, topology } = usePortal()
  const municipalities = useMemo(() => municipalProperties(topology).map((item) => ({ code: item.code, name: item.name })), [topology])
  const metadata = useMemo(() => {
    const browserLocation = `${location.split('?')[0]}${window.location.search}`
    return buildSeoMetadata(seoContextFromBrowser(browserLocation, release, catalog.indicators, municipalities))
  }, [catalog.indicators, location, municipalities, release])

  useEffect(() => {
    document.title = metadata.title
    setMeta('name', 'description', metadata.description)
    setMeta('name', 'robots', metadata.robots)
    setMeta('property', 'og:type', 'website')
    setMeta('property', 'og:site_name', 'Observatório Estadual de Saúde do RJ')
    setMeta('property', 'og:title', metadata.title)
    setMeta('property', 'og:description', metadata.description)
    setMeta('property', 'og:url', metadata.canonicalUrl)
    setMeta('property', 'og:image', metadata.ogImage)
    setMeta('property', 'og:image:alt', metadata.ogImageAlt)
    setMeta('property', 'og:locale', 'pt_BR')
    setMeta('name', 'twitter:card', 'summary_large_image')
    setMeta('name', 'twitter:title', metadata.title)
    setMeta('name', 'twitter:description', metadata.description)
    setMeta('name', 'twitter:image', metadata.ogImage)
    setLink('canonical', metadata.canonicalUrl)
    document.head.querySelectorAll('script[data-observatorio-seo]').forEach((script) => script.remove())
    metadata.structuredData.forEach((data) => {
      const script = document.createElement('script')
      script.type = 'application/ld+json'
      script.dataset.observatorioSeo = 'true'
      script.textContent = JSON.stringify(data)
      document.head.appendChild(script)
    })
  }, [metadata])

  return null
}
