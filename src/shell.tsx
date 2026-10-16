import { Icon } from "@iconify/react"
import Lenis from "lenis"
import { useEffect, useState, type ReactNode } from "react"
import { Link, useLocation } from "react-router-dom"
import { ConstellationBackground } from "@/components/ui/constellation-background"
import { GradientBackground } from "@/components/ui/paper-design-shader-background"
import { BrandMark, brands } from "./components/brands"
import { useUserSession } from "./session"

function FooterCol({ title, links }: { title: string; links: Array<[string, string]> }) {
  return (
    <div>
      <h4 className="text-sm font-medium uppercase tracking-[0.08em]">{title}</h4>
      <ul className="mt-4 space-y-3 text-sm font-light text-white/70">
        {links.map(([label, href]) => (
          <li key={label}>
            {href.startsWith("http") ? (
              <a href={href} target="_blank" rel="noreferrer" className="transition-colors duration-200 hover:text-white">
                {label}
              </a>
            ) : (
              <Link to={href} className="transition-colors duration-200 hover:text-white">
                {label}
              </Link>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

function BrandLink({ slug, label, to }: { slug: string; label: string; to: string }) {
  const icon = brands.find((item) => item.slug === slug) ?? brands[0]
  if (to.startsWith("http")) {
    return (
      <a href={to} target="_blank" rel="noreferrer" aria-label={label} className="text-white transition-opacity duration-200 hover:opacity-65">
        <BrandMark icon={icon} className="h-[22px] w-[22px]" />
      </a>
    )
  }
  return (
    <Link to={to} aria-label={label} className="text-white transition-opacity duration-200 hover:opacity-65">
      <BrandMark icon={icon} className="h-[22px] w-[22px]" />
    </Link>
  )
}

const centerLinks = [
  ["/pricing", "Pricing"],
  ["/documentation", "Docs"],
  ["/contact", "Contact"],
  ["/faq", "FAQ"],
] as const

export function Shell({ children }: { children: ReactNode }) {
  const location = useLocation()
  const user = useUserSession()
  const [compact, setCompact] = useState(false)
  const [logoOk, setLogoOk] = useState(true)

  useEffect(() => {
    if (location.pathname === "/dashboard") {
      return
    }

    let lenis: Lenis | null = null
    let frame = 0
    try {
      lenis = new Lenis({
        duration: 1.05,
        smoothWheel: true,
      })
      const onScroll = (instance: Lenis) => sync(instance.scroll)
      const sync = (scroll: number) => {
        setCompact((prev) => {
          if (!prev && scroll > 80) return true
          if (prev && scroll < 24) return false
          return prev
        })
      }
      lenis.on("scroll", onScroll)
      const onNative = () => sync(window.scrollY || document.documentElement.scrollTop)
      window.addEventListener("scroll", onNative, { passive: true })
      const loop = (time: number) => {
        lenis?.raf(time)
        frame = requestAnimationFrame(loop)
      }
      frame = requestAnimationFrame(loop)
      setCompact(false)
      return () => {
        cancelAnimationFrame(frame)
        window.removeEventListener("scroll", onNative)
        lenis?.destroy()
      }
    } catch {
      // Graceful fallback
    }
  }, [location.pathname])

  if (location.pathname === "/dashboard") {
    return (
      <div className="relative min-h-screen overflow-x-hidden text-white">
        {/* Landing page silky shader background */}
        <div className="pointer-events-none fixed inset-0 -z-30">
          <GradientBackground />
        </div>
        {/* Constellation particle network + animated circle radar/sonar */}
        <ConstellationBackground />
        {children}
      </div>
    )
  }

  return (
    <div className="relative min-h-screen overflow-x-hidden text-white">
      <div className="pointer-events-none fixed inset-0 -z-20">
        <GradientBackground />
      </div>
      <ConstellationBackground />

      <header className="fixed inset-x-0 top-0 z-50 px-4 pt-4">
        <div className="glass mx-auto grid w-full max-w-5xl grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 rounded-full px-3 py-2.5 sm:px-7 sm:py-3 md:grid-cols-[1fr_auto_1fr] md:gap-0">
          <div className="flex min-w-0 items-center gap-2 sm:gap-3">
            <Link to="/" className="flex shrink-0 items-center" aria-label="bytesint.xyz">
              {logoOk ? (
                <img
                  src="/logo.gif"
                  alt="bytesint"
                  width={44}
                  height={44}
                  className={`object-cover rounded-xl border border-white/10 transition-[width,height] duration-700 ease-[cubic-bezier(0.22,1,0.36,1)] ${compact ? "h-6 w-6 sm:h-7 sm:w-7" : "h-8 w-8 sm:h-10 sm:w-10"}`}
                  onError={() => setLogoOk(false)}
                />
              ) : (
                <Icon
                  icon="ph:detective-bold"
                  className={`transition-all duration-700 ease-[cubic-bezier(0.22,1,0.36,1)] ${compact ? "h-5 w-5 sm:h-6 sm:w-6" : "h-7 w-7 sm:h-8 sm:w-8"}`}
                  aria-hidden
                />
              )}
            </Link>
            <Link
              to="/"
              className={`overflow-hidden whitespace-nowrap text-base font-medium tracking-[-0.04em] transition-[max-width,opacity] duration-700 ease-[cubic-bezier(0.22,1,0.36,1)] sm:text-lg ${
                compact ? "max-w-0 opacity-0" : "max-w-[7.5rem] opacity-100"
              }`}
            >
              bytesint.xyz
            </Link>
          </div>
          <nav className="flex items-center justify-center gap-2.5 text-[11px] text-white/70 sm:gap-8 sm:text-sm md:gap-10">
            {centerLinks.map(([href, label]) => {
              const active = location.pathname === href
              return (
                <Link key={href} to={href} className={active ? "text-white" : "hover:text-white"}>
                  {label}
                </Link>
              )
            })}
          </nav>
          <div className="flex items-center justify-end gap-2 text-[11px] sm:gap-4 sm:text-sm">
            {user ? (
              <div className="flex items-center gap-2 sm:gap-3">
                <Link
                  to="/dashboard"
                  className={`inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-medium transition ${
                    location.pathname === "/dashboard"
                      ? "bg-white text-black shadow-md"
                      : "border border-white/20 bg-white/10 text-white hover:bg-white/20"
                  }`}
                >
                  <Icon icon="fa6-solid:gauge-high" className="h-3 w-3" />
                  Dashboard
                </Link>
                <Link
                  to="/dashboard"
                  className="hidden items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white/80 hover:text-white sm:inline-flex"
                  title="Your account"
                >
                  <span className="font-mono text-white/50 text-[11px]">{user.credits} cr</span>
                  <span className="max-w-[80px] truncate text-white/70">@{user.username}</span>
                </Link>
              </div>
            ) : (
              <div className="flex items-center gap-2 sm:gap-2.5">
                <Link
                  to="/login"
                  className="rounded-full border border-white/20 bg-white/5 px-3 py-1.5 text-xs font-medium text-white/90 hover:bg-white/15 hover:text-white transition"
                >
                  Accedi
                </Link>
                <Link
                  to="/register"
                  className="rounded-full bg-white px-3.5 py-1.5 text-xs font-semibold text-black hover:bg-white/90 transition shadow-md"
                >
                  Registrati
                </Link>
              </div>
            )}
          </div>
        </div>
      </header>

      {children}

      <footer className="relative z-10 bg-transparent px-6 pb-10 pt-16 text-left text-white">
        <div className="mx-auto grid max-w-6xl gap-12 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:items-start">
          <div>
            <div className="flex items-center gap-3">
              {logoOk ? <img src="/logo.gif" alt="" className="h-9 w-9 object-cover rounded-xl border border-white/10" /> : null}
              <h3 className="text-2xl font-medium tracking-[-0.04em]">bytesint.xyz</h3>
            </div>
            <p className="mt-4 max-w-md text-sm font-light leading-relaxed text-white/70">
              Public, source-linked intelligence for people who need the record next to the claim.
            </p>
            <div className="mt-6 flex items-center gap-4">
              <BrandLink slug="discord" label="bytesint.xyz on Discord" to="https://discord.gg/T5pZgFbGE" />
              <BrandLink slug="telegram" label="bytesint.xyz contact" to="/contact" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
            <FooterCol title="Community" links={[["Help", "/help"], ["Contact", "/contact"], ["Discord", "https://discord.gg/T5pZgFbGE"]]} />
            <FooterCol title="Resources" links={[["Documentation", "/documentation"], ["Sign in", "/login"], ["Create account", "/register"]]} />
            <FooterCol title="Product" links={[["Pricing", "/pricing"], ["Status", "/status"], ["FAQ", "/faq"]]} />
            <FooterCol title="Legal" links={[["Terms of Service", "/terms"], ["Privacy Policy", "/privacy"], ["Legal notice", "/legal"], ["EULA", "/eula"]]} />
          </div>
          <div className="flex flex-col items-start justify-between gap-4 pt-4 text-sm text-white/60 sm:flex-row sm:items-center lg:col-span-2">
            <p>© 2026 bytesint.xyz. All rights reserved.</p>
            <div className="flex gap-6">
              <Link to="/terms" className="hover:text-white">Terms of Service</Link>
              <Link to="/privacy" className="hover:text-white">Privacy Policy</Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
