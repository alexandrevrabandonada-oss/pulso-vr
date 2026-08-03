import { lazy, Suspense, useRef, useState } from 'react'
import { Share2 } from 'lucide-react'
import type { ShareContext } from '../types'

const ShareDialog = lazy(() => import('./ShareDialog'))

export function ShareButton({ context, surface, label = 'Compartilhar', className }: { context: ShareContext; surface: string; label?: string; className?: string }) {
  const [open, setOpen] = useState(false)
  const trigger = useRef<HTMLButtonElement>(null)
  return <>
    <button ref={trigger} type="button" className={className} onClick={() => setOpen(true)}><Share2 />{label}</button>
    {open ? <Suspense fallback={null}><ShareDialog context={context} surface={surface} onClose={() => { setOpen(false); requestAnimationFrame(() => trigger.current?.focus()) }} /></Suspense> : null}
  </>
}
