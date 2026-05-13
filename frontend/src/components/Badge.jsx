const MAP = {
  admin:      'bg-violet-100 text-violet-700 ring-violet-200',
  reviewer:   'bg-blue-100   text-blue-700   ring-blue-200',
  auditor:    'bg-emerald-100 text-emerald-700 ring-emerald-200',
  pending:    'bg-slate-100  text-slate-600   ring-slate-200',
  processing: 'bg-sky-100    text-sky-700     ring-sky-200',
  done:       'bg-emerald-100 text-emerald-700 ring-emerald-200',
  failed:     'bg-red-100    text-red-700     ring-red-200',
}

export default function Badge({ label, variant }) {
  const key = (variant || label || '').toLowerCase()
  const cls = MAP[key] || 'bg-slate-100 text-slate-600 ring-slate-200'
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${cls}`}>
      {label}
    </span>
  )
}
