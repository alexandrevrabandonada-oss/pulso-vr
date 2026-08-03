import { useEffect, useMemo, useRef, useState } from 'react'
import { Check, Copy, Download, Facebook, Instagram, Send, Share2, X } from 'lucide-react'
import { usePortal } from '../context/usePortal'
import { trackEvent } from '../lib/analytics'
import { buildCardUrl, buildSocialUrl, SHARE_FORMATS, SHARE_TEMPLATES } from '../lib/share'
import type { ShareContext, ShareFormat, ShareTarget, ShareTemplate } from '../types'

export default function ShareDialog({ context, surface, onClose }: { context: ShareContext; surface: string; onClose: () => void }) {
  const { release } = usePortal()
  const [template, setTemplate] = useState<ShareTemplate>(context.template)
  const [format, setFormat] = useState<ShareFormat>(context.format)
  const [message, setMessage] = useState('')
  const [previewFailed, setPreviewFailed] = useState(false)
  const close = useRef<HTMLButtonElement>(null)
  const dialog = useRef<HTMLElement>(null)
  const current = useMemo(() => ({ ...context, template, format }), [context, format, template])
  const origin = window.location.origin
  const socialUrl = buildSocialUrl(origin, current, release.releaseId)
  const imageUrl = buildCardUrl(origin, current, release.releaseId)

  useEffect(() => {
    close.current?.focus(); trackEvent('share_opened', { surface })
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
      if (event.key === 'Tab') {
        const controls = Array.from(dialog.current?.querySelectorAll<HTMLElement>('button:not([disabled]), a[href]') ?? [])
        if (!controls.length) return
        const first = controls[0]; const last = controls[controls.length - 1]
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
      }
    }
    document.body.classList.add('has-modal'); window.addEventListener('keydown', escape)
    return () => { document.body.classList.remove('has-modal'); window.removeEventListener('keydown', escape) }
  }, [onClose, surface])

  const completed = (target: ShareTarget) => trackEvent('share_completed', { surface, template, format, target })
  const download = async (instagram = false) => {
    try {
      const response = await fetch(imageUrl); if (!response.ok) throw new Error('card')
      const blob = await response.blob(); const file = new File([blob], `observatorio-${template}-${format}.png`, { type: 'image/png' })
      if (instagram && navigator.share && navigator.canShare?.({ files: [file] })) {
        await navigator.share({ files: [file], title: 'Observatório Estadual de Saúde do RJ' }); completed('instagram'); return
      }
      const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = file.name; anchor.click(); URL.revokeObjectURL(url)
      setMessage(instagram ? 'Imagem baixada. Abra o Instagram e selecione o arquivo para publicar.' : 'Card baixado.')
      completed(instagram ? 'instagram' : 'download')
    } catch { setMessage('Não foi possível gerar a imagem agora. O link continua disponível.'); trackEvent('share_failed', { surface, template, format, target: instagram ? 'instagram' : 'download' }) }
  }
  const native = async () => {
    try { await navigator.share({ title: 'Observatório Estadual de Saúde do RJ', url: socialUrl }); completed('native') }
    catch (error) { if ((error as DOMException).name !== 'AbortError') trackEvent('share_failed', { surface, template, format, target: 'native' }) }
  }
  const copy = async () => { await navigator.clipboard.writeText(socialUrl); setMessage('Link copiado.'); completed('copy') }
  const open = (target: 'whatsapp' | 'facebook') => {
    const url = target === 'whatsapp' ? `https://wa.me/?text=${encodeURIComponent(`Veja este dado do Observatório Estadual de Saúde do RJ: ${socialUrl}`)}` : `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(socialUrl)}`
    window.open(url, '_blank', 'noopener,noreferrer'); completed(target)
  }

  return <div className="share-dialog-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
    <section ref={dialog} className="share-dialog" role="dialog" aria-modal="true" aria-labelledby="share-title">
      <header><div><span>Compartilhamento seguro</span><h2 id="share-title">Criar card do dado</h2></div><button ref={close} type="button" className="share-dialog__close" onClick={onClose} aria-label="Fechar compartilhamento"><X /></button></header>
      <div className="share-dialog__layout"><div className="share-dialog__controls">
        <fieldset><legend>1. Conteúdo</legend><div className="share-choice-grid">{SHARE_TEMPLATES.map((item) => <button type="button" aria-pressed={template === item.id} key={item.id} onClick={() => { setTemplate(item.id); trackEvent('share_template_selected', { surface, template: item.id }) }}><strong>{item.label}</strong><small>{item.description}</small></button>)}</div></fieldset>
        <fieldset><legend>2. Formato</legend><div className="share-format-grid">{SHARE_FORMATS.map((item) => <button type="button" aria-pressed={format === item.id} key={item.id} onClick={() => setFormat(item.id)}><strong>{item.label}</strong><small>{item.size}</small></button>)}</div></fieldset>
      </div><div className={`share-preview share-preview--${format}`}>{previewFailed ? <p>Prévia da imagem disponível no ambiente de preview da Vercel. O link pode ser copiado normalmente.</p> : <img src={imageUrl} onError={() => setPreviewFailed(true)} alt={`Prévia do card: ${SHARE_TEMPLATES.find((item) => item.id === template)?.label}`} />}</div></div>
      <div className="share-dialog__actions"><button type="button" onClick={() => open('whatsapp')}><Send />WhatsApp</button><button type="button" onClick={() => open('facebook')}><Facebook />Facebook</button><button type="button" onClick={() => download(true)}><Instagram />Instagram</button>{'share' in navigator ? <button type="button" onClick={native}><Share2 />Sistema</button> : null}<button type="button" onClick={copy}><Copy />Copiar link</button><button type="button" onClick={() => download()}><Download />Baixar PNG</button></div>
      <p className="share-dialog__note">O texto é gerado a partir dos dados públicos. Valores protegidos não são incluídos.</p><p className="share-dialog__feedback" aria-live="polite">{message ? <><Check />{message}</> : null}</p>
    </section>
  </div>
}
