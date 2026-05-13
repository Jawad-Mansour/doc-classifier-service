import { useState } from 'react'
import { api } from '../api/client'
import Badge from '../components/Badge'
import Spinner from '../components/Spinner'

const ROLES = ['admin', 'reviewer', 'auditor']

export default function Users() {
  const [userId,  setUserId]  = useState('')
  const [role,    setRole]    = useState('reviewer')
  const [loading, setLoading] = useState(false)
  const [result,  setResult]  = useState(null)
  const [error,   setError]   = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setResult(null)
    setLoading(true)
    try {
      const updated = await api.changeRole(Number(userId), role)
      setResult(updated)
      setUserId('')
    } catch (err) {
      setError(err.message || 'Failed to update role')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-8 max-w-2xl mx-auto w-full">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">User Management</h1>
        <p className="text-slate-500 text-sm mt-1">Change user roles — admin only</p>
      </div>

      {/* Change role card */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm p-6 mb-6">
        <h2 className="text-base font-semibold text-slate-900 mb-1">Change User Role</h2>
        <p className="text-sm text-slate-500 mb-5">
          Enter a user ID and select the new role. Role changes take effect on the user's next request.
        </p>

        {error && (
          <div className="mb-4 flex items-start gap-2.5 rounded-lg bg-red-50 border border-red-200 px-3.5 py-3 text-sm text-red-700">
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 shrink-0 mt-0.5">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
            </svg>
            {error}
          </div>
        )}

        {result && (
          <div className="mb-4 flex items-start gap-2.5 rounded-lg bg-emerald-50 border border-emerald-200 px-3.5 py-3 text-sm text-emerald-700">
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 shrink-0 mt-0.5">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
            </svg>
            <span>
              Role updated for <strong>{result.email}</strong> → <Badge label={result.role} />
            </span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1.5">User ID</label>
              <input
                type="number"
                min={1}
                required
                value={userId}
                onChange={e => setUserId(e.target.value)}
                placeholder="e.g. 3"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1.5">New role</label>
              <select
                value={role}
                onChange={e => setRole(e.target.value)}
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              >
                {ROLES.map(r => (
                  <option key={r} value={r}>{r.charAt(0).toUpperCase() + r.slice(1)}</option>
                ))}
              </select>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="flex items-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 px-5 py-2.5 text-sm font-semibold text-white transition shadow-sm"
          >
            {loading && <Spinner size="sm" />}
            {loading ? 'Updating…' : 'Update role'}
          </button>
        </form>
      </div>

      {/* Role reference */}
      <div className="rounded-xl bg-white border border-slate-200 shadow-sm p-6">
        <h2 className="text-sm font-semibold text-slate-900 mb-4">Role permissions reference</h2>
        <div className="space-y-3">
          {[
            {
              role: 'admin',
              perms: ['Manage all users & roles', 'Read batches & predictions', 'Relabel predictions', 'View audit log'],
            },
            {
              role: 'reviewer',
              perms: ['Read batches & predictions', 'Relabel low-confidence predictions (< 70%)'],
            },
            {
              role: 'auditor',
              perms: ['Read batches', 'View audit log (read-only)'],
            },
          ].map(({ role: r, perms }) => (
            <div key={r} className="flex gap-4 p-3.5 rounded-lg bg-slate-50 border border-slate-100">
              <div className="shrink-0 pt-0.5"><Badge label={r} /></div>
              <ul className="text-sm text-slate-600 space-y-0.5">
                {perms.map(p => (
                  <li key={p} className="flex items-center gap-1.5">
                    <span className="text-slate-300">·</span> {p}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
