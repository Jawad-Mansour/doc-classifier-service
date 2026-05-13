function barColor(v) {
  if (v >= 0.9) return 'bg-emerald-500'
  if (v >= 0.7) return 'bg-amber-400'
  if (v >= 0.5) return 'bg-orange-400'
  return 'bg-red-400'
}

function textColor(v) {
  if (v >= 0.9) return 'text-emerald-700'
  if (v >= 0.7) return 'text-amber-700'
  if (v >= 0.5) return 'text-orange-700'
  return 'text-red-700'
}

export default function ConfidenceBar({ value }) {
  const pct = Math.round(value * 100)
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${barColor(value)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`text-xs font-semibold tabular-nums w-9 text-right ${textColor(value)}`}>
        {pct}%
      </span>
    </div>
  )
}
