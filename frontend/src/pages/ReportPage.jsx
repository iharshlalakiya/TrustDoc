import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import RiskScoreGauge from '../components/RiskScoreGauge.jsx'
import RiskRadarChart from '../components/RiskRadarChart.jsx'
import TamperHeatmapViewer from '../components/TamperHeatmapViewer.jsx'

const API = '/api'

/* ── Module display config ─────────────────────────────────────────────── */
const MODULE_META = {
  1:  { name: 'Classification',       icon: '📄', desc: 'Document type & domain detection' },
  2:  { name: 'OCR Validation',       icon: '🔍', desc: 'Text integrity & homoglyph detection' },
  5:  { name: 'Metadata Analysis',    icon: '🧬', desc: 'Authorship & timestamp forensics' },
  6:  { name: 'Content Consistency',  icon: '📊', desc: 'Quantitative claim verification' },
  7:  { name: 'Compliance Review',    icon: '⚖️', desc: 'Regulatory & PII risk audit' },
  9:  { name: 'Risk Scoring',         icon: '📈', desc: 'Weighted risk aggregation' },
  10: { name: 'Verdict Report',       icon: '🏛️', desc: 'AI-generated final assessment' },
}

/* ── Risk level badge ──────────────────────────────────────────────────── */
function RiskBadge({ level }) {
  const styles = {
    Low:    'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30',
    Medium: 'bg-amber-500/15 text-amber-300 ring-amber-500/30',
    High:   'bg-red-500/15 text-red-300 ring-red-500/30',
  }
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3.5 py-1 text-xs font-semibold ring-1 ${styles[level] || styles.Medium}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${level === 'Low' ? 'bg-emerald-400' : level === 'High' ? 'bg-red-400' : 'bg-amber-400'}`} />
      {level} Risk
    </span>
  )
}

/* ── Action badge ──────────────────────────────────────────────────────── */
function ActionBadge({ action }) {
  const styles = {
    Accept: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30',
    Review: 'bg-amber-500/15 text-amber-300 ring-amber-500/30',
    Reject: 'bg-red-500/15 text-red-300 ring-red-500/30',
  }
  const icons = {
    Accept: '✓',
    Review: '⚠',
    Reject: '✕',
  }
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3.5 py-1 text-xs font-semibold ring-1 ${styles[action] || styles.Review}`}>
      <span className="text-sm">{icons[action] || '?'}</span>
      {action}
    </span>
  )
}

/* ── Flag badge ────────────────────────────────────────────────────────── */
function FlagBadge({ severity, children }) {
  const styles = {
    High:   'bg-red-500/10 text-red-300 border-red-500/20',
    Medium: 'bg-amber-500/10 text-amber-300 border-amber-500/20',
    Low:    'bg-blue-500/10 text-blue-300 border-blue-500/20',
    Info:   'bg-blue-500/10 text-blue-300 border-blue-500/20',
  }
  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${styles[severity] || styles.Low}`}>
      {children}
    </span>
  )
}

/* ── Findings renderer ─────────────────────────────────────────────────── */
function FindingsList({ findings }) {
  if (!findings || typeof findings !== 'object') return null
  const entries = Object.entries(findings).filter(
    ([key]) => !['error', 'score', 'confidence', 'flags'].includes(key)
  )
  if (entries.length === 0) return null

  return (
    <div className="mt-3 space-y-1.5 text-xs">
      {entries.map(([key, value]) => {
        // Skip complex nested objects for now — show only meaningful scalars & short arrays
        if (value === null || value === undefined) return null
        const label = key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
        let display
        if (typeof value === 'boolean') {
          display = value ? '✓ Yes' : '✕ No'
        } else if (typeof value === 'number') {
          display = String(Math.round(value * 100) / 100)
        } else if (typeof value === 'string') {
          display = value.length > 120 ? value.slice(0, 120) + '…' : value
        } else if (Array.isArray(value)) {
          if (value.length === 0) return null
          display = `${value.length} item${value.length !== 1 ? 's' : ''}`
        } else {
          return null // skip deep objects
        }

        return (
          <div key={key} className="flex items-start gap-2">
            <span className="font-medium text-slate-400 whitespace-nowrap min-w-[100px]">{label}:</span>
            <span className="text-slate-300">{display}</span>
          </div>
        )
      })}
    </div>
  )
}

/* ── Module card ───────────────────────────────────────────────────────── */
function ModuleCard({ moduleNumber, data }) {
  const meta = MODULE_META[moduleNumber] || { name: `Module ${moduleNumber}`, icon: '🔹', desc: '' }
  const { findings, flags, score, confidence } = data

  return (
    <div className="glass rounded-xl p-5 hover:ring-1 hover:ring-brand-500/20 transition-all duration-300 group">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{meta.icon}</span>
          <div>
            <h3 className="text-sm font-semibold text-slate-100 group-hover:text-brand-300 transition-colors">
              {meta.name}
            </h3>
            <p className="text-xs text-slate-500">{meta.desc}</p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {confidence != null && (
            <span className="text-xs text-slate-500">
              Conf: <span className="text-slate-300 font-medium">{Math.round(confidence * 100)}%</span>
            </span>
          )}
          {score != null && (
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-md ${
              score <= 30 ? 'bg-emerald-500/10 text-emerald-300'
                : score <= 60 ? 'bg-amber-500/10 text-amber-300'
                  : 'bg-red-500/10 text-red-300'
            }`}>
              {Math.round(score)}
            </span>
          )}
        </div>
      </div>

      {/* Flags */}
      {flags && flags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {flags.map((flag, i) => (
            <FlagBadge key={i} severity={flag.severity || 'Low'}>
              {flag.flag_id || flag.category || `Flag ${i + 1}`}: {flag.description?.slice(0, 60) || 'Flagged'}
              {flag.description?.length > 60 ? '…' : ''}
            </FlagBadge>
          ))}
        </div>
      )}

      {/* Findings */}
      <FindingsList findings={findings} />

      {/* Error state */}
      {data.findings?.error && (
        <div className="mt-3 rounded-lg bg-red-500/8 border border-red-500/15 px-3 py-2 text-xs text-red-300">
          ⚠ Module encountered an error: {typeof data.findings.error === 'string' ? data.findings.error.slice(0, 150) : 'Unknown error'}
        </div>
      )}
    </div>
  )
}

/* ── Loading skeleton ──────────────────────────────────────────────────── */
function Skeleton() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-16">
      <div className="flex flex-col items-center gap-6">
        <div className="h-48 w-48 rounded-full bg-surface-800 animate-shimmer" />
        <div className="h-6 w-48 rounded-lg bg-surface-800 animate-shimmer" />
        <div className="h-4 w-72 rounded-lg bg-surface-800 animate-shimmer" />
      </div>
      <div className="mt-12 grid gap-4">
        {[1,2,3].map(i => (
          <div key={i} className="h-32 rounded-xl bg-surface-800/60 animate-shimmer" style={{ animationDelay: `${i * 0.15}s` }} />
        ))}
      </div>
    </div>
  )
}

/* ── Main ReportPage ───────────────────────────────────────────────────── */
export default function ReportPage() {
  const { documentId } = useParams()
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false

    async function fetchReport() {
      try {
        const res = await fetch(`${API}/report/${documentId}`)
        if (!res.ok) {
          const body = await res.json().catch(() => ({}))
          throw new Error(body.detail || `Failed to load report (${res.status})`)
        }
        const data = await res.json()
        if (!cancelled) setReport(data)
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchReport()
    return () => { cancelled = true }
  }, [documentId])

  if (loading) return <Skeleton />

  if (error) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-24 text-center animate-fade-in">
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-red-500/10 ring-1 ring-red-500/20">
          <svg className="h-8 w-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-slate-100 mb-2">Report Not Found</h2>
        <p className="text-sm text-slate-400 mb-6">{error}</p>
        <Link to="/" className="inline-flex items-center gap-2 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-500 transition-colors">
          ← Analyze Another Document
        </Link>
      </div>
    )
  }

  const { document: doc, risk_report: risk, analysis_results: results } = report
  const overallScore = risk?.overall_score ?? 0
  const riskLevel = risk?.risk_level ?? 'Medium'
  const verdict = risk?.verdict ?? 'No verdict available'
  const summary = risk?.summary ?? ''
  const forgeryProb = risk?.forgery_probability ?? 0

  // Find the recommended action from the module 10 result
  const module10 = results?.find(r => r.module_number === 10)
  const recommendedAction = module10?.findings?.recommended_action || 'Review'

  // Find module 9 (risk) and module 8 (heatmap) results
  const module9 = results?.find(r => r.module_number === 9)
  const riskResult = module9?.findings || null
  const confidenceLevel = riskResult?.confidence_level || 'Medium'
  
  const module8 = results?.find(r => r.module_number === 8)
  const heatmapResult = module8?.findings || null

  return (
    <div className="mx-auto max-w-4xl px-6 py-10 sm:py-16">
      {/* ── Hero section ─────────────────────────────────────────────── */}
      <div className="animate-fade-in text-center mb-12">
        <p className="mb-1 text-xs font-semibold uppercase tracking-[0.2em] text-brand-400">
          Forensic Analysis Report
        </p>
        <p className="text-sm text-slate-500 truncate max-w-md mx-auto">
          {doc?.filename || documentId}
        </p>
      </div>

      {/* ── Score + Verdict hero ──────────────────────────────────────── */}
      <div className="glass rounded-2xl p-8 sm:p-10 mb-8 animate-fade-in-scale">
        <div className="flex flex-col sm:flex-row items-center gap-8 sm:gap-12">
          {/* Gauge */}
          <div className="shrink-0">
            <RiskScoreGauge score={overallScore} size={180} />
          </div>

          {/* Verdict info */}
          <div className="flex-1 text-center sm:text-left">
            <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2 mb-4">
              <RiskBadge level={riskLevel} />
              <ActionBadge action={recommendedAction} />
            </div>

            <h2 className="text-lg sm:text-xl font-bold text-slate-100 mb-3 leading-snug">
              {verdict}
            </h2>

            <div className="flex flex-wrap items-center justify-center sm:justify-start gap-x-6 gap-y-2 text-xs text-slate-500">
              <span>
                Forgery Probability:{' '}
                <span className={`font-semibold ${forgeryProb > 0.5 ? 'text-red-300' : forgeryProb > 0.25 ? 'text-amber-300' : 'text-emerald-300'}`}>
                  {(forgeryProb * 100).toFixed(1)}%
                </span>
              </span>
              <span>
                Modules Run:{' '}
                <span className="text-slate-300 font-medium">{results?.length || 0}</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Multi-axis analysis section ──────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8 animate-fade-in">
        {/* Left: Radar Chart */}
        <RiskRadarChart riskResult={riskResult} />

        {/* Right: Confidence explanation */}
        <div className="glass rounded-xl p-6">
          <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
            <svg className="h-4 w-4 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
            </svg>
            Analysis Confidence
          </h3>

          <div className="mb-4">
            <span className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold ring-1 ${
              confidenceLevel === 'High' ? 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30'
                : confidenceLevel === 'Low' ? 'bg-red-500/15 text-red-300 ring-red-500/30'
                  : 'bg-amber-500/15 text-amber-300 ring-amber-500/30'
            }`}>
              <span className={`h-2 w-2 rounded-full ${
                confidenceLevel === 'High' ? 'bg-emerald-400'
                  : confidenceLevel === 'Low' ? 'bg-red-400'
                    : 'bg-amber-400'
              }`} />
              {confidenceLevel} Confidence
            </span>
          </div>

          <div className="space-y-4 text-sm text-slate-400">
            <p className="leading-relaxed">
              The confidence level indicates how reliable this analysis is based on module agreement and data completeness.
            </p>

            <div className="space-y-2 text-xs">
              <div className="flex items-start gap-2">
                <span className="text-emerald-400 font-bold mt-0.5">High:</span>
                <span>5+ modules ran successfully and scores align within 20 points</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-amber-400 font-bold mt-0.5">Medium:</span>
                <span>3+ modules ran with moderate score agreement (within 40 points)</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-red-400 font-bold mt-0.5">Low:</span>
                <span>Fewer modules completed or significant score disagreement (&gt;40 points)</span>
              </div>
            </div>

            <div className="pt-3 border-t border-white/5">
              <p className="text-[11px] text-slate-500 italic">
                A {confidenceLevel.toLowerCase()} confidence score means the multi-axis risk assessment 
                {confidenceLevel === 'High' ? ' is highly reliable and consistent across all analysis dimensions.' 
                  : confidenceLevel === 'Low' ? ' should be interpreted cautiously due to limited or conflicting data.'
                    : ' is reasonably reliable but may benefit from additional verification.'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ── Tamper heatmap section ───────────────────────────────────── */}
      <div className="mb-8 animate-fade-in">
        <TamperHeatmapViewer heatmapResult={heatmapResult} />
      </div>

      {/* ── Module results grid ──────────────────────────────────────── */}
      <h3 className="text-sm font-semibold uppercase tracking-[0.15em] text-slate-500 mb-4 animate-fade-in">
        Module Analysis Details
      </h3>

      <div className="grid gap-4 stagger-children">
        {results?.map((result) => (
          <ModuleCard
            key={result.id || result.module_number}
            moduleNumber={result.module_number}
            data={result}
          />
        ))}
      </div>

      {/* ── Explainability summary ───────────────────────────────────── */}
      {summary && (
        <div className="mt-8 glass rounded-2xl p-6 animate-fade-in">
          <h3 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
            <svg className="h-4 w-4 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
            </svg>
            Explainability Summary
          </h3>
          <p className="text-sm text-slate-400 leading-relaxed">{summary}</p>
        </div>
      )}

      {/* ── Back button ──────────────────────────────────────────────── */}
      <div className="mt-10 text-center animate-fade-in">
        <Link
          to="/"
          className="inline-flex items-center gap-2 rounded-xl bg-surface-800 ring-1 ring-white/5 px-5 py-2.5 text-sm font-medium text-slate-300 hover:text-white hover:bg-surface-700 transition-colors"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
          </svg>
          Analyze Another Document
        </Link>
      </div>
    </div>
  )
}
