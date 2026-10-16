import { addIcon } from "@iconify/react"
import at from "@iconify-icons/fa6-solid/at"
import book from "@iconify-icons/fa6-solid/book"
import bookOpen from "@iconify-icons/fa6-solid/book-open"
import chevronDown from "@iconify-icons/fa6-solid/chevron-down"
import chevronLeft from "@iconify-icons/fa6-solid/chevron-left"
import chevronRight from "@iconify-icons/fa6-solid/chevron-right"
import circleCheck from "@iconify-icons/fa6-solid/circle-check"
import circleQuestion from "@iconify-icons/fa6-solid/circle-question"
import circleXmark from "@iconify-icons/fa6-solid/circle-xmark"
import comments from "@iconify-icons/fa6-solid/comments"
import envelope from "@iconify-icons/fa6-solid/envelope"
import fileLines from "@iconify-icons/fa6-solid/file-lines"
import fingerprint from "@iconify-icons/fa6-solid/fingerprint"
import gaugeHigh from "@iconify-icons/fa6-solid/gauge-high"
import globe from "@iconify-icons/fa6-solid/globe"
import image from "@iconify-icons/fa6-solid/image"
import keyIcon from "@iconify-icons/fa6-solid/key"
import lifeRing from "@iconify-icons/fa6-solid/life-ring"
import link from "@iconify-icons/fa6-solid/link"
import lock from "@iconify-icons/fa6-solid/lock"
import magnifyingGlass from "@iconify-icons/fa6-solid/magnifying-glass"
import networkWired from "@iconify-icons/fa6-solid/network-wired"
import phone from "@iconify-icons/fa6-solid/phone"
import scaleBalanced from "@iconify-icons/fa6-solid/scale-balanced"
import shieldHalved from "@iconify-icons/fa6-solid/shield-halved"
import user from "@iconify-icons/fa6-solid/user"
import wallet from "@iconify-icons/fa6-solid/wallet"
import arrowUpRight from "@iconify-icons/lucide/arrow-up-right"
import circleSlashed from "@iconify-icons/lucide/circle-slashed"
import check from "@iconify-icons/lucide/check"
import creditCard from "@iconify-icons/lucide/credit-card"
import database from "@iconify-icons/lucide/database"
import fileText from "@iconify-icons/lucide/file-text"
import headphones from "@iconify-icons/lucide/headphones"
import lucideLink from "@iconify-icons/lucide/link"
import scan from "@iconify-icons/lucide/scan"
import lucideWallet from "@iconify-icons/lucide/wallet"
import xIcon from "@iconify-icons/lucide/x"
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import App from "./App"
import "lenis/dist/lenis.css"
import "./index.css"

addIcon("fa6-solid:at", at)
addIcon("fa6-solid:book", book)
addIcon("fa6-solid:book-open", bookOpen)
addIcon("fa6-solid:chevron-down", chevronDown)
addIcon("fa6-solid:chevron-left", chevronLeft)
addIcon("fa6-solid:chevron-right", chevronRight)
addIcon("fa6-solid:circle-check", circleCheck)
addIcon("fa6-solid:circle-question", circleQuestion)
addIcon("fa6-solid:circle-xmark", circleXmark)
addIcon("fa6-solid:comments", comments)
addIcon("fa6-solid:envelope", envelope)
addIcon("fa6-solid:file-lines", fileLines)
addIcon("fa6-solid:fingerprint", fingerprint)
addIcon("fa6-solid:gauge-high", gaugeHigh)
addIcon("fa6-solid:globe", globe)
addIcon("fa6-solid:image", image)
addIcon("fa6-solid:key", keyIcon)
addIcon("fa6-solid:life-ring", lifeRing)
addIcon("fa6-solid:link", link)
addIcon("fa6-solid:lock", lock)
addIcon("fa6-solid:magnifying-glass", magnifyingGlass)
addIcon("fa6-solid:network-wired", networkWired)
addIcon("fa6-solid:phone", phone)
addIcon("fa6-solid:scale-balanced", scaleBalanced)
addIcon("fa6-solid:shield-halved", shieldHalved)
addIcon("fa6-solid:user", user)
addIcon("fa6-solid:wallet", wallet)
addIcon("lucide:arrow-up-right", arrowUpRight)
addIcon("lucide:circle-slashed", circleSlashed)
addIcon("lucide:check", check)
addIcon("lucide:credit-card", creditCard)
addIcon("lucide:database", database)
addIcon("lucide:file-text", fileText)
addIcon("lucide:headphones", headphones)
addIcon("lucide:link", lucideLink)
addIcon("lucide:scan", scan)
addIcon("lucide:wallet", lucideWallet)
addIcon("lucide:x", xIcon)

const root = document.getElementById("root")
if (!root) throw new Error("Missing root")

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
