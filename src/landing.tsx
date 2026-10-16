import { Icon } from "@iconify/react"
import { useState } from "react"
import { Link } from "react-router-dom"
import { brands, BrandMark } from "./components/brands"
import { advancedPacks, questions, starterPacks, steps, type PackSide } from "./data"
import { PackSwitch, RisingPrice } from "./pricing-ui"

interface DemoSelector {
  id: string
  name: string
  icon: string
  query: string
  label: string
  hits: number
  logs: string[]
  platforms: string[]
  databases: string[]
}

const DEMO_ITEMS: DemoSelector[] = [
  {
    id: "discord",
    name: "Discord",
    icon: "ph:discord-logo-fill",
    query: "1500206560322912307",
    label: "Discord Snowflake",
    hits: 14,
    logs: [
      "[0.04s] Resolving snowflake ID...",
      "[0.18s] 4 mutual developer guilds identified",
      "[0.31s] Linked SteamID: 765611980321948",
      "[0.44s] Matched in 3 breach collections",
    ],
    platforms: ["Discord", "Roblox", "Steam", "GitHub"],
    databases: ["discord-ip.json", "done_final.json", "rockyou2024.json"],
  },
  {
    id: "email",
    name: "Email",
    icon: "ph:envelope-simple-bold",
    query: "target.intel@proton.me",
    label: "Email Breach",
    hits: 27,
    logs: [
      "[0.03s] Verifying MX routing...",
      "[0.15s] Querying 15.8B indexed credentials...",
      "[0.29s] 3 exposed credential hashes recovered",
      "[0.41s] Associated PayPal account confirmed",
    ],
    platforms: ["ProtonMail", "PayPal", "Minecraft", "Twitter/X"],
    databases: ["rockyou2024.json", "facebook 2021 rf.json", "Instagram 17m.jsonl"],
  },
  {
    id: "minecraft",
    name: "Minecraft",
    icon: "ph:cube-bold",
    query: "Notch",
    label: "Minecraft UUID",
    hits: 8,
    logs: [
      "[0.05s] Resolving Mojang session...",
      "[0.16s] UUID: 069a79f4-44e9-4726-a5be-fca90e38aaf5",
      "[0.28s] Mojang Classic Cape verified",
      "[0.39s] Name history: 1 recorded handle",
    ],
    platforms: ["Mojang", "OptiFine", "Hypixel", "NameMC"],
    databases: ["minecraft_capes", "done_final.json"],
  },
  {
    id: "ip",
    name: "IP / ASN",
    icon: "ph:globe-hemisphere-east-bold",
    query: "185.220.101.5",
    label: "Infrastructure",
    hits: 19,
    logs: [
      "[0.02s] BGP Route: AS208323 (Zwiebelfreunde)",
      "[0.14s] Geolocation: Frankfurt am Main, DE",
      "[0.27s] Open ports: 80, 443, 9001 (Relay)",
      "[0.40s] Reverse DNS: tor-exit-node-05.de",
    ],
    platforms: ["BGP Routing", "Reverse DNS", "SSL SAN", "Shodan"],
    databases: ["infrastructure_scans", "open_ports"],
  },
]

export function Landing() {
  const [openQuestion, setOpenQuestion] = useState<string | null>(null)
  const [pack, setPack] = useState<PackSide>("starter")
  const [fromPrices, setFromPrices] = useState<number[] | null>(null)
  const [selectedDemo, setSelectedDemo] = useState<DemoSelector>(DEMO_ITEMS[0])
  const plans = pack === "starter" ? starterPacks : advancedPacks

  function choosePack(next: PackSide) {
    if (next === pack) return
    setFromPrices(plans.map((item) => item.price))
    setPack(next)
  }

  return (
    <main id="top" className="relative mx-auto max-w-5xl px-4 sm:px-6 text-center">
      {/* 1. HERO SECTION */}
      <section className="relative mx-auto flex max-w-3xl flex-col items-center pb-20 pt-32 sm:pt-36">
        {/* Animated Detective Logo with Sonar Rings */}
        <div className="relative mb-6 flex items-center justify-center">
          {/* Subtle sonar rings behind the detective */}
          <div className="pointer-events-none absolute h-36 w-36 rounded-full border border-white/10 animate-sonar" />
          <div className="pointer-events-none absolute h-24 w-24 rounded-full border border-white/[0.08]" />

          {/* Logo container */}
          <div className="relative flex h-20 w-20 items-center justify-center overflow-hidden rounded-2xl border border-white/15 bg-black/60 shadow-[0_0_30px_rgba(255,255,255,0.06)] backdrop-blur-xl">
            <img
              src="/logo.gif"
              alt="bytesint detective logo"
              className="h-full w-full object-cover"
            />
          </div>
        </div>

        {/* Minimal Kicker Tag */}
        <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3.5 py-1 text-xs font-mono tracking-wide text-white/70 backdrop-blur-md">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
          <span>bytesint.xyz</span>
          <span className="text-white/30">·</span>
          <span>OSINT workspace</span>
        </div>

        {/* Headline */}
        <h1 className="mt-6 text-4xl font-medium tracking-[-0.04em] text-white sm:text-6xl md:text-6xl leading-[1.08]">
          Public intelligence, <br />
          <span className="text-white/60">verified at the source.</span>
        </h1>

        {/* Subtitle */}
        <p className="mt-5 max-w-xl text-base font-light leading-relaxed text-white/70 sm:text-lg">
          De-anonymize targets, cross-reference 15.8B+ breach records, and correlate gaming and social footprints in sub-second queries.
        </p>

        {/* Clean Action Buttons */}
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-2 rounded-full bg-white px-6 py-3 text-sm font-medium text-black transition duration-200 hover:bg-white/90 shadow-lg"
          >
            <Icon icon="ph:terminal-window-bold" className="h-4 w-4" />
            <span>Open Workspace</span>
          </Link>

          <a
            href="#demo"
            className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-6 py-3 text-sm font-medium text-white/80 backdrop-blur-md transition duration-200 hover:bg-white/10 hover:text-white"
          >
            <Icon icon="ph:magnifying-glass-bold" className="h-4 w-4 text-white/60" />
            <span>Interactive Demo</span>
          </a>

          <Link
            to="/pricing"
            className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-6 py-3 text-sm font-medium text-white/80 backdrop-blur-md transition duration-200 hover:bg-white/10 hover:text-white"
          >
            <span>Pricing</span>
          </Link>
        </div>

        {/* 2. INTERACTIVE DEMO (Minimal & Functional) */}
        <div id="demo" className="mt-14 w-full text-left">
          <div className="overflow-hidden rounded-2xl border border-white/15 bg-black/55 p-5 shadow-2xl backdrop-blur-2xl sm:p-6">
            {/* Window Topbar */}
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2">
                <div className="flex gap-1.5">
                  <div className="h-2.5 w-2.5 rounded-full bg-white/20" />
                  <div className="h-2.5 w-2.5 rounded-full bg-white/20" />
                  <div className="h-2.5 w-2.5 rounded-full bg-white/20" />
                </div>
                <span className="font-mono text-xs text-white/50 ml-2">lookup://terminal</span>
              </div>
              <span className="font-mono text-[11px] text-emerald-400/90 flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                15.8B records online
              </span>
            </div>

            {/* Selector Chips */}
            <div className="mt-4 flex flex-wrap gap-2">
              {DEMO_ITEMS.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setSelectedDemo(item)}
                  className={`inline-flex items-center gap-2 rounded-full px-3.5 py-1 text-xs font-mono transition ${
                    selectedDemo.id === item.id
                      ? "bg-white text-black font-medium shadow"
                      : "border border-white/10 bg-white/5 text-white/60 hover:text-white hover:bg-white/10"
                  }`}
                >
                  <Icon icon={item.icon} className="h-3.5 w-3.5" />
                  <span>{item.name}</span>
                </button>
              ))}
            </div>

            {/* Input Bar */}
            <div className="mt-4 flex items-center justify-between rounded-xl border border-white/15 bg-white/5 px-4 py-2.5 font-mono text-xs">
              <div className="flex items-center gap-2 overflow-hidden">
                <span className="text-white/40 select-none">query&gt;</span>
                <span className="truncate text-white">{selectedDemo.query}</span>
              </div>
              <span className="rounded bg-white/10 px-2 py-0.5 text-[10px] uppercase text-white/70">
                {selectedDemo.label}
              </span>
            </div>

            {/* Output Split */}
            <div className="mt-4 grid gap-3 sm:grid-cols-2 font-mono text-xs">
              {/* Telemetry Output */}
              <div className="rounded-xl border border-white/10 bg-black/40 p-3.5 space-y-1.5">
                <p className="text-[10px] uppercase tracking-wider text-white/40 mb-2">Live Execution Log</p>
                {selectedDemo.logs.map((log, idx) => (
                  <div key={idx} className="text-white/75 flex items-start gap-2">
                    <span className="text-white/40 select-none">›</span>
                    <span>{log}</span>
                  </div>
                ))}
              </div>

              {/* Matched Data */}
              <div className="rounded-xl border border-white/10 bg-black/40 p-3.5 space-y-2.5">
                <div className="flex items-center justify-between border-b border-white/10 pb-1.5">
                  <span className="text-[10px] uppercase tracking-wider text-white/40">Correlation</span>
                  <span className="text-emerald-400 font-semibold">{selectedDemo.hits} records linked</span>
                </div>
                <div>
                  <span className="text-[10px] uppercase text-white/40 block">Platforms</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {selectedDemo.platforms.map((p) => (
                      <span key={p} className="rounded bg-white/10 px-2 py-0.5 text-[11px] text-white/80">
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <span className="text-[10px] uppercase text-white/40 block">Indexed Archives</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {selectedDemo.databases.map((db) => (
                      <span key={db} className="rounded bg-white/5 border border-white/10 px-2 py-0.5 text-[11px] text-white/60">
                        {db}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Link to Full App */}
            <div className="mt-4 flex items-center justify-between pt-3 border-t border-white/10 text-xs">
              <span className="text-white/50">Run unconstrained queries in workspace</span>
              <Link to="/dashboard" className="text-white hover:underline flex items-center gap-1 font-medium">
                <span>Launch Dashboard</span>
                <Icon icon="ph:arrow-right" className="h-3 w-3" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* 3. CAPABILITIES / FEATURES GRID */}
      <section className="py-16">
        <p className="text-xs uppercase tracking-[0.25em] text-white/40 font-mono">CAPABILITIES</p>
        <h2 className="mt-3 text-2xl font-medium tracking-[-0.03em] sm:text-3xl text-white">
          One engine. Every public footprint.
        </h2>

        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 text-left">
          <div className="rounded-2xl border border-white/10 bg-black/45 p-6 backdrop-blur-xl transition hover:border-white/25">
            <Icon icon="ph:share-network-bold" className="h-6 w-6 text-white" />
            <h3 className="mt-4 text-base font-medium text-white">Identity & Handles</h3>
            <p className="mt-2 text-xs font-light leading-relaxed text-white/65">
              Decode Discord snowflakes, extract mutual guilds, and link cross-platform handles across Steam, Telegram, and forums.
            </p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/45 p-6 backdrop-blur-xl transition hover:border-white/25">
            <Icon icon="ph:shield-warning-bold" className="h-6 w-6 text-white" />
            <h3 className="mt-4 text-base font-medium text-white">15.8B+ Breach Index</h3>
            <p className="mt-2 text-xs font-light leading-relaxed text-white/65">
              Historical breach archives, combo-lists, and de-hashed credential exposure logs across hundreds of compromised databases.
            </p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/45 p-6 backdrop-blur-xl transition hover:border-white/25">
            <Icon icon="ph:game-controller-bold" className="h-6 w-6 text-white" />
            <h3 className="mt-4 text-base font-medium text-white">Gaming Ecosystems</h3>
            <p className="mt-2 text-xs font-light leading-relaxed text-white/65">
              Mojang Minecraft UUID resolver, skins and capes, Roblox live 3D avatars, Chess.com grandmaster ratings, and Steam ID64.
            </p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/45 p-6 backdrop-blur-xl transition hover:border-white/25">
            <Icon icon="ph:globe-hemisphere-east-bold" className="h-6 w-6 text-white" />
            <h3 className="mt-4 text-base font-medium text-white">Network & ASN Routing</h3>
            <p className="mt-2 text-xs font-light leading-relaxed text-white/65">
              Trace target IP routing, autonomous systems (BGP), reverse DNS records, and SSL certificate subject alternative names.
            </p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/45 p-6 backdrop-blur-xl transition hover:border-white/25">
            <Icon icon="ph:currency-btc-bold" className="h-6 w-6 text-white" />
            <h3 className="mt-4 text-base font-medium text-white">Financial & Web3</h3>
            <p className="mt-2 text-xs font-light leading-relaxed text-white/65">
              Correlate Bitcoin, Ethereum, and Solana wallet interactions and match verified PayPal transaction markers.
            </p>
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/45 p-6 backdrop-blur-xl transition hover:border-white/25">
            <Icon icon="ph:shield-checkered-bold" className="h-6 w-6 text-white" />
            <h3 className="mt-4 text-base font-medium text-white">Zero-Log RAM Enclave</h3>
            <p className="mt-2 text-xs font-light leading-relaxed text-white/65">
              RAM-only ephemeral lookups. Queries never touch persistent server disk, ensuring complete investigator privacy.
            </p>
          </div>
        </div>
      </section>

      {/* 4. METHOD PIPELINE */}
      <section className="py-16">
        <p className="text-xs uppercase tracking-[0.25em] text-white/40 font-mono">WORKFLOW</p>
        <h2 className="mt-3 text-2xl font-medium tracking-[-0.03em] sm:text-3xl text-white">
          Three steps, then the verified link.
        </h2>
        <div className="mt-10 grid gap-4 md:grid-cols-3 text-left">
          {steps.map((step) => (
            <div
              key={step.index}
              className="rounded-2xl border border-white/10 bg-black/45 p-6 backdrop-blur-xl transition hover:border-white/20"
            >
              <div className="flex items-center justify-between">
                <Icon icon={step.icon} className="h-6 w-6 text-white" />
                <span className="font-mono text-sm text-white/30">{step.index}</span>
              </div>
              <h3 className="mt-4 text-lg font-medium text-white">{step.title}</h3>
              <p className="mt-2 text-xs font-light leading-relaxed text-white/65">{step.copy}</p>
            </div>
          ))}
        </div>
      </section>

      {/* 5. INDEXED PLATFORMS */}
      <section id="sources" className="py-16">
        <p className="text-xs uppercase tracking-[0.25em] text-white/40 font-mono">PLATFORMS</p>
        <h2 className="mt-3 text-2xl font-medium tracking-[-0.03em] sm:text-3xl text-white">
          Supported Surfaces
        </h2>
        <div className="mx-auto mt-8 max-w-3xl rounded-2xl border border-white/10 bg-black/45 p-6 backdrop-blur-xl">
          <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
            {brands.map((icon) => (
              <li key={icon.slug}>
                <span className="group flex items-center justify-center gap-2 rounded-xl border border-white/5 bg-white/5 px-3 py-2.5 text-xs text-white/70 transition duration-200 hover:border-white/20 hover:bg-white/10 hover:text-white">
                  <BrandMark icon={icon} />
                  <span>{icon.title}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* 6. PRICING PACKS */}
      <section id="credits" className="py-16">
        <p className="text-xs uppercase tracking-[0.25em] text-white/40 font-mono">CREDITS</p>
        <h2 className="mt-3 text-2xl font-medium tracking-[-0.03em] sm:text-3xl text-white">
          One-time packs. No subscriptions.
        </h2>

        <div className="mx-auto mt-8 max-w-4xl rounded-2xl border border-white/10 bg-black/50 p-6 text-left backdrop-blur-xl sm:p-8">
          <PackSwitch pack={pack} onChange={choosePack} />

          <div className="mt-8 grid gap-5 md:grid-cols-3">
            {plans.map((plan, index) => (
              <article
                key={plan.name}
                className={`relative flex flex-col justify-between rounded-xl border p-5 transition ${
                  plan.popular
                    ? "border-white/40 bg-white/10 shadow-xl"
                    : "border-white/10 bg-white/5 hover:border-white/20"
                }`}
              >
                {plan.popular ? (
                  <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 rounded-full bg-white px-2.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider text-black">
                    Popular
                  </span>
                ) : null}

                <div>
                  <h3 className="text-base font-medium text-white">{plan.name}</h3>
                  <div className="mt-2 flex items-baseline gap-1">
                    <span className="text-3xl font-medium tracking-tight text-white font-mono">
                      €<RisingPrice value={plan.price} from={fromPrices?.[index] ?? plan.price} />
                    </span>
                    <span className="text-xs text-white/50 font-mono">una tantum</span>
                  </div>

                  <p className="mt-1 text-xs text-white/60 font-mono">
                    {plan.credits.toLocaleString()} crediti · €{plan.per}/query
                  </p>

                  <ul className="mt-5 space-y-2 border-t border-white/10 pt-5">
                    {plan.features.map((feature) => (
                      <li
                        key={feature.label}
                        className={`flex items-start gap-2 text-xs ${feature.off ? "text-white/30 line-through" : "text-white/80"}`}
                      >
                        <Icon
                          icon={feature.icon}
                          className={`h-3.5 w-3.5 shrink-0 mt-0.5 ${feature.off ? "text-white/20" : "text-white"}`}
                          aria-hidden
                        />
                        <span>{feature.label}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="mt-6 pt-2">
                  <Link
                    to="/register"
                    className={`flex w-full items-center justify-center gap-1.5 rounded-xl py-2.5 text-xs font-medium transition ${
                      plan.popular
                        ? "bg-white text-black hover:bg-white/90"
                        : "border border-white/20 bg-white/5 text-white hover:bg-white hover:text-black"
                    }`}
                  >
                    <span>Get Started</span>
                    <Icon icon="lucide:arrow-up-right" className="h-3 w-3" />
                  </Link>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* 7. FAQ */}
      <section id="questions" className="py-16">
        <h2 className="text-2xl font-medium tracking-[-0.03em] sm:text-3xl text-white">
          Frequently Answered
        </h2>

        <div className="mx-auto mt-8 max-w-2xl rounded-2xl border border-white/10 bg-black/45 p-4 text-left backdrop-blur-xl sm:p-6">
          <div className="divide-y divide-white/10">
            {questions.map((item) => {
              const open = openQuestion === item.q
              return (
                <div key={item.q} className="py-3.5">
                  <button
                    type="button"
                    aria-expanded={open}
                    onClick={() => setOpenQuestion(open ? null : item.q)}
                    className="flex w-full items-center justify-between gap-4 text-left"
                  >
                    <span className={`text-sm transition-colors ${open ? "text-white" : "text-white/65 hover:text-white"}`}>
                      {item.q}
                    </span>
                    <Icon
                      icon="ph:caret-down-bold"
                      className={`h-3.5 w-3.5 shrink-0 text-white/50 transition-transform duration-200 ${open ? "rotate-180 text-white" : ""}`}
                      aria-hidden
                    />
                  </button>

                  <div className={`grid transition-[grid-template-rows] duration-200 ease-out ${open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"}`}>
                    <div className="overflow-hidden">
                      <p className={`mt-2 text-xs font-light leading-relaxed text-white/60 ${open ? "opacity-100" : "opacity-0"}`}>
                        {item.a}
                      </p>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </section>
    </main>
  )
}
