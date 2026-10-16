import { Component, type ReactNode, type ErrorInfo } from "react"
import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom"
import { DashboardPage, LoginPage, RegisterPage } from "./auth"
import { Landing } from "./landing"
import { ContactPage, DiscordPage, DocsPage, FaqPage, HelpPage, LegalPage, PricingPage, StatusPage } from "./pages"
import { Shell } from "./shell"
import { getUser, useUserSession } from "./session"

class ErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean; error: Error | null }> {
  state = { hasError: false, error: null as Error | null }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-[60vh] flex-col items-center justify-center p-6 text-center text-white">
          <div className="glass rounded-3xl border border-white/20 p-8 max-w-md shadow-2xl backdrop-blur-2xl">
            <h2 className="text-xl font-medium">Sessione ripristinata</h2>
            <p className="mt-2 text-xs text-white/60">È stato evitato un blocco della schermata.</p>
            <button
              type="button"
              onClick={() => {
                this.setState({ hasError: false, error: null })
                window.location.href = "/"
              }}
              className="mt-5 rounded-full bg-white px-6 py-2.5 text-xs font-semibold text-black hover:bg-white/90 shadow-lg"
            >
              Torna alla Home
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

function DashboardGate() {
  const user = useUserSession() || getUser()
  if (!user) {
    return <Navigate to="/login" replace />
  }
  return <DashboardPage />
}

export default function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <Shell>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/contact" element={<ContactPage />} />
            <Route path="/contacts" element={<ContactPage />} />
            <Route path="/pricing" element={<PricingPage />} />
            <Route path="/status" element={<StatusPage />} />
            <Route path="/faq" element={<FaqPage />} />
            <Route path="/help" element={<HelpPage />} />
            <Route path="/discord" element={<DiscordPage />} />
            <Route path="/documentation" element={<DocsPage />} />
            <Route path="/docs" element={<DocsPage />} />
            <Route path="/terms" element={<LegalPage kind="terms" />} />
            <Route path="/privacy" element={<LegalPage kind="privacy" />} />
            <Route path="/legal" element={<LegalPage kind="legal" />} />
            <Route path="/eula" element={<LegalPage kind="eula" />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/sign-in" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/dashboard" element={<DashboardGate />} />
          </Routes>
        </Shell>
      </ErrorBoundary>
    </BrowserRouter>
  )
}

