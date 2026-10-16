import { createServer } from "node:http"
import { readFile, stat } from "node:fs/promises"
import { extname, join, resolve, sep } from "node:path"
import { fileURLToPath } from "node:url"
import { handleApiRequest } from "./osint_runner.mjs"

const root = resolve(fileURLToPath(new URL("./dist", import.meta.url)))
const port = Number(process.env.PORT || 4173)

const types = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml",
  ".woff2": "font/woff2",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".webp": "image/webp",
}

const headers = {
  "X-Content-Type-Options": "nosniff",
  "X-Frame-Options": "DENY",
  "Referrer-Policy": "no-referrer",
  "X-DNS-Prefetch-Control": "off",
  "X-Permitted-Cross-Domain-Policies": "none",
  "Cross-Origin-Opener-Policy": "same-origin",
  "Cross-Origin-Resource-Policy": "same-origin",
  "Origin-Agent-Cluster": "?1",
  "Permissions-Policy":
    "accelerometer=(), autoplay=(), camera=(), display-capture=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=(), interest-cohort=()",
  "Content-Security-Policy": [
    "default-src 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "form-action 'self' https://discord.com",
    "script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com",
    "style-src 'self' 'unsafe-inline'",
    "style-src-elem 'self' 'unsafe-inline'",
    "img-src 'self' data: https: blob: https://challenges.cloudflare.com https://api.iconify.design",
    "font-src 'self' data:",
    "connect-src 'self' https: https://challenges.cloudflare.com https://api.iconify.design https://api.simplesvg.com https://api.unisvg.com",
    "frame-src https://challenges.cloudflare.com",
    "worker-src 'none'",
    "manifest-src 'self'",
  ].join("; "),
  "Cache-Control": "no-store",
}

function insideRoot(file) {
  return file === root || file.startsWith(root + sep)
}

const server = createServer(async (req, res) => {
  for (const [key, value] of Object.entries(headers)) res.setHeader(key, value)

  if (req.url && req.url.startsWith("/api/")) {
    const handled = await handleApiRequest(req, res)
    if (handled) return
  }

  if (!req.url || (req.method !== "GET" && req.method !== "HEAD")) {
    res.writeHead(405)
    res.end("method not allowed")
    return
  }

  let pathname = "/"
  try {
    pathname = decodeURIComponent(new URL(req.url, `http://${req.headers.host || "bytesint.xyz"}`).pathname)
  } catch {
    res.writeHead(400)
    res.end("bad request")
    return
  }
  if (pathname.includes("\0")) {
    res.writeHead(400)
    res.end("bad request")
    return
  }

  const requested = resolve(root, `.${pathname}`)
  if (!insideRoot(requested)) {
    res.writeHead(403)
    res.end("forbidden")
    return
  }

  let file = requested
  try {
    const info = await stat(file)
    if (info.isDirectory()) file = join(file, "index.html")
  } catch {
    if (extname(pathname)) {
      res.writeHead(404)
      res.end("not found")
      return
    }
    file = join(root, "index.html")
  }

  if (!insideRoot(file)) {
    res.writeHead(403)
    res.end("forbidden")
    return
  }

  try {
    const body = await readFile(file)
    res.writeHead(200, { "Content-Type": types[extname(file)] || "application/octet-stream" })
    res.end(req.method === "HEAD" ? undefined : body)
  } catch {
    res.writeHead(404)
    res.end("not found")
  }
})

server.listen(port, "0.0.0.0", () => {
  console.log(`bytesint platform listening on port ${port} -> https://bytesint.xyz`)
})
