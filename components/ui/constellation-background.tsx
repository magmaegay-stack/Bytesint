import { useEffect, useRef } from "react"

export function ConstellationBackground() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    let animationFrameId: number
    let width = (canvas.width = window.innerWidth)
    let height = (canvas.height = window.innerHeight)

    let mouseX = -1000
    let mouseY = -1000

    const onResize = () => {
      if (!canvas) return
      width = canvas.width = window.innerWidth
      height = canvas.height = window.innerHeight
    }

    const onMouseMove = (e: MouseEvent) => {
      mouseX = e.clientX
      mouseY = e.clientY
    }

    const onMouseLeave = () => {
      mouseX = -1000
      mouseY = -1000
    }

    window.addEventListener("resize", onResize)
    window.addEventListener("mousemove", onMouseMove)
    document.addEventListener("mouseleave", onMouseLeave)

    // Particle setup
    const particleCount = Math.min(Math.floor((width * height) / 18000), 75)
    const particles: Array<{
      x: number
      y: number
      vx: number
      vy: number
      radius: number
      alpha: number
    }> = []

    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.45,
        vy: (Math.random() - 0.5) * 0.45,
        radius: Math.random() * 1.6 + 1.2,
        alpha: Math.random() * 0.45 + 0.35,
      })
    }

    const draw = () => {
      ctx.clearRect(0, 0, width, height)

      // Update and draw particles
      for (let i = 0; i < particles.length; i++) {
        const p = particles[i]
        p.x += p.vx
        p.y += p.vy

        // Wrap around boundaries smoothly
        if (p.x < 0) p.x = width
        else if (p.x > width) p.x = 0
        if (p.y < 0) p.y = height
        else if (p.y > height) p.y = 0

        // Subtle mouse interaction
        const mdx = mouseX - p.x
        const mdy = mouseY - p.y
        const mdist = Math.sqrt(mdx * mdx + mdy * mdy)
        if (mdist < 160) {
          const force = (1 - mdist / 160) * 0.5
          p.x -= (mdx / mdist) * force
          p.y -= (mdy / mdist) * force

          // Connection line to cursor
          ctx.beginPath()
          ctx.moveTo(p.x, p.y)
          ctx.lineTo(mouseX, mouseY)
          ctx.strokeStyle = `rgba(255, 255, 255, ${(1 - mdist / 160) * 0.28})`
          ctx.lineWidth = 0.9
          ctx.stroke()
        }

        // Draw particle node
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(255, 255, 255, ${p.alpha})`
        ctx.shadowColor = "rgba(255, 255, 255, 0.4)"
        ctx.shadowBlur = 4
        ctx.fill()
        ctx.shadowBlur = 0

        // Draw connections
        for (let j = i + 1; j < particles.length; j++) {
          const p2 = particles[j]
          const dx = p.x - p2.x
          const dy = p.y - p2.y
          const dist = Math.sqrt(dx * dx + dy * dy)

          if (dist < 140) {
            const lineAlpha = (1 - dist / 140) * 0.22
            ctx.beginPath()
            ctx.moveTo(p.x, p.y)
            ctx.lineTo(p2.x, p2.y)
            ctx.strokeStyle = `rgba(255, 255, 255, ${lineAlpha})`
            ctx.lineWidth = 0.8
            ctx.stroke()
          }
        }
      }

      animationFrameId = requestAnimationFrame(draw)
    }

    draw()

    return () => {
      window.removeEventListener("resize", onResize)
      window.removeEventListener("mousemove", onMouseMove)
      document.removeEventListener("mouseleave", onMouseLeave)
      cancelAnimationFrame(animationFrameId)
    }
  }, [])

  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      {/* Subtle cyber grid pattern */}
      <div className="cyber-grid absolute inset-0 opacity-40 [mask-image:radial-gradient(ellipse_at_center,black_40%,transparent_80%)]" />

      {/* Circle effects ("effetti a cerchio"): Concentric pulsing sonar rings */}
      <div className="absolute left-1/2 top-1/3 -translate-x-1/2 -translate-y-1/2 pointer-events-none">
        {/* Pulsing Sonar Rings */}
        <div className="absolute h-96 w-96 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/[0.08] animate-sonar" />
        <div
          className="absolute h-96 w-96 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/[0.06] animate-sonar"
          style={{ animationDelay: "1s" }}
        />
        <div
          className="absolute h-96 w-96 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/[0.04] animate-sonar"
          style={{ animationDelay: "2s" }}
        />

        {/* Concentric HUD Reticles & Ticks */}
        <div className="absolute h-[520px] w-[520px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/[0.07] border-dashed animate-reticle-slow" />
        <div className="absolute h-[340px] w-[340px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/[0.09]" />
        <div className="absolute h-[180px] w-[180px] -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/[0.12]" />

        {/* Rotating Circular Radar Beam Sweep */}
        <div className="absolute h-[500px] w-[500px] -translate-x-1/2 -translate-y-1/2 rounded-full overflow-hidden animate-radar-sweep opacity-30">
          <div className="h-full w-full bg-[conic-gradient(from_0deg_at_50%_50%,rgba(255,255,255,0.2)_0deg,rgba(255,255,255,0)_60deg,transparent_360deg)]" />
        </div>

        {/* Central Crosshairs */}
        <div className="absolute h-[540px] w-px -translate-x-1/2 -translate-y-1/2 bg-white/[0.05]" />
        <div className="absolute w-[540px] h-px -translate-x-1/2 -translate-y-1/2 bg-white/[0.05]" />
      </div>

      {/* Radial soft glow */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_35%,rgba(255,255,255,0.08),transparent_70%)]" />

      {/* Interactive Constellation Particle Canvas */}
      <canvas ref={canvasRef} className="absolute inset-0 block h-full w-full" />
    </div>
  )
}

