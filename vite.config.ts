import { defineConfig, type Connect, type Plugin } from "vite"
import react from "@vitejs/plugin-react"
import path from "node:path"

const baseHeaders: Record<string, string> = {
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
}

// @ts-ignore
import { handleApiRequest } from "./osint_runner.mjs"

function contentSecurityPolicy(dev: boolean) {
  const turnstile = "https://challenges.cloudflare.com"
  return [
    "default-src 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "form-action 'self' https://discord.com",
    dev
      ? `script-src 'self' 'unsafe-inline' 'unsafe-eval' ${turnstile}`
      : `script-src 'self' 'unsafe-inline' ${turnstile}`,
    "style-src 'self' 'unsafe-inline'",
    "style-src-elem 'self' 'unsafe-inline'",
    `img-src 'self' data: https: blob: https://api.iconify.design ${turnstile}`,
    "font-src 'self' data:",
    dev
      ? `connect-src 'self' ws: wss: https: https://api.iconify.design https://api.simplesvg.com https://api.unisvg.com ${turnstile}`
      : `connect-src 'self' https: https://api.iconify.design https://api.simplesvg.com https://api.unisvg.com ${turnstile}`,
    `frame-src ${turnstile}`,
    "worker-src 'none'",
    "manifest-src 'self'",
  ].join("; ")
}

function applyHeaders(middlewares: Connect.Server, dev: boolean) {
  const headers = {
    ...baseHeaders,
    "Content-Security-Policy": contentSecurityPolicy(dev),
  }
  middlewares.use((_req, res, next) => {
    for (const [key, value] of Object.entries(headers)) res.setHeader(key, value)
    next()
  })
}

function osintApiPlugin(): Plugin {
  return {
    name: "osint-api",
    configureServer(server) {
      applyHeaders(server.middlewares, true)
      server.middlewares.use(async (req, res, next) => {
        if (req.url && req.url.startsWith("/api/")) {
          const handled = await handleApiRequest(req, res)
          if (handled) return
        }
        next()
      })
    },
    configurePreviewServer(server) {
      applyHeaders(server.middlewares, false)
      server.middlewares.use(async (req, res, next) => {
        if (req.url && req.url.startsWith("/api/")) {
          const handled = await handleApiRequest(req, res)
          if (handled) return
        }
        next()
      })
    },
  }
}

export default defineConfig({
  plugins: [react(), osintApiPlugin()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: false,
    allowedHosts: true,
  },
  preview: {
    host: "0.0.0.0",
    port: 4173,
    strictPort: false,
    allowedHosts: true,
  },
  build: {
    sourcemap: false,
    target: "es2022",
  },
})
