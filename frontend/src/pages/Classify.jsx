import { useState, useRef } from 'react'
import { api } from '../api/client'
import ConfidenceBar from '../components/ConfidenceBar'
import Spinner from '../components/Spinner'

export default function Classify() {
  const [dragging,  setDragging]  = useState(false)
  const [file,      setFile]      = useState(null)
  const [loading,   setLoading]   = useState(false)
  const [result,    setResult]    = useState(null)
  const [error,     setError]     = useState('')
  const inputRef = useRef()

  function handleFile(f) {
    setFile(f)
    setResult(null)
    setError('')
  }

  function onDrop(e) {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }

  async function handleClassify() {
    if (!file) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const data = await api.classify(file)
      setResult(data)
    } catch (err) {
      setError(err.message || 'Classification failed')
    } finally {
      setLoading(false)
    }
  }

  function reset() {
    setFile(null)
    setResult(null)
    setError('')
  }

  return (
    <div className="p-8 max-w-2xl mx-auto w-full">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Classify Document</h1>
        <p className="text-slate-500 text-sm mt-1">Upload an image and the model will predict its document type</p>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`rounded-xl border-2 border-dashed cursor-pointer transition-colors p-10 text-center mb-6 ${
          dragging
            ? 'border-indigo-400 bg-indigo-50'
            : file
            ? 'border-emerald-300 bg-emerald-50'
            : 'border-slate-300 bg-white hover:border-indigo-300 hover:bg-slate-50'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/*,.tiff,.tif"
          className="hidden"
          onChange={e => e.target.files[0] && handleFile(e.target.files[0])}
        />

        {file ? (
          <div className="flex flex-col items-center gap-2">
            <svg viewBox="0 0 20 20" fill="currentColor" className="w-8 h-8 text-emerald-500">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
            </svg>
            <p className="text-sm font-semibold text-slate-800">{file.name}</p>
            <p className="text-xs text-slate-400">{(file.size / 1024).toFixed(1)} KB · click to change</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-10 h-10 text-slate-300">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"/>
            </svg>
            <div>
              <p className="text-sm font-medium text-slate-700">Drop a file here or <span className="text-indigo-600">browse</span></p>
              <p className="text-xs text-slate-400 mt-1">TIFF, PNG, JPG supported</p>
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="mb-5 flex items-start gap-2.5 rounded-lg bg-red-50 border border-red-200 px-3.5 py-3 text-sm text-red-700">
          <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 shrink-0 mt-0.5">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
          </svg>
          {error}
        </div>
      )}

      <div className="flex gap-3 mb-8">
        <button
          onClick={handleClassify}
          disabled={!file || loading}
          className="flex items-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed px-5 py-2.5 text-sm font-semibold text-white transition shadow-sm"
        >
          {loading && <Spinner size="sm" />}
          {loading ? 'Classifying…' : 'Classify'}
        </button>
        {(file || result) && (
          <button
            onClick={reset}
            className="rounded-lg border border-slate-300 bg-white px-5 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition"
          >
            Reset
          </button>
        )}
      </div>

      {/* Result */}
      {result && (
        <div className="rounded-xl bg-white border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-100 bg-slate-50">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Classification result</span>
          </div>

          {/* Primary result */}
          <div className="px-6 py-6 flex items-center gap-6 border-b border-slate-100">
            <div className="flex-1">
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Predicted type</p>
              <p className="text-2xl font-bold text-slate-900 capitalize">{result.label.replace(/_/g, ' ')}</p>
            </div>
            <div className="text-right">
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">Confidence</p>
              <p className={`text-2xl font-bold tabular-nums ${result.confidence >= 0.7 ? 'text-emerald-600' : 'text-amber-500'}`}>
                {(result.confidence * 100).toFixed(1)}%
              </p>
            </div>
          </div>

          {/* Confidence bar */}
          <div className="px-6 py-3 border-b border-slate-100">
            <ConfidenceBar value={result.confidence} />
          </div>

          {/* Top 5 */}
          <div className="px-6 py-4">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Top 5 predictions</p>
            <div className="space-y-2.5">
              {result.top5.map((p, i) => (
                <div key={p.label} className="flex items-center gap-3">
                  <span className="text-xs text-slate-400 w-4 tabular-nums">{i + 1}</span>
                  <span className={`text-sm capitalize flex-1 ${i === 0 ? 'font-semibold text-slate-900' : 'text-slate-600'}`}>
                    {p.label.replace(/_/g, ' ')}
                  </span>
                  <span className="text-xs font-medium tabular-nums text-slate-500 w-12 text-right">
                    {(p.confidence * 100).toFixed(1)}%
                  </span>
                  <div className="w-24 bg-slate-100 rounded-full h-1.5">
                    <div
                      className={`h-1.5 rounded-full ${i === 0 ? 'bg-indigo-500' : 'bg-slate-300'}`}
                      style={{ width: `${(p.confidence * 100).toFixed(1)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
