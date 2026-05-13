import { useState, useEffect } from 'react'
import { api } from '../api/client'
import Spinner from '../components/Spinner'

const ACTION_STYLES = {
  prediction_created: { dot: 'bg-emerald-500', label: 'bg-emerald-50 text-emerald-700 ring-emerald-200' },
  relabel:            { dot: 'bg-amber-500',   label: 'bg-amber-50   text-amber-700   ring-amber-200'   },
  role_change:        { dot: 'bg-violet-500',  label: 'bg-violet-50  text-violet-700  ring-violet-200'  },
  status_change:      { dot: 'bg-sky-500',     label: 'bg-sky-50     text-sky-700     ring-sky-200'     },
}

function ActionBadge({ action }) {
  const style = ACTION_STYLES[action] || { dot: 'bg-slate-400', label: 'bg-slate-50 text-slate-600 ring-slate-200' }
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${style.label}`}>
      <span className={`inline-block h-1.5 w-1.5 rounded-full ${style.dot}`} />
      {action.replace(/_/g, ' ')}
    </span>
  )
}

function fmt(iso) {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

export default function AuditLog() {
  const [logs,    setLogs]    = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState('')
  const [search,  setSearch]  = useState('')

  useEffect(() => {
    api.getAuditLog()
      .then(setLogs)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const filtered = logs.filter(l =>
    !search ||
    l.actor.toLowerCase().includes(search.toLowerCase()) ||
    l.action.toLowerCase().includes(search.toLowerCase()) ||
    l.target.toLowerCase().includes(search.toLowerCase())
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner size="lg" />
      </div>
    )
  }

  return (
    <div className="p-8 max-w-4xl mx-auto w-full">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Audit Log</h1>
          <p className="text-slate-500 text-sm mt-1">Immutable record of all system events</p>
        </div>
        <div className="relative">
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search events…"
            className="rounded-lg border border-slate-300 bg-white pl-9 pr-3.5 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <svg viewBox="0 0 20 20" fill="currentColor" className="absolute left-2.5 top-2.5 w-4 h-4 text-slate-400">
            <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd"/>
          </svg>
        </div>
      </div>

      {error && (
        <div className="mb-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      {/* Timeline */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-100 bg-slate-50">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            {filtered.length} events
          </span>
        </div>
        <div className="divide-y divide-slate-50">
          {filtered.map((log, i) => (
            <div key={log.id} className="flex items-start gap-4 px-5 py-4 hover:bg-slate-50/70 transition-colors">
              {/* Timeline indicator */}
              <div className="flex flex-col items-center shrink-0 pt-1">
                <div className={`h-2 w-2 rounded-full ${ACTION_STYLES[log.action]?.dot || 'bg-slate-300'}`} />
                {i < filtered.length - 1 && (
                  <div className="w-px flex-1 bg-slate-100 mt-1 min-h-[1.5rem]" />
                )}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <ActionBadge action={log.action} />
                  <span className="text-xs text-slate-500">by</span>
                  <span className="text-xs font-semibold text-slate-700 truncate">{log.actor}</span>
                </div>
                <p className="text-sm text-slate-800">
                  Target: <span className="font-mono text-xs text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded">{log.target}</span>
                </p>
                <p className="text-xs text-slate-400 mt-1">{fmt(log.timestamp)}</p>
              </div>

              <span className="text-xs text-slate-300 font-mono shrink-0">#{log.id}</span>
            </div>
          ))}
          {filtered.length === 0 && (
            <p className="px-5 py-12 text-center text-sm text-slate-400">
              {search ? 'No events match your search' : 'No audit events yet'}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
