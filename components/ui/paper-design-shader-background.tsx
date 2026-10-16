"use client"

import { GrainGradient } from "@paper-design/shaders-react"

export function GradientBackground() {
  return (
    <div className="absolute inset-0 -z-10">
      <GrainGradient
        style={{ height: "100%", width: "100%" }}
        colorBack="hsl(0, 0%, 2%)"
        softness={0.88}
        intensity={0.38}
        noise={0.015}
        shape="corners"
        offsetX={0}
        offsetY={0}
        scale={1.0}
        rotation={0}
        speed={0.6}
        colors={["hsl(0, 0%, 26%)", "hsl(0, 0%, 14%)", "hsl(0, 0%, 6%)"]}
      />
    </div>
  )
}
