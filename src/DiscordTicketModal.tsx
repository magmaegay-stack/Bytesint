import { useState } from "react"
import { Link } from "react-router-dom"
import { Icon } from "@iconify/react"

interface DiscordTicketModalProps {
  isOpen: boolean
  onClose: () => void
  isLoggedIn: boolean
  planName?: string
  planPrice?: number | string
}

export function DiscordTicketModal({
  isOpen,
  onClose,
  isLoggedIn,
  planName,
  planPrice,
}: DiscordTicketModalProps) {
  const [copied, setCopied] = useState(false)

  if (!isOpen) return null

  const discordUrl = "https://discord.gg/T5pZgFbGE"

  const handleCopy = () => {
    navigator.clipboard.writeText(discordUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div
        className="relative w-full max-w-md rounded-3xl border border-white/20 bg-[#0c0c11] p-6 sm:p-7 shadow-2xl text-center space-y-5 animate-scale-up"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close X Button */}
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 rounded-full p-2 text-white/40 hover:bg-white/10 hover:text-white transition"
          aria-label="Chiudi"
        >
          <Icon icon="ph:x-bold" className="h-4 w-4" />
        </button>

        {!isLoggedIn ? (
          /* ==================================================== */
          /* CASE 1: USER IS NOT LOGGED IN -> REQUIRE ACCOUNT    */
          /* ==================================================== */
          <div className="space-y-5">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-amber-500/15 border border-amber-500/30 text-amber-400 shadow-[0_0_35px_rgba(245,158,11,0.25)]">
              <Icon icon="ph:user-circle-plus-bold" className="h-8 w-8" />
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-amber-400 font-semibold">
                ACCOUNT RICHIESTO
              </span>
              <h3 className="mt-1 text-xl font-bold text-white tracking-tight">
                Crea un account prima di acquistare
              </h3>
              <p className="mt-2 text-xs text-white/60 leading-relaxed font-light">
                Per acquistare {planName ? `il pacchetto ${planName}` : "crediti"} e riscattare le tue ricerche OSINT, devi prima creare il tuo account operatore gratuito.
              </p>
            </div>

            <div className="space-y-2.5 pt-1">
              <Link
                to="/register"
                onClick={onClose}
                className="flex w-full items-center justify-center gap-2 rounded-2xl bg-white hover:bg-white/90 py-3 text-xs font-semibold text-black transition shadow-lg"
              >
                <span>Crea Account Gratuito</span>
                <Icon icon="ph:arrow-right-bold" className="h-3.5 w-3.5" />
              </Link>

              <Link
                to="/login"
                onClick={onClose}
                className="flex w-full items-center justify-center gap-2 rounded-2xl border border-white/15 bg-white/5 hover:bg-white/10 py-2.5 text-xs text-white/80 hover:text-white transition"
              >
                <span>Hai già un account? Accedi</span>
              </Link>
            </div>
          </div>
        ) : (
          /* ==================================================== */
          /* CASE 2: USER IS LOGGED IN -> OPEN DISCORD TICKET    */
          /* ==================================================== */
          <div className="space-y-5">
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-[#5865F2]/15 border border-[#5865F2]/40 text-[#5865F2] shadow-[0_0_35px_rgba(88,101,242,0.3)]">
              <Icon icon="ph:discord-logo-fill" className="h-8 w-8" />
            </div>

            <div>
              <span className="text-[10px] font-mono uppercase tracking-[0.2em] text-[#5865F2] font-semibold">
                ACQUISTO TICKET • DISCORD SERVER
              </span>
              <h3 className="mt-1 text-xl font-bold text-white tracking-tight">
                {planName ? `Acquista ${planName}` : "Completa il tuo Acquisto"}
              </h3>
              {planPrice && (
                <p className="text-xs text-emerald-400 font-mono mt-0.5">Prezzo: €{planPrice}</p>
              )}
              <p className="mt-2 text-xs text-white/65 leading-relaxed font-light">
                Entra nel nostro server Discord ufficiale e apri un ticket nel canale dedicato all'assistenza per ricevere subito la tua chiave licenza con i crediti:
              </p>
            </div>

            {/* Discord Link Box */}
            <div className="rounded-2xl border border-white/10 bg-white/5 p-3.5 flex items-center justify-between gap-3 text-left">
              <div className="min-w-0">
                <p className="text-[10px] font-mono text-white/40 uppercase">Server Discord Ufficiale</p>
                <p className="text-xs font-mono font-medium text-emerald-400 truncate">{discordUrl}</p>
              </div>
              <button
                type="button"
                onClick={handleCopy}
                className="shrink-0 rounded-xl border border-white/10 bg-white/10 p-2 text-white/80 hover:bg-white hover:text-black transition"
                title="Copia link"
              >
                <Icon icon={copied ? "ph:check-bold" : "ph:copy-bold"} className="h-4 w-4" />
              </button>
            </div>

            {/* Main Action Button */}
            <div className="space-y-2 pt-1">
              <a
                href={discordUrl}
                target="_blank"
                rel="noreferrer"
                className="flex w-full items-center justify-center gap-2 rounded-2xl bg-[#5865F2] hover:bg-[#4752C4] py-3.5 text-xs font-semibold text-white transition shadow-lg shadow-[#5865F2]/30"
              >
                <Icon icon="ph:discord-logo-fill" className="h-4 w-4" />
                <span>Entra nel Discord & Apri Ticket</span>
                <Icon icon="ph:arrow-up-right-bold" className="h-3.5 w-3.5" />
              </a>

              <p className="text-[11px] text-white/40">
                Un operatore prenderà in carico la richiesta e ti invierà la key istantaneamente.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
