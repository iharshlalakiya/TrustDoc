import { useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

const API = '/api'
const ACCEPTED = '.pptx,.pdf,.docx'
const MAX_SIZE_MB = 20

const STAGES = [
  { key: 'idle', label: '' },
  { key: 'uploading', label: 'Uploading document…' },
  { key: 'analyzing', label: 'Running forensic analysis…' },
  { key: 'generating', label: 'Generating verdict report…' },
]

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function fileIcon(name) {
  const ext = name?.split('.').pop()?.toLowerCase()
  const colors = { pdf: 'text-red-400', pptx: 'text-orange-400', docx: 'text-blue-400' }
  return colors[ext] || 'text-slate-400'
}

export default function UploadPage() {
  const navigate = useNavigate()
  const inputRef = useRef(null)

  const [file, setFile] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [stage, setStage] = useState('idle')
  const [error, setError] = useState(null)

  const stageIdx = STAGES.findIndex(s => s.key === stage)
  const stageLabel = STAGES[stageIdx]?.label || ''

  // ── Drag & drop handlers ──
  const onDragOver = useCallback((e) => { e.preventDefault(); setDragOver(true) }, [])
  const onDragLeave = useCallback(() => setDragOver(false), [])
  const onDrop = useCallback((e) => {
    e.preventDefault()
    setDragOver(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) { setFile(dropped); setError(null) }
  }, [])

  const onFileSelect = (e) => {
    const selected = e.target.files[0]
    if (selected) { setFile(selected); setError(null) }
  }

  // ── Upload + Analyze pipeline ──
  const handleSubmit = async () => {
    if (!file) return
    setError(null)

    try {
      // 1. Upload
      setStage('uploading')
      const formData = new FormData()
      formData.append('file', file)

      const uploadRes = await fetch(`${API}/upload`, {
        method: 'POST',
        body: formData,
      })
      if (!uploadRes.ok) {
        const body = await uploadRes.json().catch(() => ({}))
        throw new Error(body.detail || `Upload failed (${uploadRes.status})`)
      }
      const { document_id } = await uploadRes.json()

      // 2. Analyze
      setStage('analyzing')
      const analyzeRes = await fetch(`${API}/analyze/${document_id}`, {
        method: 'POST',
      })

      // 3. Report generation (happens inside analyze, but we show a stage)
      setStage('generating')

      if (!analyzeRes.ok) {
        const body = await analyzeRes.json().catch(() => ({}))
        throw new Error(body.detail || `Analysis failed (${analyzeRes.status})`)
      }

      // 4. Navigate to report
      navigate(`/report/${document_id}`)
    } catch (err) {
      setError(err.message || 'Something went wrong')
      setStage('idle')
    }
  }

  const isProcessing = stage !== 'idle'

  return (
    <div className="mx-auto max-w-2xl px-6 py-16 sm:py-24">
      {/* Header */}
      <div className="text-center mb-12 animate-fade-in">
        <p className="mb-3 text-sm font-semibold uppercase tracking-[0.2em] text-brand-400">
          Document Forensics
        </p>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
          Analyze Your Document
        </h1>
        <p className="mt-4 text-base text-slate-400 max-w-md mx-auto leading-relaxed">
          Upload a <span className="text-slate-300 font-medium">.pptx</span>,{' '}
          <span className="text-slate-300 font-medium">.pdf</span>, or{' '}
          <span className="text-slate-300 font-medium">.docx</span> file to scan for
          authenticity, metadata anomalies, and AI-generated content.
        </p>
      </div>

      {/* Upload zone */}
      <div
        className={`
          animate-fade-in-scale relative rounded-2xl border-2 border-dashed
          transition-all duration-300 cursor-pointer
          ${dragOver
            ? 'border-brand-400 bg-brand-500/8 shadow-lg shadow-brand-500/10'
            : file
              ? 'border-brand-500/30 bg-surface-900/80'
              : 'border-slate-700/60 bg-surface-900/50 hover:border-brand-500/40 hover:bg-surface-900/70'
          }
        `}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => !isProcessing && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          onChange={onFileSelect}
          className="hidden"
          disabled={isProcessing}
        />

        <div className="flex flex-col items-center justify-center px-8 py-14 sm:py-16">
          {!file ? (
            <>
              {/* Upload icon */}
              <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-500/10 ring-1 ring-brand-500/20">
                <svg className="h-8 w-8 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
                </svg>
              </div>
              <p className="text-base font-medium text-slate-200 mb-1">
                Drop your document here
              </p>
              <p className="text-sm text-slate-500">
                or <span className="text-brand-400 font-medium hover:underline">browse</span> to select a file
              </p>
              <p className="mt-3 text-xs text-slate-600">
                PPTX, PDF, or DOCX • Max {MAX_SIZE_MB}MB
              </p>
            </>
          ) : (
            <>
              {/* File preview */}
              <div className="flex items-center gap-4 w-full max-w-sm">
                <div className={`flex h-14 w-14 items-center justify-center rounded-xl bg-surface-800 ring-1 ring-white/5 ${fileIcon(file.name)}`}>
                  <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-100 truncate">{file.name}</p>
                  <p className="text-xs text-slate-500 mt-0.5">{formatSize(file.size)}</p>
                </div>
                {!isProcessing && (
                  <button
                    onClick={(e) => { e.stopPropagation(); setFile(null) }}
                    className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-500 hover:text-slate-300 hover:bg-surface-800 transition-colors"
                    aria-label="Remove file"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="mt-4 animate-fade-in rounded-xl bg-red-500/10 border border-red-500/20 px-4 py-3 text-sm text-red-300 flex items-start gap-3">
          <svg className="h-5 w-5 text-red-400 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
          </svg>
          <span>{error}</span>
        </div>
      )}

      {/* Processing spinner */}
      {isProcessing && (
        <div className="mt-8 animate-fade-in">
          {/* Progress steps */}
          <div className="flex items-center justify-center gap-2 mb-5">
            {STAGES.slice(1).map((s, i) => {
              const isActive = stageIdx === i + 1
              const isDone = stageIdx > i + 1
              return (
                <div key={s.key} className="flex items-center gap-2">
                  <div
                    className={`h-2.5 w-2.5 rounded-full transition-all duration-500 ${
                      isDone
                        ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50'
                        : isActive
                          ? 'bg-brand-400 shadow-sm shadow-brand-400/50 animate-pulse'
                          : 'bg-slate-700'
                    }`}
                  />
                  {i < STAGES.length - 2 && (
                    <div className={`h-0.5 w-8 rounded-full transition-colors duration-500 ${isDone ? 'bg-emerald-400/40' : 'bg-slate-800'}`} />
                  )}
                </div>
              )
            })}
          </div>

          <div className="flex items-center justify-center gap-3">
            <div className="relative h-5 w-5">
              <div className="absolute inset-0 rounded-full border-2 border-brand-500/20" />
              <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-brand-400 animate-spin" />
            </div>
            <p className="text-sm font-medium text-slate-300">{stageLabel}</p>
          </div>
        </div>
      )}

      {/* Analyze button */}
      {file && !isProcessing && (
        <button
          onClick={handleSubmit}
          className="
            mt-6 w-full rounded-xl bg-gradient-to-r from-brand-600 to-purple-600
            px-6 py-3.5 text-sm font-semibold text-white
            shadow-lg shadow-brand-500/25
            hover:shadow-xl hover:shadow-brand-500/30 hover:brightness-110
            active:scale-[0.98]
            transition-all duration-200
            animate-fade-in
          "
        >
          Analyze Document
        </button>
      )}

      {/* Footer hint */}
      {!isProcessing && (
        <p className="mt-8 text-center text-xs text-slate-600 animate-fade-in">
          Your document is processed securely and deleted after analysis.
        </p>
      )}
    </div>
  )
}
