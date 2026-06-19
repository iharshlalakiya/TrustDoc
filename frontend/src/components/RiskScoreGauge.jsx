/**
 * RiskScoreGauge — SVG arc gauge displaying a 0-100 risk score.
 *
 * Props:
 *   score  (number)  0–100
 *   size   (number)  diameter in px  (default 200)
 *   label  (string)  e.g. "Risk Score"
 */
export default function RiskScoreGauge({ score = 0, size = 200, label = 'Risk Score' }) {
  const clamped = Math.max(0, Math.min(100, score))
  const radius = 45
  const circumference = 2 * Math.PI * radius
  // We use 75% of the circle (270°) for the arc
  const arcLength = circumference * 0.75
  const filled = (clamped / 100) * arcLength
  const offset = arcLength - filled

  // Color stops: green → amber → red
  let strokeColor, glowColor, bgRing
  if (clamped <= 30) {
    strokeColor = '#22c55e'
    glowColor = 'rgba(34, 197, 94, 0.3)'
    bgRing = 'rgba(34, 197, 94, 0.08)'
  } else if (clamped <= 60) {
    strokeColor = '#f59e0b'
    glowColor = 'rgba(245, 158, 11, 0.3)'
    bgRing = 'rgba(245, 158, 11, 0.08)'
  } else {
    strokeColor = '#ef4444'
    glowColor = 'rgba(239, 68, 68, 0.3)'
    bgRing = 'rgba(239, 68, 68, 0.08)'
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          viewBox="0 0 100 100"
          className="w-full h-full -rotate-[135deg]"
          style={{ filter: `drop-shadow(0 0 12px ${glowColor})` }}
        >
          {/* Background arc */}
          <circle
            cx="50" cy="50" r={radius}
            fill="none"
            stroke={bgRing}
            strokeWidth="8"
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeLinecap="round"
          />
          {/* Filled arc */}
          <circle
            cx="50" cy="50" r={radius}
            fill="none"
            stroke={strokeColor}
            strokeWidth="8"
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="animate-gauge-fill transition-all duration-1000"
            style={{ '--gauge-offset': offset }}
          />
        </svg>
        {/* Center label */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="text-5xl font-extrabold tabular-nums"
            style={{ color: strokeColor }}
          >
            {Math.round(clamped)}
          </span>
          <span className="text-xs font-medium text-slate-400 mt-0.5">/ 100</span>
        </div>
      </div>
      <span className="text-sm font-medium text-slate-400 tracking-wide">{label}</span>
    </div>
  )
}
