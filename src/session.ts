import { useEffect, useState } from "react"

export interface UserProfile {
  username: string
  displayName: string
  email: string
  avatar: string
  credits: number
  plan: string
  apiKey: string
  joinedAt: string
  lastDailyRenewal?: string // Data YYYY-MM-DD dell'ultimo accredito giornaliero
  dailyCredits?: number    // Quota crediti giornalieri (20)
}

export const DAILY_CREDITS = 20

export function getTodayString(): string {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, "0")
  const d = String(now.getDate()).padStart(2, "0")
  return `${y}-${m}-${d}`
}

export function getTimeUntilMidnight(): { hours: number; minutes: number; formatted: string } {
  const now = new Date()
  const midnight = new Date(now)
  midnight.setHours(24, 0, 0, 0)
  const diffMs = midnight.getTime() - now.getTime()
  const totalMinutes = Math.max(0, Math.floor(diffMs / 60000))
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  return {
    hours,
    minutes,
    formatted: `${hours}h ${minutes}m`,
  }
}

export function applyDailyCreditsRenewal(profile: UserProfile): { profile: UserProfile; renewed: boolean } {
  const today = getTodayString()

  // Se è un profilo al primo tracciamento
  if (!profile.lastDailyRenewal) {
    profile.lastDailyRenewal = today
    profile.dailyCredits = DAILY_CREDITS
    if (typeof profile.credits !== "number" || profile.credits < DAILY_CREDITS) {
      profile.credits = DAILY_CREDITS
    }
    return { profile, renewed: false }
  }

  // Se è passata la mezzanotte!
  if (profile.lastDailyRenewal !== today) {
    profile.lastDailyRenewal = today
    profile.dailyCredits = DAILY_CREDITS
    // Rinnovo: se ha esaurito o intaccato i 20 crediti, tornano a 20.
    // Se ha crediti extra, riceve il bonus giornaliero di 20 crediti!
    if (profile.credits < DAILY_CREDITS) {
      profile.credits = DAILY_CREDITS
    } else {
      profile.credits += DAILY_CREDITS
    }
    return { profile, renewed: true }
  }

  return { profile, renewed: false }
}

export interface SearchRecord {
  id: string
  module: string
  query: string
  timestamp: string
  status: "success" | "no_results"
  resultsCount: number
  summary: string
}

const USER_KEY = "bytesint_user_session"
const HISTORY_KEY = "bytesint_search_history"
const AUTH_EVENT = "bytesint-auth-change"

export const AVATAR_OPTIONS = [
  { id: "shield", label: "Sentinel", icon: "ph:shield-check-fill" },
  { id: "terminal", label: "Operator", icon: "ph:terminal-window-fill" },
  { id: "radar", label: "Scanner", icon: "ph:radar-fill" },
  { id: "ghost", label: "Ghost", icon: "ph:ghost-fill" },
  { id: "cpu", label: "Neural", icon: "ph:cpu-fill" },
  { id: "fingerprint", label: "Trace", icon: "fa6-solid:fingerprint" },
]

function generateApiKey(): string {
  const chars = "abcdef0123456789"
  let key = "bytes_live_"
  for (let i = 0; i < 24; i++) {
    key += chars[Math.floor(Math.random() * chars.length)]
  }
  return key
}

export function getUser(): UserProfile | null {
  try {
    if (typeof window === "undefined") return null

    // Helper to safely clear auth cookie
    const clearAuthCookie = () => {
      try {
        if (typeof document !== "undefined") {
          document.cookie = "bytesint_auth=; Path=/; Max-Age=0; SameSite=Lax; expires=Thu, 01 Jan 1970 00:00:00 GMT"
        }
      } catch {}
    }

    // 1. Check URL parameters for OAuth session handoff
    if (window.location.search) {
      const searchParams = new URLSearchParams(window.location.search)
      const sessionData = searchParams.get("session") || searchParams.get("user")
      if (sessionData) {
        try {
          let jsonStr = ""
          try {
            jsonStr = atob(decodeURIComponent(sessionData))
          } catch {
            try {
              jsonStr = atob(sessionData)
            } catch {
              jsonStr = decodeURIComponent(sessionData)
            }
          }
          const parsed = JSON.parse(jsonStr)
          if (parsed && (parsed.username || parsed.displayName)) {
            let existingCredits = typeof parsed.credits === "number" ? parsed.credits : 100
            try {
              const currentRaw = localStorage.getItem(USER_KEY)
              if (currentRaw) {
                const cur = JSON.parse(currentRaw)
                if (cur && cur.username === (parsed.username || cur.username) && typeof cur.credits === "number") {
                  existingCredits = Math.max(cur.credits, existingCredits)
                }
              }
            } catch {}

            const rawProfile: UserProfile = {
              username: String(parsed.username || "operator").trim(),
              displayName: String(parsed.displayName || parsed.username || "Operator"),
              email: String(parsed.email || `${parsed.username}@discord.bytesint.xyz`),
              avatar: String(parsed.avatar || "terminal"),
              credits: existingCredits,
              plan: String(parsed.plan || "Discord Operator"),
              apiKey: String(parsed.apiKey || generateApiKey()),
              joinedAt: String(parsed.joinedAt || "Today"),
              lastDailyRenewal: parsed.lastDailyRenewal || getTodayString(),
              dailyCredits: DAILY_CREDITS,
            }

            const { profile: userProfile } = applyDailyCreditsRenewal(rawProfile)

            const data = JSON.stringify(userProfile)
            localStorage.setItem(USER_KEY, data)
            sessionStorage.setItem(USER_KEY, data)
            clearAuthCookie()

            const cleanUrl = window.location.pathname
            window.history.replaceState({}, document.title, cleanUrl)
            return userProfile
          }
        } catch (e) {
          console.error("Failed to parse session from URL:", e)
        }
      }
    }

    // 2. Read from localStorage (primary source of truth)
    const raw =
      localStorage.getItem(USER_KEY) ||
      sessionStorage.getItem(USER_KEY) ||
      localStorage.getItem("detrace_user_session")

    if (raw) {
      let parsed: any = null
      try {
        parsed = JSON.parse(raw)
      } catch {
        parsed = raw
      }

      // Clean up old placeholder user if present
      if (parsed && typeof parsed === "object" && parsed.username === "asdasdas") {
        localStorage.removeItem(USER_KEY)
        sessionStorage.removeItem(USER_KEY)
        return null
      }

      if (typeof parsed === "string" && parsed.trim().length > 0) {
        const u = parsed.trim()
        const userObj: UserProfile = {
          username: u,
          displayName: u,
          email: `${u.toLowerCase()}@bytesint.xyz`,
          avatar: "terminal",
          credits: DAILY_CREDITS,
          plan: "Free Tier",
          apiKey: generateApiKey(),
          joinedAt: "Today",
          lastDailyRenewal: getTodayString(),
          dailyCredits: DAILY_CREDITS,
        }
        localStorage.setItem(USER_KEY, JSON.stringify(userObj))
        return userObj
      }

      if (parsed && typeof parsed === "object" && parsed.username) {
        const u = String(parsed.username).trim()
        const userObj: UserProfile = {
          username: u,
          displayName: String(parsed.displayName || u),
          email: String(parsed.email || `${u.toLowerCase()}@bytesint.xyz`),
          avatar: String(parsed.avatar || "terminal"),
          credits: typeof parsed.credits === "number" ? parsed.credits : DAILY_CREDITS,
          plan: String(parsed.plan || "Free Tier"),
          apiKey: String(parsed.apiKey || generateApiKey()),
          joinedAt: String(parsed.joinedAt || "Today"),
          lastDailyRenewal: parsed.lastDailyRenewal,
          dailyCredits: typeof parsed.dailyCredits === "number" ? parsed.dailyCredits : DAILY_CREDITS,
        }

        const { profile: renewedProfile, renewed } = applyDailyCreditsRenewal(userObj)
        if (renewed || !parsed.lastDailyRenewal) {
          const data = JSON.stringify(renewedProfile)
          localStorage.setItem(USER_KEY, data)
          sessionStorage.setItem(USER_KEY, data)
        }
        return renewedProfile
      }
    }

    // 3. Fallback: Check Cookie only if localStorage had nothing
    if (typeof document !== "undefined" && document.cookie) {
      const match = document.cookie.match(/(?:^|;\s*)bytesint_auth=([^;]+)/)
      if (match && match[1]) {
        try {
          const cookieVal = decodeURIComponent(match[1])
          let jsonStr = ""
          try {
            jsonStr = atob(cookieVal)
          } catch {
            jsonStr = cookieVal
          }
          const parsed = JSON.parse(jsonStr)
          if (parsed && (parsed.username || parsed.displayName)) {
            const userProfile: UserProfile = {
              username: String(parsed.username || "operator").trim(),
              displayName: String(parsed.displayName || parsed.username || "Operator"),
              email: String(parsed.email || `${parsed.username}@discord.bytesint.xyz`),
              avatar: String(parsed.avatar || "terminal"),
              credits: typeof parsed.credits === "number" ? parsed.credits : 100,
              plan: String(parsed.plan || "Discord Operator"),
              apiKey: String(parsed.apiKey || generateApiKey()),
              joinedAt: String(parsed.joinedAt || "Today"),
            }
            clearAuthCookie()
            const data = JSON.stringify(userProfile)
            localStorage.setItem(USER_KEY, data)
            sessionStorage.setItem(USER_KEY, data)
            return userProfile
          }
        } catch (e) {}
      }
    }

    return null
  } catch {
    return null
  }
}

export async function redeemLicenseKey(rawKey: string): Promise<{ success: boolean; creditsAdded?: number; newBalance?: number; message?: string; error?: string }> {
  const user = getUser()
  if (!user) {
    return { success: false, error: "Devi prima effettuare l'accesso per riscattare una chiave." }
  }

  let cleanKey = String(rawKey || "").trim().toUpperCase().replace(/\s+/g, "")
  if (!cleanKey) {
    return { success: false, error: "Inserisci un codice licenza valido." }
  }

  if (!cleanKey.startsWith("BYTES-") && !cleanKey.includes("-")) {
    cleanKey = `BYTES-${cleanKey}`
  }

  try {
    const res = await fetch("/api/keys/redeem", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: cleanKey, username: user.username }),
    })

    const data = await res.json()
    if (res.ok && data.success) {
      const added = Number(data.creditsAdded || 50)
      const newBal = addCredits(added)
      return {
        success: true,
        creditsAdded: added,
        newBalance: newBal,
        message: data.message || `Chiave riscattata con successo! +${added} crediti accreditati.`,
      }
    } else {
      return {
        success: false,
        error: data.error || "Codice licenza non valido o già utilizzato.",
      }
    }
  } catch (netErr) {
    return {
      success: false,
      error: "Errore di connessione al server per il riscatto della chiave. Verifica che il server sia attivo.",
    }
  }
}

export function saveUser(profile: UserProfile): void {
  if (!profile.lastDailyRenewal) {
    profile.lastDailyRenewal = getTodayString()
  }
  if (!profile.dailyCredits) {
    profile.dailyCredits = DAILY_CREDITS
  }
  const data = JSON.stringify(profile)
  localStorage.setItem(USER_KEY, data)
  sessionStorage.setItem(USER_KEY, data)
  window.dispatchEvent(new Event(AUTH_EVENT))
}

export function updateProfile(updates: Partial<UserProfile>): UserProfile | null {
  const current = getUser()
  if (!current) return null
  const updated: UserProfile = { ...current, ...updates }
  saveUser(updated)
  return updated
}

export function login(username: string, email?: string): UserProfile {
  const existing = getUser()
  const cleanUser = username.trim()
  const today = getTodayString()
  
  if (existing && existing.username.toLowerCase() === cleanUser.toLowerCase()) {
    const { profile: refreshed, renewed } = applyDailyCreditsRenewal(existing)
    if (renewed) saveUser(refreshed)
    return refreshed
  }

  // Nuovo utente / primo login: 20 crediti giornalieri
  const profile: UserProfile = {
    username: cleanUser,
    displayName: cleanUser,
    email: email?.trim() || `${cleanUser.toLowerCase()}@bytesint.xyz`,
    avatar: "terminal",
    credits: DAILY_CREDITS, // 20 crediti al primo accesso
    dailyCredits: DAILY_CREDITS,
    lastDailyRenewal: today,
    plan: "Free Tier",
    apiKey: generateApiKey(),
    joinedAt: new Date().toLocaleDateString("en-US", { month: "short", year: "numeric" }),
  }

  saveUser(profile)
  return profile
}

export function logout(): void {
  localStorage.removeItem(USER_KEY)
  sessionStorage.removeItem(USER_KEY)
  try {
    if (typeof document !== "undefined") {
      document.cookie = "bytesint_auth=; Path=/; Max-Age=0; SameSite=Lax; expires=Thu, 01 Jan 1970 00:00:00 GMT"
    }
  } catch {}
  window.dispatchEvent(new Event(AUTH_EVENT))
}

export function deductCredit(amount = 1): boolean {
  const user = getUser()
  if (!user || user.credits < amount) return false
  user.credits -= amount
  saveUser(user)
  return true
}

export function addCredits(amount: number): number {
  const user = getUser()
  if (!user) return 0
  user.credits += amount
  saveUser(user)
  return user.credits
}

export function regenerateApiKey(): string {
  const newKey = generateApiKey()
  updateProfile({ apiKey: newKey })
  return newKey
}

export function getSearchHistory(): SearchRecord[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY)
    if (!raw) return []
    return JSON.parse(raw) as SearchRecord[]
  } catch {
    return []
  }
}

export function addSearchRecord(record: SearchRecord): void {
  try {
    const history = getSearchHistory()
    const updated = [record, ...history.filter((r) => r.id !== record.id)].slice(0, 50)
    localStorage.setItem(HISTORY_KEY, JSON.stringify(updated))
  } catch {
    // ignore
  }
}

export function clearSearchHistory(): void {
  localStorage.removeItem(HISTORY_KEY)
}

// React Hook for real-time reactivity across Header, Dashboard, Pages
export function useUserSession() {
  const [user, setUser] = useState<UserProfile | null>(() => getUser())

  useEffect(() => {
    const handleAuthChange = () => {
      setUser(getUser())
    }

    window.addEventListener(AUTH_EVENT, handleAuthChange)
    window.addEventListener("storage", handleAuthChange)

    // Controllo periodico del rinnovo a mezzanotte (ogni 15s)
    const midnightInterval = setInterval(() => {
      const refreshed = getUser()
      if (refreshed) {
        setUser((prev) => {
          if (!prev) return refreshed
          if (prev.credits !== refreshed.credits || prev.lastDailyRenewal !== refreshed.lastDailyRenewal) {
            return refreshed
          }
          return prev
        })
      }
    }, 15000)

    return () => {
      window.removeEventListener(AUTH_EVENT, handleAuthChange)
      window.removeEventListener("storage", handleAuthChange)
      clearInterval(midnightInterval)
    }
  }, [])

  return user
}

// Backwards compatibility functions
export function readSession() {
  const u = getUser()
  return u ? u.username : null
}

export function saveSession(username: string) {
  login(username)
}

export function clearSession() {
  logout()
}
