import { useEffect, useRef, useState } from "react"
import { BrandMark, brands } from "./components/brands"

const SITEKEY = "3x00000000000000000000FF"

type TurnstileApi = {
  render: (el: HTMLElement, opts: Record<string, unknown>) => string
  remove: (id: string) => void
}

declare global {
  interface Window {
    turnstile?: TurnstileApi
  }
}

let loader: Promise<void> | null = null

function loadTurnstile() {
  if (window.turnstile) return Promise.resolve()
  if (!loader) {
    loader = new Promise((resolve, reject) => {
      const script = document.createElement("script")
      script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit"
      script.async = true
      script.onload = () => resolve()
      script.onerror = () => {
        loader = null
        reject(new Error("Turnstile failed to load"))
      }
      document.head.appendChild(script)
    })
  }
  return loader
}

export function Turnstile({ onVerify }: { onVerify: (ok: boolean) => void }) {
  const host = useRef<HTMLDivElement>(null)
  const [failed, setFailed] = useState(false)
  const cloudflare = brands.find((icon) => icon.slug === "cloudflare") ?? brands[0]

  useEffect(() => {
    let widgetId = ""
    let gone = false
    loadTurnstile()
      .then(() => {
        if (gone || !host.current || !window.turnstile) return
        widgetId = window.turnstile.render(host.current, {
          sitekey: SITEKEY,
          theme: "dark",
          callback: () => onVerify(true),
          "expired-callback": () => onVerify(false),
          "error-callback": () => {
            setFailed(true)
            onVerify(false)
          },
        })
      })
      .catch(() => {
        if (!gone) setFailed(true)
      })
    return () => {
      gone = true
      if (widgetId && window.turnstile) window.turnstile.remove(widgetId)
    }
  }, [onVerify])

  return (
    <div className="flex flex-col items-center gap-3">
      <p className="flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-white/55">
        <BrandMark icon={cloudflare} className="h-4 w-4" />
        Cloudflare Turnstile
      </p>
      <div ref={host} />
      {failed ? <p className="text-sm text-white/60">The check could not load. The buttons stay off until it does.</p> : null}
      <p className="max-w-sm text-center text-xs font-light text-white/45">
        Interactive preview widget from Cloudflare. It does not open a bytesint.xyz account and nothing you type is stored.
      </p>
    </div>
  )
}
