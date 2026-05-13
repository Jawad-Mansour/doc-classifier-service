import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import Badge from '../components/Badge'
import ConfidenceBar from '../components/ConfidenceBar'
import Spinner from '../components/Spinner'

function StatCard({ label, value, sub, color = 'indigo' }) {
  const colors = {
    indigo:  'from-indigo-500  to-indigo-600',
    emerald: 'from-emerald-500 to-emerald-600',
    amber:   'from-amber-400   to-amber-500',
    violet:  'from-violet-500  to-violet-600',
  }
  return (
    <div className="rounded-xl bg-white border border-slate-200 shadow-sm p-5">
      <div className={`inline-flex rounded-lg bg-gradient-to-br ${colors[color]} p-2.5 mb-3`}>
        <div className="w-4 h-4 bg-white/40 rounded" />
      </div>
      <p className="text-2xl font-bold text-slate-900 tabular-nums">{value}</p>
      <p className="text-sm font-medium text-slate-700 mt-0.5">{label}</p>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
    </div>
  )
}

function fmt(iso) {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

export default function Dashboard() {
  const { user } = useAuth()
  const navigate  = useNavigate()

  const [predictions, setPredictions] = useState([])
  const [batches,     setBatches]     = useState([])
  const [loading,     setLoading]     = useState(true)
  const [error,       setError]       = useState('')

  const role = user?.role || 'auditor'
  const canSeePredictions = ['admin', 'reviewer'].includes(role)

  useEffect(() => {
    const tasks = [api.getBatches().then(setBatches)]
    if (canSeePredictions) tasks.push(api.getPredictions().then(setPredictions))
    Promise.all(tasks)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [canSeePredictions])

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center h-full">
        <Spinner size="lg" />
      </div>
    )
  }

  const highConf   = predictions.filter(p => p.confidence >= 0.9).length
  const relabeled  = predictions.filter(p => p.relabeled_by).length
  const doneCount  = batches.filter(b => b.status === 'done').length

  return (
    <div className="p-8 max-w-7xl mx-auto w-full">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
        <p className="text-slate-500 mt-1 text-sm">Overview of the classification pipeline</p>
      </div>

      {error && (
        <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Batches"      value={batches.length}      color="indigo" />
        <StatCard label="Completed Batches"  value={doneCount}           color="emerald" />
        {canSeePredictions && (
          <>
            <StatCard label="Recent Predictions" value={predictions.length} color="violet" />
            <StatCard label="High Confidence"    value={highConf}           sub="≥ 90%" color="amber" />
          </>
        )}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Recent predictions */}
        {canSeePredictions && (
          <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
            <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
              <h2 className="font-semibold text-slate-900 text-sm">Recent Predictions</h2>
              <button
                onClick={() => navigate('/predictions')}
                className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
              >
                View all →
              </button>
            </div>
            <div className="divide-y divide-slate-50">
              {predictions.slice(0, 6).map(p => (
                <div key={p.id} className="px-5 py-3.5 flex items-center gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-sm font-medium text-slate-800 capitalize">{p.label.replace('_', ' ')}</span>
                      {p.relabeled_by && (
                        <span className="text-xs text-slate-400 italic">relabeled</span>
                      )}
                    </div>
                    <ConfidenceBar value={p.confidence} />
                  </div>
                  <span className="text-xs text-slate-400 shrink-0">{fmt(p.created_at)}</span>
                </div>
              ))}
              {predictions.length === 0 && (
                <p className="px-5 py-8 text-sm text-slate-400 text-center">No predictions yet</p>
              )}
            </div>
          </div>
        )}

        {/* Recent batches */}
        <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
            <h2 className="font-semibold text-slate-900 text-sm">Recent Batches</h2>
            <button
              onClick={() => navigate('/batches')}
              className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
            >
              View all →
            </button>
          </div>
          <div className="divide-y divide-slate-50">
            {batches.slice(0, 8).map(b => (
              <div key={b.id} className="px-5 py-3.5 flex items-center gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800">Batch #{b.id}</p>
                  <p className="text-xs text-slate-400 font-mono truncate mt-0.5">{b.request_id}</p>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <Badge label={b.status} />
                  <span className="text-xs text-slate-400">{fmt(b.created_at)}</span>
                </div>
              </div>
            ))}
            {batches.length === 0 && (
              <p className="px-5 py-8 text-sm text-slate-400 text-center">No batches yet</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
