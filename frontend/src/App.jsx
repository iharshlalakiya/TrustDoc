import { Routes, Route } from 'react-router-dom'
import UploadPage from './pages/UploadPage.jsx'
import ReportPage from './pages/ReportPage.jsx'

export default function App() {
  return (
    <div className="min-h-screen bg-surface-950 text-slate-100 font-sans">
      {/* Ambient background glow */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-40 h-[600px] w-[600px] rounded-full bg-brand-600/10 blur-[120px]" />
        <div className="absolute -right-40 top-1/3 h-[500px] w-[500px] rounded-full bg-purple-600/8 blur-[100px]" />
        <div className="absolute -bottom-40 left-1/3 h-[400px] w-[400px] rounded-full bg-brand-500/6 blur-[80px]" />
      </div>

      {/* Navigation */}
      <nav className="relative z-10 border-b border-white/5">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <a href="/" className="flex items-center gap-2.5 group">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500 to-purple-600 shadow-lg shadow-brand-500/20 group-hover:shadow-brand-500/40 transition-shadow">
              <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
              </svg>
            </div>
            <span className="text-lg font-bold tracking-tight">
              Trust<span className="text-brand-400">Doc</span>
            </span>
          </a>
          <span className="hidden sm:inline-flex items-center gap-1.5 rounded-full bg-brand-500/10 px-3 py-1 text-xs font-medium text-brand-300 ring-1 ring-brand-500/20">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Document Forensics AI
          </span>
        </div>
      </nav>

      {/* Routes */}
      <main className="relative z-10">
        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/report/:documentId" element={<ReportPage />} />
        </Routes>
      </main>
    </div>
  )
}
