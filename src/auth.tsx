import { useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { Icon } from "@iconify/react"
import { Dashboard } from "./dashboard"
import { saveSession, saveUser } from "./session"

function AuthField({
  label,
  type,
  value,
  onChange,
  autoComplete,
  maxLength,
}: {
  label: string
  type: string
  value: string
  onChange: (value: string) => void
  autoComplete: string
  maxLength?: number
}) {
  return (
    <label className="block">
      <span className="sr-only">{label}</span>
      <input
        className="auth-field"
        type={type}
        value={value}
        placeholder={label}
        autoComplete={autoComplete}
        maxLength={maxLength}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  )
}

function DiscordLoginButton({ mode = "login" }: { mode?: "login" | "register" }) {
  const [showQuickModal, setShowQuickModal] = useState(false)
  const [discordHandle, setDiscordHandle] = useState("")
  const navigate = useNavigate()

  const handleOAuthLogin = () => {
    window.location.href = "/api/auth/discord/login"
  }

  const handleQuickDiscordLogin = (e: React.FormEvent) => {
    e.preventDefault()
    const handle = discordHandle.trim()
    if (!handle) return

    const cleanUser = handle.replace(/^@/, "").replace(/#.*$/, "")
    const today = new Date().toISOString().slice(0, 10)
    const newUser = {
      username: cleanUser,
      displayName: handle,
      email: `${cleanUser.toLowerCase()}@discord.bytesint.xyz`,
      avatar: "terminal",
      credits: 20, // 20 crediti giornalieri rinnovabili a mezzanotte
      dailyCredits: 20,
      lastDailyRenewal: today,
      plan: "Free Tier",
      apiKey: `by_live_${Math.random().toString(36).substring(2, 14)}`,
      joinedAt: new Date().toLocaleDateString("en-US", { month: "short", year: "numeric" }),
      discordId: "quick_discord_session",
    }
    saveUser(newUser)
    navigate("/dashboard")
  }

  return (
    <div className="w-full space-y-2">
      <button
        type="button"
        onClick={handleOAuthLogin}
        className="flex w-full items-center justify-center gap-2.5 rounded-2xl bg-[#5865F2] px-5 py-3 text-sm font-medium text-white shadow-lg transition duration-200 hover:bg-[#4752C4] hover:shadow-[#5865F2]/25"
      >
        <Icon icon="ph:discord-logo-fill" className="h-5 w-5" />
        <span>{mode === "register" ? "Registrati con Discord" : "Accedi con Discord"}</span>
      </button>

      <div className="flex justify-center">
        <button
          type="button"
          onClick={() => setShowQuickModal(true)}
          className="text-[11px] text-white/40 hover:text-white/70 transition underline"
        >
          Problemi con il redirect OAuth? Accedi rapido con Discord ID
        </button>
      </div>

      {showQuickModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-md">
          <div className="glass max-w-sm w-full rounded-3xl border border-white/20 p-6 shadow-2xl animate-rise text-left">
            <div className="flex items-center gap-2 text-[#5865F2]">
              <Icon icon="ph:discord-logo-fill" className="h-6 w-6" />
              <h3 className="text-base font-semibold text-white">Accesso Rapido Discord</h3>
            </div>
            <p className="mt-2 text-xs text-white/60">
              Inserisci il tuo username Discord o ID per accedere istantaneamente con 20 crediti giornalieri (rinnovo automatico a mezzanotte).
            </p>
            <form onSubmit={handleQuickDiscordLogin} className="mt-4 space-y-3">
              <input
                type="text"
                value={discordHandle}
                onChange={(e) => setDiscordHandle(e.target.value)}
                placeholder="Es. username o handle#0000"
                className="w-full rounded-xl border border-white/20 bg-white/5 px-4 py-2.5 text-xs text-white outline-none focus:border-[#5865F2]"
                autoFocus
              />
              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowQuickModal(false)}
                  className="rounded-full px-4 py-1.5 text-xs text-white/60 hover:text-white"
                >
                  Annulla
                </button>
                <button
                  type="submit"
                  disabled={!discordHandle.trim()}
                  className="rounded-full bg-[#5865F2] px-5 py-1.5 text-xs font-semibold text-white hover:bg-[#4752C4] disabled:opacity-40"
                >
                  Entra Ora
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export function LoginPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const ready = username.trim().length > 0 && password.length > 0
  const errorMsg = searchParams.get("error")

  return (
    <main className="mx-auto flex min-h-[75vh] w-full max-w-sm flex-col justify-center px-6 pb-24 pt-32 animate-rise">
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
        <span className="text-[10px] uppercase font-mono tracking-widest text-white/50">AUTENTICAZIONE OSINT</span>
      </div>
      <h1 className="mt-2 text-3xl font-medium tracking-[-0.04em]">Accedi a bytesint</h1>
      <p className="mt-2 text-sm font-light text-white/60">Entra nel tuo workspace per condurre ricerche sui nodi.</p>

      {errorMsg && (
        <div className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-xs text-red-300">
          {errorMsg}
        </div>
      )}

      {/* Accesso con Discord */}
      <div className="mt-6">
        <DiscordLoginButton mode="login" />
      </div>

      <div className="my-6 flex items-center gap-3">
        <div className="h-px flex-1 bg-white/10" />
        <span className="text-[11px] uppercase tracking-wider text-white/40">oppure con credenziali</span>
        <div className="h-px flex-1 bg-white/10" />
      </div>

      <form
        className="flex flex-col gap-4"
        onSubmit={(event) => {
          event.preventDefault()
          if (!ready) return
          saveSession(username.trim())
          navigate("/dashboard")
        }}
      >
        <AuthField label="Username" type="text" value={username} onChange={setUsername} autoComplete="username" />
        <AuthField label="Password" type="password" value={password} onChange={setPassword} autoComplete="current-password" />
        <button
          type="submit"
          disabled={!ready}
          className={`mt-2 rounded-2xl py-2.5 text-sm font-medium transition ${
            ready ? "bg-white text-black hover:bg-white/90 shadow-md" : "cursor-not-allowed bg-white/10 text-white/35"
          }`}
        >
          Accedi
        </button>
      </form>
      <p className="mt-8 text-sm text-white/55 text-center">
        Non hai ancora un account?{" "}
        <Link to="/register" className="text-white hover:underline font-medium">
          Registrati qui
        </Link>
      </p>
    </main>
  )
}

export function RegisterPage() {
  const navigate = useNavigate()
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const userOk = /^[A-Za-z0-9]{3,20}$/.test(username)
  const passOk = password.length >= 8
  const confirmOk = confirm === password && confirm.length > 0
  const ready = userOk && passOk && confirmOk

  return (
    <main className="mx-auto flex min-h-[75vh] w-full max-w-sm flex-col justify-center px-6 pb-24 pt-32 animate-rise">
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
        <span className="text-[10px] uppercase font-mono tracking-widest text-emerald-400">REGISTRAZIONE OBBLIGATORIA</span>
      </div>
      <h1 className="mt-2 text-3xl font-medium tracking-[-0.04em]">Crea il tuo account</h1>
      <p className="mt-2 text-sm font-light text-white/60">
        Registrati per accedere alla piattaforma <strong>bytesint.xyz</strong>. Ricevi subito <strong>20 crediti giornalieri</strong> gratuiti che si rinnovano automaticamente ogni giorno a mezzanotte!
      </p>

      {/* Accesso con Discord */}
      <div className="mt-6">
        <DiscordLoginButton mode="register" />
      </div>

      <div className="my-6 flex items-center gap-3">
        <div className="h-px flex-1 bg-white/10" />
        <span className="text-[11px] uppercase tracking-wider text-white/40">oppure crea con password</span>
        <div className="h-px flex-1 bg-white/10" />
      </div>

      <form
        className="flex flex-col gap-4"
        onSubmit={(event) => {
          event.preventDefault()
          if (!ready) return
          saveSession(username)
          navigate("/dashboard")
        }}
      >
        <div>
          <AuthField label="Username" type="text" value={username} onChange={setUsername} autoComplete="username" maxLength={20} />
          <p className={`mt-1.5 text-xs ${username.length > 0 && !userOk ? "text-amber-400" : "text-white/40"}`}>
            3–20 lettere o numeri
          </p>
        </div>
        <div>
          <AuthField label="Password" type="password" value={password} onChange={setPassword} autoComplete="new-password" />
          <p className={`mt-1.5 text-xs ${password.length > 0 && !passOk ? "text-amber-400" : "text-white/40"}`}>
            Almeno 8 caratteri
          </p>
        </div>
        <div>
          <AuthField label="Conferma password" type="password" value={confirm} onChange={setConfirm} autoComplete="new-password" />
          {confirm.length > 0 && !confirmOk ? <p className="mt-1.5 text-xs text-red-400">Le password non coincidono</p> : null}
        </div>
        <button
          type="submit"
          disabled={!ready}
          className={`mt-2 rounded-2xl py-2.5 text-sm font-medium transition ${
            ready ? "bg-white text-black hover:bg-white/90 shadow-md" : "cursor-not-allowed bg-white/10 text-white/35"
          }`}
        >
          Crea Account & Inizia
        </button>
      </form>
      <p className="mt-8 text-sm text-white/55 text-center">
        Hai già un account?{" "}
        <Link to="/login" className="text-white hover:underline font-medium">
          Accedi qui
        </Link>
      </p>
    </main>
  )
}

export function DashboardPage() {
  return <Dashboard />
}
