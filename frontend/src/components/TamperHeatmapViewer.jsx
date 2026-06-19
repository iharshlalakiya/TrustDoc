import { useState } from 'react'

export default function TamperHeatmapViewer({ heatmapResult }) {
  const [currentPage, setCurrentPage] = useState(0)
  const [hoveredBox, setHoveredBox] = useState(null)

  if (!heatmapResult || !heatmapResult.pages || heatmapResult.pages.length === 0) {
    return (
      <div className="glass rounded-xl p-8 text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-slate-700/50">
          <svg className="h-6 w-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 001.5-1.5V6a1.5 1.5 0 00-1.5-1.5H3.75A1.5 1.5 0 002.25 6v12a1.5 1.5 0 001.5 1.5zm10.5-11.25h.008v.008h-.008V8.25zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
          </svg>
        </div>
        <p className="text-sm text-slate-400">No heatmap data available</p>
      </div>
    )
  }

  const pages = heatmapResult.pages
  const page = pages[currentPage]
  const hasMultiplePages = pages.length > 1

  const intensityStyles = {
    high: 'border-red-500 bg-red-500/10',
    medium: 'border-orange-500 bg-orange-500/10',
    low: 'border-yellow-500 bg-yellow-500/10'
  }

  return (
    <div className="glass rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
          <svg className="h-4 w-4 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
          </svg>
          Tamper Detection Heatmap
        </h3>
        
        {hasMultiplePages && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage(p => Math.max(0, p - 1))}
              disabled={currentPage === 0}
              className="p-1.5 rounded-lg bg-surface-800 hover:bg-surface-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <svg className="h-4 w-4 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
            </button>
            <span className="text-xs text-slate-400 min-w-[80px] text-center">
              Page {currentPage + 1} of {pages.length}
            </span>
            <button
              onClick={() => setCurrentPage(p => Math.min(pages.length - 1, p + 1))}
              disabled={currentPage === pages.length - 1}
              className="p-1.5 rounded-lg bg-surface-800 hover:bg-surface-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <svg className="h-4 w-4 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        )}
      </div>

      <div className="relative">
        {page.image_url ? (
          <div className="relative inline-block max-w-full">
            <img
              src={page.image_url}
              alt={`Page ${page.page_number}`}
              className="max-w-full h-auto rounded-lg border border-white/5"
              onLoad={(e) => {
                // Store dimensions for scaling
                e.target.dataset.naturalWidth = e.target.naturalWidth
                e.target.dataset.naturalHeight = e.target.naturalHeight
              }}
            />
            
            {/* Overlay boxes */}
            {page.boxes && page.boxes.length > 0 && page.boxes.map((box, idx) => {
              const intensity = box.intensity || 'low'
              
              return (
                <div
                  key={idx}
                  className={`absolute border-2 ${intensityStyles[intensity]} cursor-help transition-opacity hover:opacity-80`}
                  style={{
                    left: `${box.x}px`,
                    top: `${box.y}px`,
                    width: `${box.width}px`,
                    height: `${box.height}px`,
                    opacity: intensity === 'high' ? 0.4 : intensity === 'medium' ? 0.3 : 0.2
                  }}
                  onMouseEnter={() => setHoveredBox({ ...box, idx })}
                  onMouseLeave={() => setHoveredBox(null)}
                />
              )
            })}

            {/* Tooltip */}
            {hoveredBox && (
              <div className="absolute z-50 max-w-xs px-3 py-2 text-xs text-white bg-slate-900 rounded-lg shadow-xl border border-white/10"
                   style={{
                     left: `${hoveredBox.x + hoveredBox.width / 2}px`,
                     top: `${hoveredBox.y - 10}px`,
                     transform: 'translate(-50%, -100%)'
                   }}>
                <div className="font-semibold text-brand-300 mb-1">
                  {hoveredBox.intensity.toUpperCase()} Risk
                </div>
                <div className="text-slate-300 mb-1">{hoveredBox.reason}</div>
                <div className="text-slate-500 text-[10px]">
                  Source: {hoveredBox.source_module}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="aspect-[4/3] bg-surface-800/50 rounded-lg flex items-center justify-center">
            <p className="text-sm text-slate-500">Image not available</p>
          </div>
        )}

        {/* Legend */}
        {page.boxes && page.boxes.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-4 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded border-2 border-red-500 bg-red-500/10" />
              <span className="text-slate-400">High Risk</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded border-2 border-orange-500 bg-orange-500/10" />
              <span className="text-slate-400">Medium Risk</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded border-2 border-yellow-500 bg-yellow-500/10" />
              <span className="text-slate-400">Low Risk</span>
            </div>
          </div>
        )}

        {page.boxes && page.boxes.length === 0 && (
          <div className="mt-4 text-center py-6 bg-emerald-500/5 rounded-lg border border-emerald-500/10">
            <svg className="h-8 w-8 text-emerald-400 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-sm text-emerald-300 font-medium">No anomalies detected on this page</p>
          </div>
        )}
      </div>
    </div>
  )
}
