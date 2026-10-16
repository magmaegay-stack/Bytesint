import { Icon } from "@iconify/react"
import { useState } from "react"
import { Link } from "react-router-dom"
import { BrandMark, brands } from "./components/brands"
import { advancedPacks, questions, starterPacks, type PackSide } from "./data"
import { PackSwitch, RisingPrice } from "./pricing-ui"
import { useUserSession } from "./session"
import { DiscordTicketModal } from "./DiscordTicketModal"

function PageIntro({ icon, kicker, title, copy }: { icon: string; kicker: string; title: string; copy: string }) {
  return (
    <header className="mx-auto max-w-2xl text-center">
      <Icon icon={icon} className="mx-auto h-8 w-8" aria-hidden />
      <p className="mt-5 text-xs uppercase tracking-[0.28em] text-white/50">{kicker}</p>
      <h1 className="mt-3 text-4xl font-medium tracking-[-0.04em] md:text-5xl">{title}</h1>
      <p className="mt-4 text-sm font-light leading-relaxed text-white/70">{copy}</p>
    </header>
  )
}

export function ContactPage() {
  const [sent, setSent] = useState(false)
  return (
    <main className="mx-auto max-w-xl px-6 pb-24 pt-32 text-center">
      <PageIntro
        icon="fa6-solid:comments"
        kicker="Contact"
        title="Write to the workspace."
        copy="Questions about packs, a source line, or the product. This preview keeps the note on the page. It is not sent to a server."
      />
      <form
        className="mt-10 flex flex-col gap-6 text-left"
        onSubmit={(event) => {
          event.preventDefault()
          setSent(true)
        }}
      >
        <label className="block text-center">
          <Icon icon="fa6-solid:user" className="mx-auto h-5 w-5" aria-hidden />
          <input className="auth-field mt-2" name="name" placeholder="Name" autoComplete="name" required />
        </label>
        <label className="block text-center">
          <Icon icon="fa6-solid:envelope" className="mx-auto h-5 w-5" aria-hidden />
          <input className="auth-field mt-2" type="email" name="email" placeholder="Email" autoComplete="email" required />
        </label>
        <label className="block text-center">
          <Icon icon="fa6-solid:file-lines" className="mx-auto h-5 w-5" aria-hidden />
          <textarea className="auth-field mt-2 min-h-28 resize-y" name="note" placeholder="Note" required />
        </label>
        <button type="submit" className="mx-auto rounded-full bg-white px-6 py-2.5 text-sm text-black">
          Leave a note
        </button>
      </form>
      {sent ? <p className="mt-6 text-sm text-white/70">Noted in this preview only. Nothing was transmitted.</p> : null}
      <div className="mt-10 flex justify-center gap-8 text-sm text-white/70">
        <Link to="/help" className="hover:text-white">Help</Link>
        <a href="https://discord.gg/T5pZgFbGE" target="_blank" rel="noreferrer" className="hover:text-white">Discord</a>
      </div>
    </main>
  )
}

export function PricingPage() {
  const user = useUserSession()
  const [pack, setPack] = useState<PackSide>("starter")
  const [index, setIndex] = useState(1)
  const [fromPrice, setFromPrice] = useState<number | null>(null)
  const [ticketModal, setTicketModal] = useState<{ open: boolean; planName?: string; planPrice?: number }>({ open: false })
  const plans = pack === "starter" ? starterPacks : advancedPacks
  const plan = plans[index] ?? plans[0]

  function choosePack(next: PackSide) {
    if (next === pack) return
    setFromPrice(plan.price)
    setPack(next)
  }

  function chooseIndex(next: number) {
    if (next === index) return
    setFromPrice(plan.price)
    setIndex(next)
  }

  return (
    <main className="mx-auto max-w-xl px-6 pb-24 pt-32 text-center">
      <PageIntro
        icon="fa6-solid:wallet"
        kicker="Pricing"
        title="One-time packs."
        copy="The same prices as the landing. One pack at a time, price first, the rest underneath."
      />
      <div className="panel mx-auto mt-10 rounded-3xl px-6 py-10">
        <PackSwitch pack={pack} onChange={choosePack} />
        <div className="mt-8 flex items-center justify-center gap-6">
          <button type="button" aria-label="Previous pack" onClick={() => chooseIndex((index + plans.length - 1) % plans.length)} className="text-white/70 hover:text-white">
            <Icon icon="fa6-solid:chevron-left" className="h-4 w-4" aria-hidden />
          </button>
          <div className="flex gap-5">
            {plans.map((item, itemIndex) => (
              <button
                key={item.name}
                type="button"
                onClick={() => chooseIndex(itemIndex)}
                className={`text-sm transition-colors ${itemIndex === index ? "text-white" : "text-white/40 hover:text-white"}`}
              >
                {item.name}
              </button>
            ))}
          </div>
          <button type="button" aria-label="Next pack" onClick={() => chooseIndex((index + 1) % plans.length)} className="text-white/70 hover:text-white">
            <Icon icon="fa6-solid:chevron-right" className="h-4 w-4" aria-hidden />
          </button>
        </div>
        <div key={`${pack}-${plan.name}`} className="animate-rise mt-8">
          {plan.popular ? <p className="text-[11px] uppercase tracking-[0.18em] text-white/45">Most popular</p> : <p className="h-4" aria-hidden />}
          <p className="mt-2 text-6xl font-medium tracking-[-0.05em] md:text-7xl">
            €<RisingPrice value={plan.price} from={fromPrice ?? plan.price} />
          </p>
          <p className="mt-2 text-sm text-white/50">una tantum</p>
          <p className="mt-2 text-sm text-white/75">
            {plan.credits.toLocaleString()} crediti · €{plan.per} / credito
          </p>
          <ul className="mx-auto mt-8 grid max-w-sm gap-3 text-left">
            {plan.features.map((feature) => (
              <li key={feature.label} className={`flex items-center gap-2 text-sm ${feature.off ? "text-white/40" : "text-white/85"}`}>
                <Icon icon={feature.off ? "fa6-solid:circle-xmark" : "fa6-solid:circle-check"} className="h-4 w-4 shrink-0" aria-hidden />
                {feature.label}
              </li>
            ))}
          </ul>
          <button
            type="button"
            onClick={() => setTicketModal({ open: true, planName: plan.name, planPrice: plan.price })}
            className="mt-8 inline-flex items-center gap-2 rounded-full bg-white px-7 py-3 text-sm font-semibold text-black transition-all hover:bg-neutral-200 active:scale-95 shadow-lg shadow-white/10"
          >
            <Icon icon="fa6-brands:discord" className="h-4 w-4 text-[#5865F2]" />
            <span>Acquista Pacchetto</span>
          </button>
        </div>
      </div>

      <DiscordTicketModal
        isOpen={ticketModal.open}
        onClose={() => setTicketModal({ open: false })}
        isLoggedIn={Boolean(user)}
        planName={ticketModal.planName}
        planPrice={ticketModal.planPrice}
      />
    </main>
  )
}

const services = [
  { icon: "fa6-solid:fingerprint", name: "Workspace", state: "Operational" },
  { icon: "fa6-solid:wallet", name: "Credits", state: "Operational" },
  { icon: "fa6-solid:link", name: "Source links", state: "Operational" },
  { icon: "fa6-solid:file-lines", name: "PDF export", state: "Operational" },
]

export function StatusPage() {
  return (
    <main className="mx-auto max-w-xl px-6 pb-24 pt-32 text-center">
      <PageIntro
        icon="fa6-solid:gauge-high"
        kicker="Status"
        title="All systems operational."
        copy="A quiet reading of the product surfaces. This page is part of the preview and is not a live probe."
      />
      <ul className="mx-auto mt-10 grid max-w-md gap-6">
        {services.map((service) => (
          <li key={service.name} className="flex items-center justify-between gap-4 text-left">
            <span className="flex items-center gap-3">
              <Icon icon={service.icon} className="h-5 w-5" aria-hidden />
              {service.name}
            </span>
            <span className="flex items-center gap-2 text-sm text-white/70">
              <Icon icon="fa6-solid:circle-check" className="h-4 w-4 text-white" aria-hidden />
              {service.state}
            </span>
          </li>
        ))}
      </ul>
    </main>
  )
}

export function FaqPage() {
  const [open, setOpen] = useState<string | null>(questions[0]?.q ?? null)
  return (
    <main className="mx-auto max-w-xl px-6 pb-24 pt-32">
      <PageIntro icon="fa6-solid:circle-question" kicker="FAQ" title="Short answers." copy="The same questions as the landing, on their own page." />
      <div className="mt-10 text-left">
        {questions.map((item) => {
          const expanded = open === item.q
          return (
            <div key={item.q}>
              <button type="button" aria-expanded={expanded} onClick={() => setOpen(expanded ? null : item.q)} className="flex w-full items-center justify-between gap-4 py-4 text-left">
                <span className={`text-sm ${expanded ? "text-white" : "text-white/60"}`}>{item.q}</span>
                <Icon icon="fa6-solid:chevron-down" className={`h-3.5 w-3.5 shrink-0 transition-transform duration-300 ${expanded ? "rotate-180" : ""}`} aria-hidden />
              </button>
              <div className={`grid transition-[grid-template-rows] duration-500 ease-out ${expanded ? "grid-rows-[1fr]" : "grid-rows-[0fr]"}`}>
                <div className="overflow-hidden">
                  <p className={`pb-4 text-sm font-light leading-relaxed text-white/75 ${expanded ? "opacity-100" : "opacity-0"}`}>{item.a}</p>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </main>
  )
}

export function HelpPage() {
  const items = [
    { icon: "fa6-solid:user", title: "Sign in", copy: "Username and password only. Continue reveals the Cloudflare check. Authenticate stays gray until that check finishes." },
    { icon: "fa6-solid:envelope", title: "Create an account", copy: "Three steps: handle and password, email and a one-time code, then the same Cloudflare check." },
    { icon: "fa6-solid:wallet", title: "Credits", copy: "Packs are one-time. Starter runs from $4.99 to $19.99. Advanced runs from $34.99 to $99.99. There is no subscription." },
    { icon: "fa6-solid:link", title: "Source links", copy: "A useful line stays attached to where it was found. Open the origin, quote it, or throw the line out." },
  ]
  return (
    <main className="mx-auto max-w-2xl px-6 pb-24 pt-32 text-center">
      <PageIntro icon="fa6-solid:life-ring" kicker="Help" title="How the preview moves." copy="A short map of the pages. Lookups are not running here." />
      <ul className="mt-10 grid gap-8 text-left sm:grid-cols-2">
        {items.map((item) => (
          <li key={item.title}>
            <Icon icon={item.icon} className="h-6 w-6" aria-hidden />
            <h2 className="mt-3 text-lg font-medium">{item.title}</h2>
            <p className="mt-2 text-sm font-light leading-relaxed text-white/70">{item.copy}</p>
          </li>
        ))}
      </ul>
      <div className="mt-10 flex justify-center gap-6 text-sm">
        <Link to="/faq" className="text-white/70 hover:text-white">FAQ</Link>
        <Link to="/documentation" className="text-white/70 hover:text-white">Documentation</Link>
        <Link to="/contact" className="text-white/70 hover:text-white">Contact</Link>
      </div>
    </main>
  )
}

export function DiscordPage() {
  const discord = brands.find((icon) => icon.slug === "discord") ?? brands[0]
  return (
    <main className="mx-auto max-w-xl px-6 pb-24 pt-32 text-center">
      <BrandMark icon={discord} className="mx-auto h-12 w-12" />
      <p className="mt-5 text-xs uppercase tracking-[0.28em] text-white/50">Discord</p>
      <h1 className="mt-3 text-4xl font-medium tracking-[-0.04em]">Join the community</h1>
      <p className="mt-4 text-sm font-light leading-relaxed text-white/70">
        Connect with our analysts, get quick support, and stay updated on database releases.
      </p>
      <div className="mt-8 flex items-center justify-center gap-4">
        <a
          href="https://discord.gg/T5pZgFbGE"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-2 rounded-full bg-white px-6 py-2.5 text-sm font-medium text-black hover:bg-white/90 transition shadow-lg"
        >
          <BrandMark icon={discord} className="h-4 w-4 text-black" />
          Join Discord Server
        </a>
        <Link to="/contact" className="inline-flex rounded-full border border-white/20 bg-white/5 px-6 py-2.5 text-sm text-white hover:bg-white/10 transition">
          Contact Desk
        </Link>
      </div>
    </main>
  )
}

const docs = [
  { icon: "fa6-solid:magnifying-glass", title: "Seeds", copy: "Phone, email, username, name, wallet, domain, IP, and public image. One kind of question. The seed is the start of a line, not the whole answer." },
  { icon: "fa6-solid:book-open", title: "Public side", copy: "bytesint.xyz reads public context and names the page or record on the same line. A hit without a source is not a result." },
  { icon: "fa6-solid:link", title: "Keep the link", copy: "Open the origin, quote it, or throw the line out. The link is part of the note." },
  { icon: "fa6-solid:wallet", title: "Credits", copy: "Starter, Basic, and Plus are the starter packs. Pro, Business, and Ultimate are the advanced packs. Payment is one-time. Plus adds a daily IntelX cap. Ultimate lookups are unlimited. Starter and Basic do not include IntelX." },
  { icon: "fa6-solid:file-lines", title: "PDF", copy: "Every pack can export a PDF. The export is the lines you kept, still source-linked." },
]

export function DocsPage() {
  return (
    <main className="mx-auto max-w-2xl px-6 pb-24 pt-32 text-center">
      <PageIntro icon="fa6-solid:book" kicker="Documentation" title="The workspace, in short." copy="What the product is for. This preview does not perform a lookup." />
      <ul className="mt-10 grid gap-8 text-left">
        {docs.map((item) => (
          <li key={item.title} className="flex gap-4">
            <Icon icon={item.icon} className="mt-1 h-5 w-5 shrink-0" aria-hidden />
            <div>
              <h2 className="text-lg font-medium">{item.title}</h2>
              <p className="mt-2 text-sm font-light leading-relaxed text-white/70">{item.copy}</p>
            </div>
          </li>
        ))}
      </ul>
    </main>
  )
}

const legal: Record<string, { icon: string; kicker: string; title: string; blocks: string[] }> = {
  terms: {
    icon: "fa6-solid:scale-balanced",
    kicker: "Terms of Service",
    title: "The deal, in plain lines.",
    blocks: [
      "bytesint.xyz is an OSINT workspace for public, source-linked context. Packs are one-time payments. There is no monthly plan.",
      "You use it for lookups you are allowed to run. A phone number, email, username, name, wallet, domain, IP, or public image is a seed. The useful part is the context that can be tied back to a source.",
      "Credits on Starter, Basic, Plus, Pro, Business, and Ultimate match the prices published on the pricing page. IntelX access follows that page: absent on Starter and Basic, capped on Plus, included on Pro, Business, and Ultimate, unlimited on Ultimate.",
      "This marketing preview does not submit the forms to a server, does not store a password, and does not run a lookup. The live service, when you use it, is bytesint.xyz.",
    ],
  },
  privacy: {
    icon: "fa6-solid:shield-halved",
    kicker: "Privacy Policy",
    title: "What this preview holds.",
    blocks: [
      "The sign-in and register screens keep a username in session storage so the dashboard can greet you. The password is not saved. Closing the tab clears it. No account is created on bytesint.xyz.",
      "The one-time code is generated in the page so the register steps can be walked through. No email is sent.",
      "The Cloudflare Turnstile widget is Cloudflare’s published interactive test widget. It is there to gate the button. It is not a production site key for bytesint.xyz.",
      "A contact note stays in the browser. It is not transmitted. The product itself is built around public records and keeps the source next to the line. Do not put a secret into a seed.",
    ],
  },
  legal: {
    icon: "fa6-solid:scale-balanced",
    kicker: "Legal notice",
    title: "Who is speaking.",
    blocks: [
      "This site is the bytesint.xyz marketing preview. It describes an OSINT workspace that turns public data into source-linked context.",
      "No company registration number, postal address, or phone is published in this preview. Reach the product through the contact page rather than a guessed inbox.",
      "Prices shown are the published one-time packs. They are not an offer of a subscription. Nothing on these pages is legal advice about a specific lookup.",
    ],
  },
  eula: {
    icon: "fa6-solid:file-lines",
    kicker: "EULA",
    title: "License to use the workspace.",
    blocks: [
      "You receive a personal, non-transferable license to use the bytesint.xyz workspace interface for lawful review of public information.",
      "You do not get the right to break access controls, to present a line without its source, or to resell the packs as a different product.",
      "PDF export, credits, and IntelX access are limited to what the pack you bought includes. Priority support is on Business and Ultimate only.",
      "The license ends if the use is unlawful or if the account is closed. This preview adds nothing beyond the screens you can click through.",
    ],
  },
}

export function LegalPage({ kind }: { kind: keyof typeof legal }) {
  const page = legal[kind]
  return (
    <main className="mx-auto max-w-2xl px-6 pb-24 pt-32 text-center">
      <PageIntro icon={page.icon} kicker={page.kicker} title={page.title} copy="English, and only the lines this product actually stands on." />
      <div className="mt-10 space-y-5 text-left text-sm font-light leading-relaxed text-white/75">
        {page.blocks.map((block) => (
          <p key={block}>{block}</p>
        ))}
      </div>
    </main>
  )
}
