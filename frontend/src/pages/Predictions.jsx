import { useState, useEffect } from 'react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import Badge from '../components/Badge'
import ConfidenceBar from '../components/ConfidenceBar'
import Spinner from '../components/Spinner'

const CLASS_NAMES = [
  'letter','form','email','handwritten','advertisement',
  'scientific_report','scientific_publication','specification',
  'file_folder','news_article','budget','invoice',
  'presentation','questionnaire','resume','memo',
]

function fmt(iso) {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

function RelabelModal({ prediction, onClose, onSuccess }) {
  const [label,   setLabel]   = useState(prediction.label)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    if (label === prediction.label) { onClose(); return }
    setLoading(true)
    setError('')
    try {
      const updated = await api.relabel(prediction.id, label)
      onSuccess(updated)
    } catch (err) {
      setError(err.message || 'Failed to relabel')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-md rounded-2xl bg-white shadow-2xl border border-slate-200 p-6">
        <h2 className="text-base font-semibold text-slate-900 mb-1">Relabel Prediction</h2>
        <p className="text-sm text-slate-500 mb-5">
          Prediction <span className="font-mono text-slate-700">#{prediction.id}</span> · Current:&nbsp;
          <span className="font-medium text-slate-700 capitalize">{prediction.label.replace('_', ' ')}</span>
        </p>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-3.5 py-2.5 text-sm text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1.5">New label</label>
            <select
              value={label}
              onChange={e => setLabel(e.target.value)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            >
              {CLASS_NAMES.map(c => (
                <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>
              ))}
            </select>
          </div>
          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 px-4 py-2 text-sm font-semibold text-white transition"
            >
              {loading && <Spinner size="sm" />}
              Save label
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function Predictions() {
  const { user } = useAuth()
  const role = user?.role || 'reviewer'

  const [predictions, setPredictions] = useState([])
  const [loading,     setLoading]     = useState(true)
  const [error,       setError]       = useState('')
  const [minConf,     setMinConf]     = useState(0)
  const [relabelTarget, setRelabelTarget] = useState(null)
  const [toast,       setToast]       = useState('')

  useEffect(() => {
    api.getPredictions()
      .then(setPredictions)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  function showToast(msg) {
    setToast(msg)
    setTimeout(() => setToast(''), 3000)
  }

  function handleRelabelSuccess(updated) {
    setPredictions(prev => prev.map(p => p.id === updated.id ? updated : p))
    setRelabelTarget(null)
    showToast('Label updated successfully')
  }

  const filtered = predictions.filter(p => p.confidence >= minConf / 100)

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner size="lg" />
      </div>
    )
  }

  return (
    <div className="p-8 max-w-7xl mx-auto w-full">
      {/* Toast */}
      {toast && (
        <div className="fixed top-5 right-5 z-50 flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-3 text-sm font-medium text-white shadow-lg">
          <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
          </svg>
          {toast}
        </div>
      )}

      {relabelTarget && (
        <RelabelModal
          prediction={relabelTarget}
          onClose={() => setRelabelTarget(null)}
          onSuccess={handleRelabelSuccess}
        />
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Predictions</h1>
          <p className="text-slate-500 text-sm mt-1">
            {predictions.length} recent results from the classification pipeline
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-xs font-medium text-slate-600">Min confidence</label>
          <input
            type="range"
            min={0} max={100} step={5}
            value={minConf}
            onChange={e => setMinConf(+e.target.value)}
            className="w-28 accent-indigo-600"
          />
          <span className="text-sm font-semibold text-slate-700 w-10 text-right tabular-nums">{minConf}%</span>
        </div>
      </div>

      {error && (
        <div className="mb-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Table */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50">
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">ID</th>
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Label</th>
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider w-48">Confidence</th>
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Batch</th>
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Relabeled by</th>
              <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Date</th>
              {['admin', 'reviewer'].includes(role) && (
                <th className="px-5 py-3.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wider">Action</th>
              )}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {filtered.map(p => {
              const locked = role !== 'admin' && p.confidence >= 0.7
              return (
                <tr key={p.id} className="hover:bg-slate-50/70 transition-colors">
                  <td className="px-5 py-3.5 font-mono text-xs text-slate-400">#{p.id}</td>
                  <td className="px-5 py-3.5">
                    <span className="font-medium text-slate-800 capitalize">{p.label.replace(/_/g, ' ')}</span>
                  </td>
                  <td className="px-5 py-3.5 w-48">
                    <ConfidenceBar value={p.confidence} />
                  </td>
                  <td className="px-5 py-3.5 text-slate-500">#{p.batch_id}</td>
                  <td className="px-5 py-3.5">
                    {p.relabeled_by
                      ? <span className="text-xs text-slate-500 truncate max-w-[120px] block">{p.relabeled_by}</span>
                      : <span className="text-slate-300">—</span>}
                  </td>
                  <td className="px-5 py-3.5 text-slate-400 text-xs whitespace-nowrap">{fmt(p.created_at)}</td>
                  {['admin', 'reviewer'].includes(role) && (
                    <td className="px-5 py-3.5 text-right">
                      <button
                        onClick={() => !locked && setRelabelTarget(p)}
                        disabled={locked}
                        title={locked ? 'Confidence ≥ 70% — reviewer relabeling not allowed' : 'Relabel this prediction'}
                        className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                          locked
                            ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                            : 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100'
                        }`}
                      >
                        {locked ? '🔒 Locked' : 'Relabel'}
                      </button>
                    </td>
                  )}
                </tr>
              )
            })}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={7} className="px-5 py-12 text-center text-sm text-slate-400">
                  No predictions match the current filter
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
