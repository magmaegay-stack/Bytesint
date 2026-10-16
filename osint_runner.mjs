import { execFile } from "node:child_process"
import { existsSync, readFileSync, writeFileSync } from "node:fs"
import { randomBytes, createHmac } from "node:crypto"
import { resolve, join } from "node:path"
import { fileURLToPath } from "node:url"

const __dirname = fileURLToPath(new URL(".", import.meta.url))
const MODULES_DIR = existsSync(resolve(__dirname, "modules_osint"))
  ? resolve(__dirname, "modules_osint")
  : resolve(__dirname, "modules osint")

export const OSINT_MODULES = [
  // MultiSearch Federated
  { id: "multisearch", file: "multisearch", name: "MultiSearch", category: "all", icon: "ph:magnifying-glass-plus-bold", type: "all", placeholder: "Enter username, email, phone, Discord ID, wallet...", sample: "torvalds", kicker: "FEDERATED • MULTI MODULE DISPATCH", heroTitle: "One query. Full OSINT correlation." },

  // Discord & Gaming
  { id: "discord", file: "Discord/discord_snowflake.py", name: "Discord Snowflake", category: "gaming", icon: "ph:discord-logo-fill", type: "discord", placeholder: "Discord Snowflake ID (e.g. 1554183119408468128)...", sample: "1554183119408468128", kicker: "DISCORD INTELLIGENCE • SNOWFLAKE & LIVE PROFILE", heroTitle: "Discord User & Snowflake Resolver" },
  { id: "roblox", file: "Username/roblox.py", name: "Roblox OSINT", category: "gaming", icon: "ph:cube-bold", type: "username", placeholder: "Roblox username or User ID...", sample: "roblox", kicker: "ROBLOX OSINT • AVATAR & STATS", heroTitle: "Roblox Live Dossier" },
  { id: "minecraft", file: "Username/minecraft.py", name: "Minecraft Mojang", category: "gaming", icon: "ph:cube-transparent-bold", type: "username", placeholder: "Minecraft username or UUID...", sample: "Notch", kicker: "MOJANG ASSET • MINECRAFT OSINT", heroTitle: "Minecraft UUID & Texture Lookup" },
  { id: "steam", file: "Username/steam.py", name: "Steam Profile", category: "gaming", icon: "ph:steam-logo-fill", type: "username", placeholder: "Steam vanity handle or SteamID64...", sample: "gabelogannewell", kicker: "VALVE ASSET • STEAM IDENTITY", heroTitle: "Steam ID64 & Community Resolver" },
  { id: "chess", file: "Username/chess.py", name: "Chess.com", category: "gaming", icon: "ph:crown-bold", type: "username", placeholder: "Chess.com handle...", sample: "magnuscarlsen", kicker: "FIDE / ONLINE • CHESS GRAPH", heroTitle: "Chess.com Grandmaster & Rating" },
  { id: "medal", file: "Mail/medal.py", name: "Medal.tv", category: "gaming", icon: "ph:medal-bold", type: "username", placeholder: "Medal.tv username...", sample: "ninja", kicker: "GAMING CLIPS • MEDAL IDENTITY", heroTitle: "Medal.tv Clip Registry" },

  // Developer & Social
  { id: "github", file: "Username/github.py", name: "GitHub Recon", category: "dev", icon: "ph:github-logo-bold", type: "username", placeholder: "GitHub username (e.g. torvalds)...", sample: "torvalds", kicker: "DEVELOPER • REPO & IDENTITY", heroTitle: "GitHub Public Intelligence" },
  { id: "gitlab", file: "Username/gitlab.py", name: "GitLab Profile", category: "dev", icon: "ph:gitlab-logo-bold", type: "username", placeholder: "GitLab username...", sample: "gitlab", kicker: "DEVELOPER • GITLAB MESH", heroTitle: "GitLab Account Recon" },
  { id: "keybase", file: "Username/keybase.py", name: "Keybase Proofs", category: "dev", icon: "ph:key-bold", type: "username", placeholder: "Keybase username...", sample: "max", kicker: "PGP • CRYPTOGRAPHIC PROOF", heroTitle: "Keybase Identity Proofs" },
  { id: "telegram", file: "Username/telegram.py", name: "Telegram Intel", category: "social", icon: "ph:telegram-logo-bold", type: "username", placeholder: "Telegram handle without @...", sample: "durov", kicker: "TELEGRAM • ENCRYPTED CHANNEL", heroTitle: "Telegram Public Channel & User" },
  { id: "tiktok", file: "Username/tiktok.py", name: "TikTok Profile", category: "social", icon: "ph:tiktok-logo-bold", type: "username", placeholder: "TikTok username...", sample: "tiktok", kicker: "SHORT VIDEO • TIKTOK GRAPH", heroTitle: "TikTok Social Metrics" },
  { id: "x", file: "Username/twitter.py", name: "X / Twitter", category: "social", icon: "ph:x-logo-bold", type: "username", placeholder: "X / Twitter handle...", sample: "elonmusk", kicker: "MICROBLOGGING • X IDENTITY", heroTitle: "X (Twitter) Footprint" },
  { id: "youtube", file: "Username/youtube.py", name: "YouTube Channel", category: "social", icon: "ph:youtube-logo-bold", type: "username", placeholder: "YouTube username/channel...", sample: "google", kicker: "MEDIA • YOUTUBE GRAPH", heroTitle: "YouTube Channel Recon" },
  { id: "instagram", file: "Username/instagram.py", name: "Instagram", category: "social", icon: "ph:instagram-logo-bold", type: "username", placeholder: "Instagram handle...", sample: "instagram", kicker: "SOCIAL • INSTAGRAM GRAPH", heroTitle: "Instagram Profile Recon" },
  { id: "twitch", file: "Username/twitch.py", name: "Twitch", category: "social", icon: "ph:twitch-logo-bold", type: "username", placeholder: "Twitch streamer handle...", sample: "shroud", kicker: "STREAMING • TWITCH IDENTITY", heroTitle: "Twitch Streamer Presence" },
  { id: "duolingo", file: "Username/duolingo.py", name: "Duolingo Languages", category: "social", icon: "ph:translate-bold", type: "username", placeholder: "Duolingo username...", sample: "simo", kicker: "EDUTECH • DUOLINGO STREAK", heroTitle: "Duolingo Language Learner Intel" },
  { id: "soundcloud", file: "Username/soundcloud.py", name: "SoundCloud", category: "social", icon: "ph:sound-waves-bold", type: "username", placeholder: "SoundCloud artist...", sample: "skrillex", kicker: "AUDIO STREAM • SOUNDCLOUD", heroTitle: "SoundCloud Artist Profile" },
  { id: "pinterest", file: "Username/pinterest.py", name: "Pinterest Boards", category: "social", icon: "ph:pinterest-logo-bold", type: "username", placeholder: "Pinterest username...", sample: "pinterest", kicker: "VISUAL BOARD • PINTEREST", heroTitle: "Pinterest Boards & Collections" },
  { id: "linktree", file: "Username/linktree.py", name: "Linktree Bio", category: "social", icon: "ph:tree-structure-bold", type: "username", placeholder: "Linktree slug...", sample: "alex", kicker: "BIO LINK • MULTI CHANNEL", heroTitle: "Linktree Aggregated Links" },

  // Crypto & Finance
  { id: "crypto", file: "Wallet/crypto_resolver.py", name: "Crypto Wallet", category: "finance", icon: "ph:currency-btc-bold", type: "wallet", placeholder: "0x... or 1A1zP1... or Solana address...", sample: "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", kicker: "BLOCKCHAIN • ON-CHAIN LEDGER", heroTitle: "Crypto Wallet Explorer (BTC, ETH, SOL, LTC, DOGE, TRX, XRP, BNB)" },
  { id: "paypal", file: "Mail/paypal.py", name: "PayPal.me", category: "finance", icon: "ph:credit-card-bold", type: "username", placeholder: "PayPal.me handle or email...", sample: "alexpay", kicker: "FINTECH • SETTLEMENT HANDLE", heroTitle: "PayPal.me Recipient Query" },
  { id: "revolut", file: "Mail/revolut.py", name: "Revolut Revtag", category: "finance", icon: "ph:arrows-clockwise-bold", type: "username", placeholder: "Revtag or handle...", sample: "alex", kicker: "NEOBANK • REVTAG ROUTING", heroTitle: "Revolut Pay Identity" },
  { id: "stripe", file: "Mail/stripe.py", name: "Stripe Merchant", category: "finance", icon: "ph:currency-dollar-bold", type: "email", placeholder: "Merchant email...", sample: "billing@shop.com", kicker: "GATEWAY • STRIPE VERIFIER", heroTitle: "Stripe Payment Account" },

  // Email & Services Verification
  { id: "email", file: "Mail/email_osint.py", name: "Email OSINT Deep", category: "identity", icon: "ph:envelope-simple-bold", type: "email", placeholder: "Target email address...", sample: "target@gmail.com", kicker: "CROSS PLATFORM • DEEP EMAIL PROBE", heroTitle: "Email Footprint & Domain Verification" },
  { id: "adobe", file: "Mail/adobe.py", name: "Adobe Creative Cloud", category: "identity", icon: "ph:palette-bold", type: "email", placeholder: "Adobe ID email...", sample: "creative@adobe.com", kicker: "CREATIVE CLOUD • ADOBE ID", heroTitle: "Adobe Account Verification" },
  { id: "aliexpress", file: "Mail/aliexpress.py", name: "AliExpress Buyer", category: "identity", icon: "ph:storefront-bold", type: "email", placeholder: "Account email or phone...", sample: "buyer@gmail.com", kicker: "ECOMMERCE • ALIBABA CLOUD", heroTitle: "AliExpress Buyer Verification" },
  { id: "apple", file: "Mail/apple.py", name: "Apple ID", category: "identity", icon: "ph:apple-logo-bold", type: "email", placeholder: "Apple ID email...", sample: "user@icloud.com", kicker: "APPLE SERVICES • ICLOUD AUTH", heroTitle: "Apple ID Verification" },
  { id: "google", file: "Mail/google.py", name: "Google Identity", category: "identity", icon: "ph:google-logo-bold", type: "email", placeholder: "Google account email...", sample: "target@gmail.com", kicker: "GOOGLE WORKSPACE • IDENTITY", heroTitle: "Google Account Intelligence" },
  { id: "microsoft", file: "Mail/microsoft.py", name: "Microsoft Live", category: "identity", icon: "ph:windows-logo-bold", type: "email", placeholder: "Live / Hotmail / Outlook email...", sample: "user@outlook.com", kicker: "MICROSOFT RECOVERY • AUTH", heroTitle: "Microsoft Account Footprint" },
  { id: "office365", file: "Mail/office365.py", name: "Office 365 / Azure", category: "identity", icon: "ph:microsoft-teams-logo-bold", type: "email", placeholder: "Work / school email...", sample: "admin@corp.com", kicker: "ENTERPRISE • MICROSOFT 365", heroTitle: "Microsoft 365 Federation" },
  { id: "amazon", file: "Mail/amazon.py", name: "Amazon Customer", category: "identity", icon: "ph:shopping-cart-bold", type: "email", placeholder: "Amazon account email...", sample: "buyer@amazon.com", kicker: "RETAIL MESH • AMAZON ID", heroTitle: "Amazon Account Verification" },
  { id: "netflix", file: "Mail/netflix.py", name: "Netflix Account", category: "identity", icon: "ph:television-bold", type: "email", placeholder: "Netflix registered email...", sample: "streamer@netflix.com", kicker: "STREAMING NODE • NETFLIX", heroTitle: "Netflix Account Check" },
  { id: "spotify", file: "Mail/spotify.py", name: "Spotify Account", category: "identity", icon: "ph:spotify-logo-bold", type: "email", placeholder: "Spotify registered email...", sample: "user@gmail.com", kicker: "MEDIA ACCOUNT • SPOTIFY", heroTitle: "Spotify Subscription Check" },
  { id: "gravatar", file: "Mail/gravatar.py", name: "Gravatar Global Avatar", category: "identity", icon: "ph:user-circle-gear-bold", type: "email", placeholder: "Email address...", sample: "target@gmail.com", kicker: "HASHED MD5 • GLOBAL AVATAR", heroTitle: "Gravatar Global Hash Lookup" },
  { id: "wix", file: "Mail/wix.py", name: "Wix Platform", category: "identity", icon: "ph:globe-simple-bold", type: "email", placeholder: "Wix account email...", sample: "web@example.com", kicker: "CMS • WIX USER ACCOUNT", heroTitle: "Wix Platform Identity" },
  { id: "shein", file: "Mail/shein.py", name: "Shein Customer", category: "identity", icon: "ph:shopping-bag-bold", type: "email", placeholder: "Customer email...", sample: "shopper@gmail.com", kicker: "RETAIL MESH • SHEIN", heroTitle: "Shein Customer Record" },
  { id: "deliveroo", file: "Mail/deliveroo.py", name: "Deliveroo", category: "identity", icon: "ph:moped-bold", type: "email", placeholder: "Customer email or phone...", sample: "eats@gmail.com", kicker: "FOOD DISPATCH • DELIVEROO", heroTitle: "Deliveroo Customer Record" },
  { id: "esty", file: "Mail/esty.py", name: "Etsy Marketplace", category: "identity", icon: "ph:basket-bold", type: "email", placeholder: "Etsy member email...", sample: "artisan@gmail.com", kicker: "MARKETPLACE • ETSY USER", heroTitle: "Etsy Marketplace Member" },
  { id: "dropbox", file: "Mail/dropbox.py", name: "Dropbox Storage", category: "identity", icon: "ph:dropbox-logo-bold", type: "email", placeholder: "Dropbox user email...", sample: "user@dropbox.com", kicker: "CLOUD STORAGE • DROPBOX", heroTitle: "Dropbox Account Presence" },
  { id: "plex", file: "Mail/plex.py", name: "Plex Media Server", category: "identity", icon: "ph:film-slate-bold", type: "email", placeholder: "Plex account email...", sample: "media@gmail.com", kicker: "STREAMING NODE • PLEX", heroTitle: "Plex Media Server Account" },

  // Phone Intel
  { id: "phone", file: "Phone/phone_osint.py", name: "Phone OSINT Deep", category: "identity", icon: "ph:phone-bold", type: "phone", placeholder: "+39 340... or +1 555...", sample: "+39 340 1234567", kicker: "PHONE ASSET • HLR & CARRIER ROUTING", heroTitle: "Carrier, HLR & Messaging Footprint" },

  // Breach & Threat Intelligence
  { id: "breach", file: "Breach/leak_intelligence.py", name: "Breach & Stealer Intel", category: "identity", icon: "ph:shield-warning-bold", type: "all", placeholder: "Email, username, or IP to check against breaches...", sample: "test@gmail.com", kicker: "FREE THREAT INTEL • HUDSON ROCK & LEAKCHECK", heroTitle: "Live Data Breach & Stealer Intelligence" },
]

export function findModuleScript(moduleIdentifier) {
  if (!moduleIdentifier) return null
  const clean = String(moduleIdentifier).trim()

  // 0. Explicit alias checks
  if (clean === "discord" || clean === "discord_snowflake" || clean === "snowflake" || clean === "discord.py") {
    const p = resolve(MODULES_DIR, "Discord/discord_snowflake.py")
    if (existsSync(p)) return p
  }
  if (clean === "breach" || clean === "leak" || clean === "leakcheck" || clean === "stealer" || clean === "hudsonrock") {
    const p = resolve(MODULES_DIR, "Breach/leak_intelligence.py")
    if (existsSync(p)) return p
  }
  if (clean === "crypto" || clean === "wallet") {
    const p = resolve(MODULES_DIR, "Wallet/crypto_resolver.py")
    if (existsSync(p)) return p
  }
  if (clean === "roblox") {
    const p = resolve(MODULES_DIR, "Username/roblox.py")
    if (existsSync(p)) return p
  }

  // 1. Direct path check
  const direct = resolve(MODULES_DIR, clean)
  if (existsSync(direct)) return direct

  // 2. Lookup in OSINT_MODULES table
  const matchDef = OSINT_MODULES.find((m) => m.id === clean || m.file === clean)
  if (matchDef && matchDef.file) {
    const p = resolve(MODULES_DIR, matchDef.file)
    if (existsSync(p)) return p
  }

  // 3. Fallback search across known subdirectories
  const cleanFile = clean.endsWith(".py") ? clean : `${clean}.py`
  const subdirs = ["Discord", "Username", "Breach", "Wallet", "Mail", "Phone", ""]
  for (const sub of subdirs) {
    const candidate = join(MODULES_DIR, sub, cleanFile)
    if (existsSync(candidate)) return candidate
  }

  return null
}

function getPythonPath() {
  if (process.env.PYTHON_PATH) return process.env.PYTHON_PATH
  if (process.platform === "win32") {
    const defaultWin = "C:\\Users\\mr.opsec\\AppData\\Local\\Programs\\Python\\Python314\\python.exe"
    if (existsSync(defaultWin)) return defaultWin
  }
  return "python3"
}

function parseJsonFromOutput(output) {
  if (!output || typeof output !== "string") return null
  try {
    return JSON.parse(output)
  } catch {
    const firstBrace = output.indexOf("{")
    const lastBrace = output.lastIndexOf("}")
    if (firstBrace !== -1 && lastBrace !== -1 && lastBrace > firstBrace) {
      try {
        return JSON.parse(output.slice(firstBrace, lastBrace + 1))
      } catch {
        return null
      }
    }
    return null
  }
}

export function executePythonModule(moduleFileOrId, target, timeoutMs = 15000) {
  return new Promise((resolve) => {
    const pythonBin = getPythonPath()
    const scriptPath = findModuleScript(moduleFileOrId)

    if (!scriptPath || !existsSync(scriptPath)) {
      resolve({
        success: false,
        error: `Module script not found: ${moduleFileOrId}`,
        raw: null,
      })
      return
    }

    const env = {
      ...process.env,
      PYTHONIOENCODING: "utf-8",
      PYTHONUTF8: "1",
    }

    const args = [scriptPath, target]
    if (
      scriptPath.endsWith("email_osint.py") ||
      scriptPath.endsWith("phone_osint.py") ||
      scriptPath.endsWith("username_osint.py")
    ) {
      args.push("--json")
    }

    execFile(
      pythonBin,
      args,
      { env, timeout: timeoutMs, maxBuffer: 10 * 1024 * 1024 },
      (error, stdout, stderr) => {
        const textOut = (stdout || "").toString("utf-8")
        const parsed = parseJsonFromOutput(textOut)

        if (parsed) {
          resolve({
            success: true,
            data: parsed,
            rawText: textOut,
            stderr: (stderr || "").toString("utf-8"),
          })
          return
        }

        if (error) {
          resolve({
            success: false,
            error: error.message,
            stderr: (stderr || "").toString("utf-8"),
            rawText: textOut,
          })
          return
        }

        resolve({
          success: true,
          data: { raw: textOut },
          rawText: textOut,
        })
      }
    )
  })
}

export function normalizeModuleResult(moduleId, target, rawResult) {
  const modDef = OSINT_MODULES.find((m) => m.id === moduleId) || {
    id: moduleId,
    name: moduleId,
    icon: "ph:magnifying-glass-bold",
    category: "identity",
    kicker: "OSINT LOOKUP",
    heroTitle: `${moduleId.toUpperCase()} Intel`,
  }

  if (!rawResult || !rawResult.success) {
    return {
      moduleId,
      moduleName: modDef.name,
      moduleIcon: modDef.icon,
      target,
      found: false,
      status: "Not Registered",
      statusMessage: "Nessun record riscontrato nei registri pubblici per questo identificatore.",
      displayName: target,
      username: target,
      avatarUrl: `https://api.dicebear.com/7.x/identicon/svg?seed=${target}`,
      idPill: "NO-RECORD",
      datePill: "Not Found",
      details: [
        { label: "TARGET", value: target },
        { label: "STATUS", value: "Not Registered / Safe", isStatus: true, statusDot: "bg-white/30" },
        { label: "MODULE", value: modDef.name },
        { label: "ENGINE TYPE", value: "Native OSINT Probe" },
      ],
      raw: rawResult,
    }
  }

  const data = rawResult.data || {}

  // 0. Leak & Breach Intelligence Result (Hudson Rock & LeakCheck)
  if (data.service === "leak_intelligence" && data.return) {
    const ret = data.return
    const isFound = Boolean(ret.is_breached)
    const hr = ret.hudson_rock || {}
    const lc = ret.leakcheck || {}
    const details = [
      { label: "BREACH STATUS", value: isFound ? "Compromised Records Found" : "Clean / Zero Breaches" },
      { label: "RISK SCORE", value: `${ret.threat_score}/100` },
      { label: "TOTAL BREACHES", value: String(ret.total_records) },
      { label: "INFOSTEALER INFECTIONS", value: hr.stealers_count ? `${hr.stealers_count} Compromised Devices` : "0 Stealer Infections" },
    ]
    if (hr.malware_families && hr.malware_families.length > 0) {
      details.push({ label: "MALWARE FAMILIES", value: hr.malware_families.join(", ") })
    }
    if (lc.sources && lc.sources.length > 0) {
      details.push({ label: "LEAK SOURCES", value: lc.sources.slice(0, 6).map((s) => s.name).join(", ") })
    }
    if (ret.shodan && ret.shodan.ports) {
      details.push({ label: "OPEN PORTS (SHODAN)", value: ret.shodan.ports.join(", ") })
    }

    return {
      moduleId,
      moduleName: modDef.name,
      moduleIcon: modDef.icon,
      target,
      found: isFound,
      status: isFound ? `Compromised (${ret.total_records} Breaches)` : "Clean (0 Breaches)",
      displayName: target,
      username: target,
      avatarUrl: `https://api.dicebear.com/7.x/identicon/svg?seed=${target}`,
      profileUrl: null,
      idPill: isFound ? `THREAT-${ret.threat_score}` : "CLEAN-RECORD",
      datePill: isFound ? "Breach Recorded" : "Safe Identity",
      details,
      raw: data,
    }
  }

  // 1. Discord Snowflake Result
  if (data.service === "discord" && data.return) {
    const ret = data.return
    const isFound = data.result === "found"
    const details = [
      { label: "USER ID", value: ret.user_id },
      { label: "USERNAME", value: ret.username },
      { label: "DISPLAY NAME", value: ret.display_name },
      { label: "ACCOUNT CREATED", value: ret.created_at },
      { label: "ACCOUNT AGE", value: ret.account_age },
      { label: "IS BOT / APP", value: ret.is_bot ? "Yes (Application / Bot)" : "No (Human User)" },
    ]
    if (ret.badges && ret.badges.length > 0) {
      details.push({ label: "BADGES", value: ret.badges.join(", ") })
    }
    if (ret.worker_id !== undefined) {
      details.push({ label: "SNOWFLAKE WORKER / PROCESS", value: `Worker: ${ret.worker_id} | Process: ${ret.process_id} | Inc: ${ret.increment}` })
    }

    return {
      moduleId,
      moduleName: modDef.name,
      moduleIcon: modDef.icon,
      target,
      found: isFound,
      status: isFound ? "Verified Live Identity" : "Not Found",
      displayName: ret.display_name || ret.username || target,
      username: ret.username || target,
      avatarUrl: ret.avatar_url,
      bannerUrl: ret.banner_url,
      profileUrl: ret.profile_url || `https://discord.com/users/${ret.user_id}`,
      idPill: `DISCORD-${ret.user_id}`,
      datePill: ret.created_at ? ret.created_at.split(" ")[0] : "Verified",
      details,
      raw: data,
    }
  }

  // 2. Roblox Profile Result
  if (data.service === "roblox" && data.return) {
    const ret = data.return
    const isFound = data.result === "found"
    const details = []
    if (ret.user_id) details.push({ label: "ROBLOX USER ID", value: String(ret.user_id) })
    if (ret.display_name) details.push({ label: "DISPLAY NAME", value: ret.display_name })
    if (ret.username) details.push({ label: "USERNAME", value: `@${ret.username}` })
    if (ret.joined) details.push({ label: "JOINED DATE", value: ret.joined })
    if (ret.followers !== undefined) details.push({ label: "FOLLOWERS", value: Number(ret.followers).toLocaleString() })
    if (ret.friends !== undefined) details.push({ label: "FRIENDS", value: Number(ret.friends).toLocaleString() })
    if (ret.is_banned !== undefined) details.push({ label: "ACCOUNT STATUS", value: ret.is_banned ? "Banned" : "Active (Clean)" })
    if (ret.description) details.push({ label: "ABOUT / BIO", value: ret.description })

    return {
      moduleId,
      moduleName: modDef.name,
      moduleIcon: modDef.icon,
      target,
      found: isFound,
      status: isFound ? (ret.is_banned ? "Account Banned" : "Verified Active Player") : "Not Found",
      displayName: ret.display_name || ret.username || target,
      username: ret.username || target,
      avatarUrl: ret.avatar_headshot || ret.avatar_url || ret.avatar_render,
      avatarRender: ret.avatar_render,
      profileUrl: ret.profile_url || (ret.user_id ? `https://www.roblox.com/users/${ret.user_id}/profile` : null),
      idPill: ret.user_id ? `ROBLOX-${ret.user_id}` : "ROBLOX-OK",
      datePill: ret.joined || "Roblox Member",
      details,
      raw: data,
    }
  }

  // 3. Crypto Wallet Result
  if ((data.service === "wallet" || data.ExtraData?.Chain || data.taken !== undefined && data.ExtraData?.Address) && (data.return || data.ExtraData)) {
    const isFound = data.result === "found" || Boolean(data.taken)
    const ret = data.return || {}
    const extra = data.ExtraData || {}
    const chain = ret.chain || extra.Chain || "Ledger"
    const addr = ret.address || extra.Address || target
    const balance = ret.balance || (extra.BalanceETH ? `${extra.BalanceETH} ETH` : extra.BalanceBTC ? `${extra.BalanceBTC} BTC` : extra.BalanceSOL ? `${extra.BalanceSOL} SOL` : "0.00")
    const txCount = ret.total_transactions !== undefined ? ret.total_transactions : extra.TotalTransactions !== undefined ? extra.TotalTransactions : 0

    const details = [
      { label: "BLOCKCHAIN", value: chain.toUpperCase() },
      { label: "ADDRESS", value: addr },
      { label: "VERIFIED BALANCE", value: balance },
      { label: "TOTAL TRANSACTIONS", value: String(txCount) },
      { label: "LEDGER STATE", value: isFound ? "Active Funded On-Chain Record" : "Unfunded / Clean" },
    ]

    return {
      moduleId,
      moduleName: modDef.name,
      moduleIcon: modDef.icon,
      target,
      found: isFound,
      status: isFound ? `${chain} Active Wallet` : "Zero Balance / Inactive",
      displayName: `${chain} Wallet: ${addr.slice(0, 6)}...${addr.slice(-4)}`,
      username: addr,
      avatarUrl: `https://api.dicebear.com/7.x/identicon/svg?seed=${addr}`,
      profileUrl: ret.explorer_url || `https://etherscan.io/address/${addr}`,
      idPill: `${chain.toUpperCase()}-LEDGER`,
      datePill: isFound ? "Active Ledger Node" : "Zero Balance",
      details,
      raw: data,
    }
  }

  // 4. Adobe Module
  if (moduleId === "adobe" || data.accountExists !== undefined && data.raw?.authenticationState) {
    const isFound = Boolean(data.accountExists)
    const challenges = data.challenges || data.raw?.challenges || {}
    const authState = data.raw?.authenticationState || {}
    const details = [
      { label: "ADOBE ACCOUNT", value: isFound ? "Registered Active ID" : "Not Registered" },
    ]
    if (challenges.primaryEmail) details.push({ label: "PRIMARY EMAIL MASK", value: challenges.primaryEmail })
    if (challenges.securityPhoneNumber) details.push({ label: "SECURITY PHONE", value: challenges.securityPhoneNumber })
    if (challenges.secondaryEmail) details.push({ label: "SECONDARY EMAIL", value: challenges.secondaryEmail })
    if (authState.mfaStatus) details.push({ label: "MFA STATUS", value: authState.mfaStatus })
    if (authState.passwordlessAvailable !== undefined) details.push({ label: "PASSWORDLESS", value: authState.passwordlessAvailable ? "Enabled" : "Disabled" })

    return {
      moduleId,
      moduleName: modDef.name,
      moduleIcon: modDef.icon,
      target,
      found: isFound,
      status: isFound ? "Adobe ID Confirmed" : "Not Found",
      displayName: challenges.primaryEmail || target,
      username: target,
      avatarUrl: null,
      profileUrl: "https://account.adobe.com",
      idPill: "ADOBE-CC",
      datePill: isFound ? "Registered Adobe ID" : "No Account",
      details,
      raw: data,
    }
  }

  // 5. Email OSINT Full Suite
  if (data.email && (data.summary || data.services)) {
    const sum = data.summary || {}
    const foundOn = sum.registered_on || []
    const isFound = foundOn.length > 0 || Boolean(data.domain_info?.valid_mx)
    const details = [
      { label: "TARGET EMAIL", value: data.email },
      { label: "REGISTERED PLATFORMS", value: foundOn.length > 0 ? foundOn.join(", ") : "None detected" },
      { label: "SERVICES FOUND COUNT", value: `${foundOn.length} active registrations` },
    ]
    if (data.domain_info?.mx_records) {
      details.push({ label: "PRIMARY MX HOST", value: data.domain_info.mx_records[0] || "N/A" })
    }
    if (sum.is_disposable !== undefined) {
      details.push({ label: "DISPOSABLE / TEMP MAIL", value: sum.is_disposable ? "Yes (Burner)" : "No (Permanent Domain)" })
    }

    const gravatarAv = data.services?.gravatar?.profile?.avatar_url || data.services?.gravatar?.avatar_url

    return {
      moduleId,
      moduleName: modDef.name,
      moduleIcon: modDef.icon,
      target,
      found: isFound,
      status: isFound ? `${foundOn.length} Services Verified` : "No Public Registrations",
      displayName: data.email,
      username: data.email,
      avatarUrl: gravatarAv || `https://api.dicebear.com/7.x/identicon/svg?seed=${data.email}`,
      profileUrl: null,
      idPill: `EMAIL-${foundOn.length}-SERVICES`,
      datePill: isFound ? "Email Dossier Resolved" : "Zero Matches",
      details,
      raw: data,
    }
  }

  // 6. Phone OSINT Full Suite
  if (data.phone && (data.summary || data.services || data.valid !== undefined)) {
    const sum = data.summary || {}
    const isFound = Boolean(data.valid)
    const details = [
      { label: "PHONE NUMBER", value: data.phone },
      { label: "VALID NUMBER", value: isFound ? "Yes (E.164 Valid)" : "Invalid Format" },
    ]
    if (sum.carrier) details.push({ label: "TELECOM CARRIER", value: sum.carrier })
    if (sum.country) details.push({ label: "COUNTRY / REGION", value: sum.country })
    if (sum.line_type) details.push({ label: "LINE TYPE", value: sum.line_type.toUpperCase() })
    if (sum.registered_services && sum.registered_services.length > 0) {
      details.push({ label: "MESSENGERS & APPS", value: sum.registered_services.join(", ") })
    }

    return {
      moduleId,
      moduleName: modDef.name,
      moduleIcon: modDef.icon,
      target,
      found: isFound,
      status: isFound ? `Carrier: ${sum.carrier || "Resolved"}` : "Invalid Phone",
      displayName: data.phone,
      username: data.phone,
      avatarUrl: null,
      profileUrl: null,
      idPill: sum.country ? `PHONE-${sum.country}` : "PHONE-OK",
      datePill: sum.line_type || "Carrier Line",
      details,
      raw: data,
    }
  }

  // 7. Standard Pattern: { result: "found" | "not_found", return: { ... } }
  if (data.result !== undefined && data.return !== undefined) {
    const isFound = data.result === "found"
    const ret = data.return || {}
    const details = []

    if (ret.location) details.push({ label: "LOCATION", value: String(ret.location) })
    if (ret.company) details.push({ label: "COMPANY", value: String(ret.company) })
    if (ret.bio) details.push({ label: "BIO", value: String(ret.bio) })
    if (ret.public_repos !== undefined) details.push({ label: "PUBLIC REPOSITORIES", value: String(ret.public_repos) })
    if (ret.followers !== undefined) details.push({ label: "FOLLOWERS", value: String(ret.followers) })
    if (ret.following !== undefined) details.push({ label: "FOLLOWING", value: String(ret.following) })
    if (ret.created_at) details.push({ label: "CREATED AT", value: String(ret.created_at) })
    if (ret.website) details.push({ label: "WEBSITE", value: String(ret.website) })
    if (ret.email) details.push({ label: "EMAIL", value: String(ret.email) })
    if (ret.uuid) details.push({ label: "MOJANG UUID", value: String(ret.uuid) })
    if (ret.steam_id_64) details.push({ label: "STEAMID64", value: String(ret.steam_id_64) })
    if (ret.total_xp !== undefined) details.push({ label: "DUOLINGO XP", value: `${ret.total_xp} XP` })
    if (ret.current_learning) details.push({ label: "LEARNING", value: String(ret.current_learning).toUpperCase() })
    if (ret.status) details.push({ label: "STATUS", value: String(ret.status) })

    const avatar =
      ret.avatar_render ||
      ret.avatar_headshot ||
      ret.avatar_url ||
      ret.avatar ||
      ret.profile_image ||
      ret.skin_texture_url ||
      null

    return {
      moduleId,
      moduleName: modDef.name,
      moduleIcon: modDef.icon,
      target,
      found: isFound,
      status: isFound ? "Verified Active" : "Not Found",
      displayName: ret.profile_name || ret.name || ret.display_name || (isFound ? target : "Unknown"),
      username: ret.username || target,
      avatarUrl: avatar,
      profileUrl: ret.profile_url || ret.url,
      idPill: ret.uuid || ret.steam_id_64 || ret.id || ret.player_id || "INDEX-OK",
      datePill: ret.created_at || (isFound ? "Active Record" : "Not Found"),
      details,
      raw: data,
    }
  }

  // 8. Pattern: { taken: true | false, ExtraData: { ... } }
  if (data.taken !== undefined) {
    const isFound = Boolean(data.taken)
    const extra = data.ExtraData || {}
    const details = []

    if (extra.UserID) details.push({ label: "USER ID", value: String(extra.UserID) })
    if (extra.Nickname) details.push({ label: "NICKNAME", value: String(extra.Nickname) })
    if (extra.RealName) details.push({ label: "REAL NAME", value: String(extra.RealName) })
    if (extra.Blurb) details.push({ label: "BIO / BLURB", value: String(extra.Blurb) })
    if (extra.CreationDate) details.push({ label: "CREATION DATE", value: String(extra.CreationDate) })
    if (extra.IsBanned !== undefined) details.push({ label: "BANNED", value: extra.IsBanned ? "Yes" : "No (Clean)" })
    if (extra.Title) details.push({ label: "PROFILE TITLE", value: String(extra.Title) })
    if (extra.Description) details.push({ label: "DESCRIPTION", value: String(extra.Description) })

    return {
      moduleId,
      moduleName: modDef.name,
      moduleIcon: modDef.icon,
      target,
      found: isFound,
      status: isFound ? "Verified Active" : "Not Found",
      displayName: extra.DisplayName || extra.Nickname || extra.RealName || extra.Title || target,
      username: extra.Username || target,
      avatarUrl: extra.ProfilePicUrl || extra.ThumbnailUrl || null,
      profileUrl: extra.ProfileUrl,
      idPill: extra.UserID ? String(extra.UserID) : "IDENT-OK",
      datePill: extra.CreationDate ? String(extra.CreationDate).split(" ")[0] : (isFound ? "Active Record" : "Not Found"),
      details,
      raw: data,
    }
  }

  // 9. Generic status check (e.g. wix, shein, office365, aliexpress, apple, spotify, etc.)
  const isFound = Boolean(
    data.exists ||
    data.registered ||
    data.emailVerified !== undefined ||
    data.accountExists ||
    data.userAuthenticatorsData
  )

  const details = []
  for (const [k, v] of Object.entries(data)) {
    if (typeof v === "string" || typeof v === "number" || typeof v === "boolean") {
      details.push({ label: k.toUpperCase().replace(/_/g, " "), value: String(v) })
    }
  }

  return {
    moduleId,
    moduleName: modDef.name,
    moduleIcon: modDef.icon,
    target,
    found: isFound,
    status: isFound ? "Registered Identity" : "Not Registered",
    displayName: target,
    username: target,
    avatarUrl: null,
    profileUrl: null,
    idPill: "VERIFIED-RECORD",
    datePill: isFound ? "Record Present" : "No Record",
    details,
    raw: data,
  }
}

export async function runMultiSearch(target) {
  const cleanTarget = target.trim()
  const isEmail = cleanTarget.includes("@")
  const isPhone = !isEmail && /^(\+?[0-9\s\-()]{7,})$/.test(cleanTarget) && cleanTarget.replace(/\D/g, "").length <= 15
  const isDiscordId = /^\d{17,21}$/.test(cleanTarget)
  const isCrypto =
    (cleanTarget.startsWith("0x") && cleanTarget.length === 42) ||
    cleanTarget.startsWith("bc1") ||
    ((cleanTarget.startsWith("1") || cleanTarget.startsWith("3")) && cleanTarget.length >= 26 && cleanTarget.length <= 35) ||
    (cleanTarget.length >= 32 && cleanTarget.length <= 44 && !cleanTarget.includes(" ") && !cleanTarget.includes("@"))

  let candidateIds = []
  if (isDiscordId) {
    candidateIds = ["discord", "breach", "phone"]
  } else if (isCrypto) {
    candidateIds = ["crypto"]
  } else if (isEmail) {
    candidateIds = ["breach", "adobe", "aliexpress", "apple", "google", "microsoft", "spotify", "github", "gravatar", "shein", "wix"]
  } else if (isPhone) {
    candidateIds = ["phone", "breach", "revolut", "aliexpress"]
  } else {
    // Username handles
    candidateIds = ["breach", "roblox", "github", "minecraft", "steam", "telegram", "tiktok", "chess", "duolingo", "x", "paypal"]
  }

  const selectedModules = OSINT_MODULES.filter((m) => candidateIds.includes(m.id))

  const promises = selectedModules.map(async (mod) => {
    try {
      const raw = await executePythonModule(mod.file, cleanTarget, 12000)
      return normalizeModuleResult(mod.id, cleanTarget, raw)
    } catch (err) {
      return {
        moduleId: mod.id,
        moduleName: mod.name,
        moduleIcon: mod.icon,
        target: cleanTarget,
        found: false,
        status: "Timeout / Error",
        details: [],
        raw: { error: err.message },
      }
    }
  })

  const results = await Promise.all(promises)
  return {
    target: cleanTarget,
    queryType: isDiscordId ? "discord" : isCrypto ? "crypto" : isEmail ? "email" : isPhone ? "phone" : "username",
    timestamp: new Date().toISOString(),
    results,
    hitsCount: results.filter((r) => r.found).length,
    totalScanned: results.length,
  }
}

const DISCORD_CLIENT_ID = process.env.DISCORD_CLIENT_ID || "1554183119408468128"
const DISCORD_CLIENT_SECRET = process.env.DISCORD_CLIENT_SECRET || "ln0H7ZjP_njrqatQ_X-oWKQFM5zJ3ovh"
const KEYS_DB_FILE = resolve(__dirname, "keys_db.json")

function loadKeysDatabase() {
  try {
    if (existsSync(KEYS_DB_FILE)) {
      const data = readFileSync(KEYS_DB_FILE, "utf8")
      return JSON.parse(data)
    }
  } catch (err) {
    console.error("[Backend] Error loading keys database:", err.message)
  }
  return []
}

function saveKeysDatabase(keys) {
  try {
    writeFileSync(KEYS_DB_FILE, JSON.stringify(keys, null, 2), "utf8")
    return true
  } catch (err) {
    console.error("[Backend] Error saving keys database:", err.message)
    return false
  }
}

const BASE32_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

export function encodeCreditsToBlock(credits) {
  const num = Math.floor(Number(credits) || 0)
  if (num > 0 && num <= 9999) return num.toString().padStart(4, "0")
  return "X" + num.toString(36).toUpperCase().padStart(3, "0").slice(-3)
}

export function decodeCreditsFromBlock(block) {
  if (!block || typeof block !== "string" || block.length !== 4) return 0
  if (block.startsWith("X")) {
    const val = parseInt(block.slice(1), 36)
    return isNaN(val) ? 0 : val
  }
  const val = parseInt(block, 10)
  return isNaN(val) ? 0 : val
}

export function computeHmacBlock(payload, secret = DISCORD_CLIENT_SECRET) {
  const hmac = createHmac("sha256", secret).update(payload).digest()
  let res = ""
  for (let i = 0; i < 4; i++) {
    res += BASE32_CHARS[hmac[i] % BASE32_CHARS.length]
  }
  return res
}

export function generateSignedLicenseKey(credits, secret = DISCORD_CLIENT_SECRET) {
  const block1 = encodeCreditsToBlock(credits)
  const rndBytes = randomBytes(4)
  let block2 = ""
  for (let i = 0; i < 4; i++) {
    block2 += BASE32_CHARS[rndBytes[i] % BASE32_CHARS.length]
  }
  const block3 = computeHmacBlock(`${block1}-${block2}`, secret)
  return `BYTES-${block1}-${block2}-${block3}`
}

export function verifySignedLicenseKey(keyString, secret = DISCORD_CLIENT_SECRET) {
  let body = String(keyString || "").replace(/[^A-Z0-9]/gi, "").toUpperCase()
  if (body.startsWith("BYTES")) body = body.slice(5)
  if (body.length !== 12) return { valid: false }

  const block1 = body.slice(0, 4)
  const block2 = body.slice(4, 8)
  const block3 = body.slice(8, 12)

  const expectedBlock3 = computeHmacBlock(`${block1}-${block2}`, secret)
  if (expectedBlock3 === block3) {
    const credits = decodeCreditsFromBlock(block1)
    if (credits > 0) {
      return {
        valid: true,
        credits,
        normalizedKey: `BYTES-${block1}-${block2}-${block3}`,
      }
    }
  }
  return { valid: false }
}

function generateLicenseKeyString() {
  return generateSignedLicenseKey(100, DISCORD_CLIENT_SECRET)
}

async function readRequestBody(req) {
  return new Promise((resolve) => {
    let accum = ""
    req.on("data", (chunk) => {
      accum += chunk
    })
    req.on("end", () => {
      try {
        resolve(accum ? JSON.parse(accum) : {})
      } catch {
        resolve({})
      }
    })
  })
}

export async function handleApiRequest(req, res) {
  const url = new URL(req.url, `http://${req.headers.host || "localhost"}`)
  const pathname = url.pathname

  const sendCors = () => {
    res.setHeader("Access-Control-Allow-Origin", "*")
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization")
  }

  if (req.method === "OPTIONS") {
    sendCors()
    res.writeHead(204)
    res.end()
    return true
  }

  // 1. GET /api/modules
  if (pathname === "/api/modules") {
    sendCors()
    res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" })
    res.end(JSON.stringify({ success: true, modules: OSINT_MODULES }))
    return true
  }

  // 2. POST /api/keys/create (Chiamata da bot Discord su VPS remota o admin)
  if (pathname === "/api/keys/create") {
    sendCors()
    const body = await readRequestBody(req)
    const credits = Number(body.credits || 100)
    const note = String(body.note || "Created via API")
    const key = (body.key && typeof body.key === "string" && body.key.trim().length > 0)
      ? body.key.trim().toUpperCase()
      : generateSignedLicenseKey(credits, DISCORD_CLIENT_SECRET)
    const createdBy = String(body.createdBy || "api:caller")

    const keys = loadKeysDatabase()
    const cleanKey = key.replace(/\s+/g, "").toUpperCase()
    let existing = keys.find((k) => String(k.key || "").replace(/\s+/g, "").toUpperCase() === cleanKey)
    if (!existing) {
      const record = {
        key: cleanKey,
        credits,
        note,
        created_at: new Date().toISOString(),
        created_by: createdBy,
        redeemed: false,
        redeemed_by: null,
        redeemed_at: null,
      }
      keys.push(record)
      saveKeysDatabase(keys)
      existing = record
    }

    res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" })
    res.end(JSON.stringify({ success: true, key: existing.key, credits: existing.credits }))
    return true
  }

  // 2b. POST /api/keys/batch-sync (Sincronizzazione massiva dal bot)
  if (pathname === "/api/keys/batch-sync") {
    sendCors()
    const body = await readRequestBody(req)
    const incomingKeys = Array.isArray(body.keys) ? body.keys : []
    const keys = loadKeysDatabase()
    let addedCount = 0

    for (const item of incomingKeys) {
      if (!item || !item.key) continue
      const cleanKey = String(item.key).replace(/\s+/g, "").toUpperCase()
      const found = keys.find((k) => String(k.key || "").replace(/\s+/g, "").toUpperCase() === cleanKey)
      if (!found) {
        keys.push({
          key: cleanKey,
          credits: Number(item.credits || 100),
          note: String(item.note || "Synced from Bot VPS"),
          created_at: item.created_at || new Date().toISOString(),
          created_by: item.created_by || "bot:sync",
          redeemed: Boolean(item.redeemed),
          redeemed_by: item.redeemed_by || null,
          redeemed_at: item.redeemed_at || null,
        })
        addedCount++
      }
    }

    if (addedCount > 0) {
      saveKeysDatabase(keys)
    }

    res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" })
    res.end(JSON.stringify({ success: true, addedCount, totalKeys: keys.length }))
    return true
  }

  // 3. POST /api/keys/redeem (Chiamata dalla Dashboard utente)
  if (pathname === "/api/keys/redeem") {
    sendCors()
    const body = await readRequestBody(req)
    const rawKey = String(body.key || "").trim().toUpperCase()
    const username = String(body.username || "operator").trim()

    if (!rawKey) {
      res.writeHead(400, { "Content-Type": "application/json; charset=utf-8" })
      res.end(JSON.stringify({ success: false, error: "Inserisci un codice key valido." }))
      return true
    }

    const norm = (s) => String(s || "").replace(/[^A-Z0-9]/gi, "").toUpperCase()
    const targetNorm = norm(rawKey)
    const cleanRaw = rawKey.replace(/\s+/g, "").toUpperCase()

    const keys = loadKeysDatabase()
    let match = keys.find((k) => {
      const kNorm = norm(k.key)
      const kClean = String(k.key || "").replace(/\s+/g, "").toUpperCase()
      return (
        kClean === cleanRaw ||
        kNorm === targetNorm ||
        (targetNorm.length >= 8 && kNorm.endsWith(targetNorm)) ||
        (kNorm.length >= 8 && targetNorm.endsWith(kNorm))
      )
    })

    // Fallback: se la chiave non è ancora nel database locale, verifichiamo la firma crittografica HMAC!
    if (!match) {
      const signedCheck = verifySignedLicenseKey(rawKey, DISCORD_CLIENT_SECRET)
      if (signedCheck.valid) {
        match = {
          key: signedCheck.normalizedKey,
          credits: signedCheck.credits,
          note: "Generata via Discord Bot (Firma Crittografica Valida)",
          created_at: new Date().toISOString(),
          created_by: "discord:bot_hmac",
          redeemed: false,
          redeemed_by: null,
          redeemed_at: null,
        }
        keys.push(match)
      }
    }

    if (!match) {
      res.writeHead(404, { "Content-Type": "application/json; charset=utf-8" })
      res.end(JSON.stringify({ success: false, error: "Codice key non valido o inesistente. Verifica i caratteri inseriti." }))
      return true
    }

    if (match.redeemed) {
      const redeemedDate = match.redeemed_at ? new Date(match.redeemed_at).toLocaleDateString("it-IT") : "precedenza"
      res.writeHead(400, { "Content-Type": "application/json; charset=utf-8" })
      res.end(JSON.stringify({
        success: false,
        error: `Questa key è già stata riscattata in data ${redeemedDate} da @${match.redeemed_by || "un altro utente"}.`,
      }))
      return true
    }

    // Riscatto valido!
    match.redeemed = true
    match.redeemed_at = new Date().toISOString()
    match.redeemed_by = username
    saveKeysDatabase(keys)

    res.writeHead(200, { "Content-Type": "application/json; charset=utf-8" })
    res.end(JSON.stringify({
      success: true,
      key: match.key,
      creditsAdded: match.credits,
      note: match.note,
      message: `Key riscattata con successo! +${match.credits} crediti accreditati.`,
    }))
    return true
  }

  // 4. GET /api/keys/list (Verifica o statistiche)
  if (pathname === "/api/keys/list") {
    const keys = loadKeysDatabase()
    res.writeHead(200, {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*",
    })
    res.end(JSON.stringify({
      success: true,
      total: keys.length,
      active: keys.filter((k) => !k.redeemed).length,
      redeemed: keys.filter((k) => k.redeemed).length,
      keys: keys.slice(-20).reverse(),
    }))
    return true
  }

  // 5. GET /api/auth/discord/login (Avvia OAuth2 Discord)
  if (pathname === "/api/auth/discord/login") {
    const host = req.headers.host || "localhost:4173"
    const proto = req.headers["x-forwarded-proto"] || (host.includes("localhost") || host.includes("127.0.0.1") ? "http" : "https")
    const redirectUri = `${proto}://${host}/api/auth/discord/callback`
    const authUrl = `https://discord.com/oauth2/authorize?client_id=${DISCORD_CLIENT_ID}&response_type=code&redirect_uri=${encodeURIComponent(redirectUri)}&scope=identify%20email`

    res.writeHead(302, { Location: authUrl })
    res.end()
    return true
  }

  // 6. GET /api/auth/discord/callback (Riceve il codice OAuth2 da Discord)
  if (pathname === "/api/auth/discord/callback") {
    const code = url.searchParams.get("code")
    const host = req.headers.host || "localhost:4173"
    const proto = req.headers["x-forwarded-proto"] || (host.includes("localhost") || host.includes("127.0.0.1") ? "http" : "https")
    const redirectUri = `${proto}://${host}/api/auth/discord/callback`

    if (!code) {
      const err = url.searchParams.get("error_description") || url.searchParams.get("error") || "Accesso annullato"
      res.writeHead(302, { Location: `/login?error=${encodeURIComponent(err)}` })
      res.end()
      return true
    }

    try {
      const tokenResp = await fetch("https://discord.com/api/oauth2/token", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          client_id: DISCORD_CLIENT_ID,
          client_secret: DISCORD_CLIENT_SECRET,
          grant_type: "authorization_code",
          code: code,
          redirect_uri: redirectUri,
        }),
      })

      const tokenData = await tokenResp.json()

      if (tokenData.access_token) {
        const userResp = await fetch("https://discord.com/api/users/@me", {
          headers: { Authorization: `Bearer ${tokenData.access_token}` },
        })
        const dUser = await userResp.json()

        const avatarUrl = dUser.avatar
          ? `https://cdn.discordapp.com/avatars/${dUser.id}/${dUser.avatar}.png?size=128`
          : "terminal"

        const username = dUser.username || `discord_${dUser.id.slice(-4)}`
        const displayName = dUser.global_name || dUser.username || username
        const email = dUser.email || `${username.toLowerCase()}@discord.bytesint.xyz`

        const userPayload = {
          username,
          displayName,
          email,
          avatar: avatarUrl,
          credits: 20, // 20 crediti giornalieri di benvenuto
          dailyCredits: 20,
          lastDailyRenewal: new Date().toISOString().slice(0, 10),
          plan: "Discord Free Tier",
          apiKey: `by_live_${randomBytes(12).toString("hex")}`,
          joinedAt: new Date().toLocaleDateString("en-US", { month: "short", year: "numeric" }),
          discordId: dUser.id,
        }

        const encodedPayload = Buffer.from(JSON.stringify(userPayload)).toString("base64")
        const redirectUrl = `/dashboard?auth=discord_success&session=${encodeURIComponent(encodedPayload)}`

        // Expire any lingering cookie to prevent stale session overwrites
        res.setHeader("Set-Cookie", "bytesint_auth=; Path=/; Max-Age=0; SameSite=Lax; expires=Thu, 01 Jan 1970 00:00:00 GMT")

        // Immediate 302 Redirect to Dashboard (no getting stuck on splash screen)
        res.writeHead(302, {
          Location: redirectUrl,
          "Content-Type": "text/html; charset=utf-8",
        })
        res.end(`<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0;url=${redirectUrl}">
  <title>Reindirizzamento...</title>
</head>
<body style="background:#060608;color:#fff;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;">
  <div style="text-align:center;">
    <p>Accesso completato! Reindirizzamento alla dashboard in corso...</p>
    <a href="${redirectUrl}" style="color:#5865F2;text-decoration:underline;font-size:14px;">Clicca qui se non vieni reindirizzato automaticamente</a>
  </div>
  <script>
    try {
      localStorage.setItem("bytesint_user_session", JSON.stringify(${JSON.stringify(userPayload)}));
      sessionStorage.setItem("bytesint_user_session", JSON.stringify(${JSON.stringify(userPayload)}));
      window.dispatchEvent(new Event("bytesint-auth-change"));
    } catch(e) {}
    window.location.replace("${redirectUrl}");
  </script>
</body>
</html>`)
        return true
      } else {
        // Errore token Discord (es. redirect_uri non ancora aggiunto nel portale Discord Developer)
        const errMsg = tokenData.error_description || tokenData.error || "Token non rilasciato"
        const fallbackHtml = `<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <title>Configurazione Discord OAuth</title>
</head>
<body style="background:#070709;color:#fff;font-family:system-ui,-apple-system,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;padding:20px;box-sizing:border-box;">
  <div style="max-width:520px;background:#121217;padding:32px;border-radius:28px;border:1px solid rgba(255,255,255,0.12);text-align:center;box-shadow:0 20px 40px rgba(0,0,0,0.8);">
    <div style="width:54px;height:54px;margin:0 auto 16px;background:rgba(255,100,100,0.15);border:1px solid rgba(255,100,100,0.3);border-radius:50%;display:flex;align-items:center;justify-content:center;color:#ff6b6b;font-size:24px;">⚠</div>
    <h2 style="font-size:20px;margin:0 0 10px;font-weight:600;">Configurazione Discord OAuth Necessaria</h2>
    <p style="font-size:13px;color:#bbb;line-height:1.5;margin:0 0 16px;">
      Discord ha restituito: <br><strong style="color:#ff8787;">${errMsg}</strong>
    </p>
    <div style="background:#09090c;border:1px solid rgba(255,255,255,0.08);padding:14px;border-radius:14px;text-align:left;font-size:12px;color:#aaa;line-height:1.6;margin-bottom:20px;">
      <strong>Come risolvere:</strong>
      <ol style="margin:8px 0 0;padding-left:18px;">
        <li>Apri il <a href="https://discord.com/developers/applications/1554183119408468128/oauth2" target="_blank" style="color:#5865F2;">Discord Developer Portal</a></li>
        <li>Vai nella sezione <strong>OAuth2 → Redirects</strong></li>
        <li>Aggiungi questo URL esatto:</li>
        <code style="background:#000;display:block;padding:6px 10px;border-radius:8px;margin-top:6px;color:#00ff88;font-family:monospace;word-break:break-all;">${redirectUri}</code>
        <li style="margin-top:6px;">Salva le modifiche (Save Changes)</li>
      </ol>
    </div>
    <div style="display:flex;gap:12px;justify-content:center;">
      <a href="/login" style="padding:10px 22px;border-radius:99px;background:#fff;color:#000;text-decoration:none;font-size:13px;font-weight:600;">Torna al Login</a>
      <button onclick="window.history.back()" style="padding:10px 22px;border-radius:99px;border:1px solid rgba(255,255,255,0.2);background:transparent;color:#fff;cursor:pointer;font-size:13px;">Riprova</button>
    </div>
  </div>
</body>
</html>`
        res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" })
        res.end(fallbackHtml)
        return true
      }
    } catch (e) {
      res.writeHead(500, { "Content-Type": "text/plain; charset=utf-8" })
      res.end("Errore durante autenticazione Discord: " + e.message)
      return true
    }
  }

  if (pathname === "/api/search") {
    let target = url.searchParams.get("target") || ""
    let module = url.searchParams.get("module") || "multisearch"

    if (req.method === "POST") {
      try {
        const bodyText = await new Promise((resolve) => {
          let accum = ""
          req.on("data", (chunk) => {
            accum += chunk
          })
          req.on("end", () => resolve(accum))
        })
        if (bodyText) {
          const parsed = JSON.parse(bodyText)
          if (parsed.target) target = parsed.target
          if (parsed.module) module = parsed.module
        }
      } catch {
        // Fallback to query params
      }
    }

    target = target.trim()
    if (!target) {
      res.writeHead(400, {
        "Content-Type": "application/json; charset=utf-8",
        "Access-Control-Allow-Origin": "*",
      })
      res.end(JSON.stringify({ success: false, error: "Target identifier is required" }))
      return true
    }

    try {
      if (module === "multisearch") {
        const multiResult = await runMultiSearch(target)
        res.writeHead(200, {
          "Content-Type": "application/json; charset=utf-8",
          "Access-Control-Allow-Origin": "*",
        })
        res.end(JSON.stringify({ success: true, mode: "multi", result: multiResult }))
        return true
      }

      const mod = OSINT_MODULES.find((m) => m.id === module)
      const targetScript = mod ? mod.file : `${module}.py`
      const raw = await executePythonModule(targetScript, target)
      const normalized = normalizeModuleResult(mod ? mod.id : module, target, raw)

      // Parallel breach threat intel check (Hudson Rock & LeakCheck)
      let breachIntel = null
      if (module !== "breach") {
        try {
          const bRaw = await executePythonModule("Breach/leak_intelligence.py", target, 6000)
          if (bRaw && bRaw.success && bRaw.data?.return) {
            breachIntel = bRaw.data.return
          }
        } catch {}
      }

      res.writeHead(200, {
        "Content-Type": "application/json; charset=utf-8",
        "Access-Control-Allow-Origin": "*",
      })
      res.end(JSON.stringify({ success: true, mode: "single", result: normalized, breachIntel }))
      return true
    } catch (err) {
      res.writeHead(500, {
        "Content-Type": "application/json; charset=utf-8",
        "Access-Control-Allow-Origin": "*",
      })
      res.end(JSON.stringify({ success: false, error: err.message }))
      return true
    }
  }

  return false
}
