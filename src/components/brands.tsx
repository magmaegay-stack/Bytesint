import type { SimpleIcon } from "simple-icons"
import {
  siApple,
  siBitcoin,
  siCloudflare,
  siDiscord,
  siEthereum,
  siGithub,
  siGoogle,
  siInstagram,
  siProton,
  siMastodon,
  siPaypal,
  siReddit,
  siSignal,
  siSteam,
  siTelegram,
  siWhatsapp,
  siWikipedia,
  siX,
} from "simple-icons"

export const brands: SimpleIcon[] = [
  siGithub,
  siTelegram,
  siX,
  siDiscord,
  siReddit,
  siInstagram,
  siProton,
  siWhatsapp,
  siSignal,
  siWikipedia,
  siGoogle,
  siApple,
  siSteam,
  siMastodon,
  siBitcoin,
  siEthereum,
  siPaypal,
  siCloudflare,
]

export function BrandMark({ icon, className = "h-5 w-5" }: { icon: SimpleIcon; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={20}
      height={20}
      className={`shrink-0 inline-block ${className}`}
      style={{ width: "20px", height: "20px", maxWidth: "20px", maxHeight: "20px" }}
      role="img"
      aria-label={icon.title}
    >
      <path fill="currentColor" d={icon.path} />
    </svg>
  )
}
