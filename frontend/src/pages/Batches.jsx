import { useState, useEffect } from 'react'
import { api } from '../api/client'
import Badge from '../components/Badge'
import Spinner from '../components/Spinner'

function fmt(iso) {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

const STATUS_ORDER = { processing: 0, pending: 1, done: 2, failed: 3 }

export default function Batches() {
  const [batches,  setBatches]  = useState([])
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState('')
  const [sort,     setSort]     = useState('newest')

  useEffect(() => {
    api.getBatches()
      .then(setBatches)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const sorted = [...batches].sort((a, b) => {
    if (sort === 'newest') return new Date(b.created_at) - new Date(a.created_at)
    if (sort === 'oldest') return new Date(a.created_at) - new Date(b.created_at)
    if (sort === 'status') return (STATUS_ORDER[a.status] ?? 9) - (STATUS_ORDER[b.status] ?? 9)
    return 0
  })

  const counts = batches.reduce((acc, b) => {
    acc[b.status] = (acc[b.status] || 0) + 1
    return acc
  }, {})

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner size="lg" />
      </div>
    )
  }

  return (
    <div className="p-8 max-w-5xl mx-auto w-full">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Batches</h1>
        <p className="text-slate-500 text-sm mt-1">All document ingestion batches from the SFTP pipeline</p>
      </div>

      {error && (
        <div className="mb-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      {/* Summary chips */}
      <div className="flex flex-wrap gap-2 mb-6">
        {[['done', 'Completed'], ['processing', 'Processing'], ['pending', 'Pending'], ['failed', 'Failed']].map(([s, label]) => (
          <div key={s} className="flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5">
            <Badge label={s} />
            <span className="text-xs font-semibold text-slate-700 tabular-nums">{counts[s] || 0}</span>
            <span className="text-xs text-slate-400">{label}</span>
          </div>
        ))}
      </div>

      {/* Sort + Table */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-100 bg-slate-50">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            {batches.length} batches
          </span>
          <select
            value={sort}
            onChange={e => setSort(e.target.value)}
            className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-600 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
            <option value="status">By status</option>
          </select>
        </div>

        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100">
              <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Batch</th>
              <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Request ID</th>
              <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
              <th className="px-5 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Created</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {sorted.map(b => (
              <tr key={b.id} className="hover:bg-slate-50/70 transition-colors">
                <td className="px-5 py-3.5">
                  <span className="font-semibold text-slate-800">#{b.id}</span>
                </td>
                <td className="px-5 py-3.5">
                  <span className="font-mono text-xs text-slate-500 truncate block max-w-[280px]">{b.request_id}</span>
                </td>
                <td className="px-5 py-3.5">
                  <Badge label={b.status} />
                </td>
                <td className="px-5 py-3.5 text-xs text-slate-400 whitespace-nowrap">{fmt(b.created_at)}</td>
              </tr>
            ))}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={4} className="px-5 py-12 text-center text-sm text-slate-400">
                  No batches found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
