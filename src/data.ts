export type Feature = { icon: string; label: string; off?: boolean }
export type Pack = { name: string; price: number; credits: number; per: string; popular?: boolean; features: Feature[] }
export type PackSide = "starter" | "advanced"

export const seeds = [
  { icon: "ph:fingerprint-bold", name: "Identity & Handles", desc: "Cross-platform handles, aliases, and persona graphing" },
  { icon: "ph:envelope-simple-bold", name: "Email Recon", desc: "MX verification, deliverability, and account associations" },
  { icon: "ph:shield-warning-bold", name: "Breach Vaults", desc: "15.8B+ compromised passwords, combo-lists & past breaches" },
  { icon: "ph:game-controller-bold", name: "Gaming & Meta", desc: "Discord snowflake, Minecraft UUIDs, Steam, Roblox RAP" },
  { icon: "ph:currency-btc-bold", name: "Crypto & Web3", desc: "BTC, ETH, SOL cluster tracking and PayPal footprints" },
  { icon: "ph:globe-hemisphere-east-bold", name: "Network & ASN", desc: "Reverse DNS, autonomous systems, open ports & BGP" },
  { icon: "ph:phone-bold", name: "Carrier & HLR", desc: "Line routing, IMSI risk scoring, and linked messengers" },
  { icon: "ph:file-search-bold", name: "Deep Archives", desc: "Historical pastes, darknet dumps, and de-hashed logs" },
]

export const steps = [
  {
    icon: "ph:crosshair-simple-bold",
    index: "01",
    title: "Inject Target Identifier",
    copy: "Input any target seed: email, Discord snowflake, username, phone, or IP. MultiSearch automatically determines optimal OSINT engines.",
  },
  {
    icon: "ph:cpu-bold",
    index: "02",
    title: "Autonomous Graph Resolution",
    copy: "bytesint.xyz cross-references 120+ public databases, historical leak vaults, and live APIs in parallel sub-second threads.",
  },
  {
    icon: "ph:shield-check-bold",
    index: "03",
    title: "Actionable Source Intelligence",
    copy: "Every correlation includes direct origin verification, confidence scores, breach records, and full forensic export options.",
  },
]

export const questions = [
  {
    q: "What makes bytesint.xyz different from other OSINT tools?",
    a: "bytesint.xyz combines live API telemetry with an indexed repository of over 15.8 billion breach and leak records. Instead of fragmented single-lookup tools, our federated MultiSearch correlates identities across gaming, financial, network, and social nodes in one unified intelligence dashboard.",
  },
  {
    q: "How does the credit system work?",
    a: "Credits are sold in lifetime one-time packs. There are zero subscriptions and zero recurring charges. Credits never expire, and each lookup clearly displays its exact credit cost before execution.",
  },
  {
    q: "Are searches logged or tracked?",
    a: "No. bytesint.xyz adheres to a strict Zero-Log RAM-Only policy. Lookups are executed through encrypted transit corridors and are never stored on persistent disks or linked to your real identity.",
  },
  {
    q: "What platforms can be cross-referenced?",
    a: "Our identity engine correlates Discord (snowflakes, live profiles), Roblox (live 3D avatars, user IDs), Crypto Wallets (BTC, ETH, SOL), Adobe, AliExpress, Apple ID, Steam (SteamID64), Minecraft, PayPal, Telegram, GitHub, Instagram, and more.",
  },
  {
    q: "Can I export forensic reports?",
    a: "Yes. All completed intelligence reports can be exported to structured JSON or clean, print-ready PDF formats with complete source citations and cryptographic timestamps.",
  },
  {
    q: "Is there priority support for high-volume analysts?",
    a: "Yes. Pro and Syndicate packages include direct access to our priority SOC dispatch channel and dedicated proxy throughput for large-scale operations.",
  },
]

export const starterPacks: Pack[] = [
  {
    name: "Scout",
    price: 4.99,
    credits: 100,
    per: "0.04",
    features: [
      { icon: "lucide:check", label: "100 crediti di ricerca inclusi" },
      { icon: "lucide:check", label: "€0.04 per singola ricerca" },
      { icon: "lucide:zap", label: "Riscatto istantaneo tramite Key" },
      { icon: "lucide:shield", label: "Zero abbonamenti · Paga solo ciò che usi" },
      { icon: "lucide:file-text", label: "Accesso a tutti i 32 moduli OSINT live" },
      { icon: "lucide:x", label: "Accesso API Developer dedicato", off: true },
    ],
  },
  {
    name: "Field Operator",
    price: 9.99,
    credits: 300,
    per: "0.03",
    popular: true,
    features: [
      { icon: "lucide:check", label: "300 crediti di ricerca inclusi" },
      { icon: "lucide:check", label: "€0.03 per singola ricerca" },
      { icon: "lucide:zap", label: "Motore MultiSearch federato parallelo" },
      { icon: "lucide:bot", label: "Key riscattabile via Bot Discord" },
      { icon: "lucide:gamepad", label: "Gaming, Discord snowflake & Fintech" },
      { icon: "lucide:file-text", label: "Esportazione report JSON & PDF" },
    ],
  },
  {
    name: "Analyst Pro",
    price: 19.99,
    credits: 800,
    per: "0.025",
    features: [
      { icon: "lucide:check", label: "800 crediti di ricerca inclusi" },
      { icon: "lucide:check", label: "€0.025 per singola ricerca" },
      { icon: "lucide:zap", label: "Scansioni simultanee senza rate limit" },
      { icon: "lucide:server", label: "Chiave API REST per automazioni" },
      { icon: "lucide:shield-check", label: "RAM Enclave a zero log persistenti" },
      { icon: "lucide:headphones", label: "Supporto prioritario su Discord" },
    ],
  },
]

export const advancedPacks: Pack[] = [
  {
    name: "Syndicate",
    price: 39.99,
    credits: 2000,
    per: "0.020",
    features: [
      { icon: "lucide:check", label: "2.000 crediti di ricerca inclusi" },
      { icon: "lucide:check", label: "€0.020 per ricerca (€20/1000)" },
      { icon: "lucide:cpu", label: "Throughput e proxy residenziali dedicati" },
      { icon: "lucide:link", label: "Grafi di identità cross-platform" },
      { icon: "lucide:bot", label: "Generazione multi-key tramite bot" },
      { icon: "lucide:headphones", label: "Ruolo e canale dedicato su Discord" },
    ],
  },
  {
    name: "Command Core",
    price: 79.99,
    credits: 5000,
    per: "0.016",
    popular: true,
    features: [
      { icon: "lucide:check", label: "5.000 crediti di ricerca inclusi" },
      { icon: "lucide:check", label: "Miglior rapporto valore (€0.016/query)" },
      { icon: "lucide:zap", label: "Velocità massima garantita (<300ms)" },
      { icon: "lucide:server", label: "Integrazione Webhook su misura" },
      { icon: "lucide:shield-alert", label: "Monitoraggio nodi in tempo reale" },
      { icon: "lucide:headphones", label: "Assistenza 24/7 diretta dal team" },
    ],
  },
  {
    name: "Unlimited Syndicate",
    price: 129.99,
    credits: 15000,
    per: "0.008",
    features: [
      { icon: "lucide:check", label: "15.000 crediti di ricerca inclusi" },
      { icon: "lucide:check", label: "Super conveniente (€0.008 per query)" },
      { icon: "lucide:server", label: "Accesso totale a tutti i moduli e tool" },
      { icon: "lucide:users", label: "Condivisione crediti e multi-account" },
      { icon: "lucide:bot", label: "Comandi bot illimitati via Discord" },
      { icon: "lucide:headphones", label: "Contatto diretto con i developer" },
    ],
  },
]
