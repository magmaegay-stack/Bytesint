import { useEffect, useLayoutEffect, useRef, useState } from "react"

export function PackSwitch({
  pack,
  onChange,
}: {
  pack: "starter" | "advanced"
  onChange: (next: "starter" | "advanced") => void
}) {
  const starterRef = useRef<HTMLButtonElement>(null)
  const advancedRef = useRef<HTMLButtonElement>(null)
  const [pill, setPill] = useState({ x: 2, width: 0 })

  useLayoutEffect(() => {
    const measure = () => {
      const button = pack === "starter" ? starterRef.current : advancedRef.current
      const parent = button?.parentElement
      if (!button || !parent) return
      const parentBox = parent.getBoundingClientRect()
      const buttonBox = button.getBoundingClientRect()
      setPill({ x: buttonBox.left - parentBox.left, width: buttonBox.width })
    }
    measure()
    window.addEventListener("resize", measure)
    return () => window.removeEventListener("resize", measure)
  }, [pack])

  const bar = Math.min(28, Math.max(18, pill.width * 0.42))
  return (
    <div className="relative z-10 mx-auto flex w-fit items-center gap-1 rounded-full bg-black/55 px-1.5 py-1">
      <span
        className="pointer-events-none absolute bottom-1.5 h-0.5 rounded-full bg-white transition-all duration-500 ease-[cubic-bezier(0.22,1,0.36,1)]"
        style={{
          width: bar,
          transform: `translateX(${pill.x + (pill.width - bar) / 2}px)`,
        }}
      />
      <button ref={starterRef} type="button" onClick={() => onChange("starter")} className="relative z-10 rounded-full px-4 py-2 text-sm text-white">
        Starter packs
      </button>
      <button ref={advancedRef} type="button" onClick={() => onChange("advanced")} className="relative z-10 rounded-full px-4 py-2 text-sm text-white">
        Advanced packs
      </button>
    </div>
  )
}

export function RisingPrice({ value, from }: { value: number; from: number }) {
  const [text, setText] = useState(value.toFixed(2))
  useEffect(() => {
    const start = performance.now()
    let frame = 0
    const run = (now: number) => {
      const t = Math.min(1, (now - start) / 700)
      const eased = 1 - (1 - t) ** 3
      setText((from + (value - from) * eased).toFixed(2))
      if (t < 1) frame = requestAnimationFrame(run)
    }
    frame = requestAnimationFrame(run)
    return () => cancelAnimationFrame(frame)
  }, [value, from])
  return <>{text}</>
}
