import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer } from 'recharts'

export default function RiskRadarChart({ riskResult }) {
  if (!riskResult || !riskResult.axes) {
    return (
      <div className="glass rounded-xl p-8 text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-slate-700/50">
          <svg className="h-6 w-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
          </svg>
        </div>
        <p className="text-sm text-slate-400">No risk data available</p>
      </div>
    )
  }

  const axes = riskResult.axes
  const riskLevel = riskResult.risk_level || 'Medium'

  // Transform axes data for Recharts
  const chartData = [
    {
      axis: 'Metadata\nIntegrity',
      value: axes.metadata_integrity?.score || 0,
      fullName: 'Metadata Integrity',
      factors: axes.metadata_integrity?.contributing_factors || []
    },
    {
      axis: 'Content\nConsistency',
      value: axes.content_consistency?.score || 0,
      fullName: 'Content Consistency',
      factors: axes.content_consistency?.contributing_factors || []
    },
    {
      axis: 'Visual\nAuthenticity',
      value: axes.visual_authenticity?.score || 0,
      fullName: 'Visual Authenticity',
      factors: axes.visual_authenticity?.contributing_factors || []
    },
    {
      axis: 'Compliance\nRisk',
      value: axes.compliance_risk?.score || 0,
      fullName: 'Compliance Risk',
      factors: axes.compliance_risk?.contributing_factors || []
    }
  ]

  // Color based on risk level
  const radarColor = riskLevel === 'High' ? '#ef4444' : riskLevel === 'Medium' ? '#f59e0b' : '#10b981'
  const radarFill = riskLevel === 'High' ? '#ef444420' : riskLevel === 'Medium' ? '#f59e0b20' : '#10b98120'

  return (
    <div className="glass rounded-xl p-6">
      <h3 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
        <svg className="h-4 w-4 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5M9 11.25v1.5M12 9v3.75m3-6v6" />
        </svg>
        Multi-Axis Risk Assessment
      </h3>

      <div className="mb-6">
        <ResponsiveContainer width="100%" height={280}>
          <RadarChart data={chartData}>
            <PolarGrid stroke="#475569" strokeOpacity={0.3} />
            <PolarAngleAxis 
              dataKey="axis" 
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              tickLine={false}
            />
            <PolarRadiusAxis 
              angle={90} 
              domain={[0, 100]}
              tick={{ fill: '#64748b', fontSize: 10 }}
              axisLine={false}
            />
            <Radar
              name="Risk Score"
              dataKey="value"
              stroke={radarColor}
              fill={radarFill}
              fillOpacity={0.6}
              strokeWidth={2}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* Contributing factors for each axis */}
      <div className="space-y-4">
        {chartData.map((item, idx) => (
          <div key={idx} className="border-l-2 border-slate-700 pl-3">
            <div className="flex items-center justify-between mb-1">
              <h4 className="text-xs font-semibold text-slate-300">{item.fullName}</h4>
              <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                item.value <= 30 ? 'bg-emerald-500/10 text-emerald-300'
                  : item.value <= 60 ? 'bg-amber-500/10 text-amber-300'
                    : 'bg-red-500/10 text-red-300'
              }`}>
                {item.value}
              </span>
            </div>
            {item.factors && item.factors.length > 0 && (
              <ul className="space-y-1 mt-1.5">
                {item.factors.slice(0, 3).map((factor, i) => (
                  <li key={i} className="text-[11px] text-slate-500 flex items-start gap-1.5">
                    <span className="text-brand-400 mt-0.5">•</span>
                    <span className="flex-1">{factor}</span>
                  </li>
                ))}
                {item.factors.length > 3 && (
                  <li className="text-[10px] text-slate-600 italic">
                    +{item.factors.length - 3} more factor{item.factors.length - 3 !== 1 ? 's' : ''}
                  </li>
                )}
              </ul>
            )}
            {(!item.factors || item.factors.length === 0) && (
              <p className="text-[11px] text-slate-600 italic">No issues detected</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
