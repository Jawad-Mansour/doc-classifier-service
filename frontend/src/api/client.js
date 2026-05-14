const BASE = '/api/v1'

function getToken() {
  return localStorage.getItem('token')
}

function authHeaders() {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request(method, path, { body, form } = {}) {
  const headers = { ...authHeaders() }
  let bodyData

  if (form) {
    const fd = new URLSearchParams()
    for (const [k, v] of Object.entries(form)) fd.append(k, v)
    bodyData = fd
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    bodyData = JSON.stringify(body)
  }

  const res = await fetch(`${BASE}${path}`, { method, headers, body: bodyData })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    const message = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
    throw Object.assign(new Error(message || 'Request failed'), { status: res.status, data: err })
  }

  if (res.status === 204) return null
  return res.json()
}

export const api = {
  login:        (email, password) => request('POST', '/auth/login', { form: { username: email, password } }),
  me:           ()                 => request('GET',  '/auth/me'),

  getPredictions: ()               => request('GET',  '/predictions/recent'),
  relabel:      (id, new_label)    => request('PATCH', `/predictions/${id}`, { body: { new_label } }),

  getBatches:   ()                 => request('GET',  '/batches'),
  getBatch:     (id)               => request('GET',  `/batches/${id}`),

  getAuditLog:  ()                 => request('GET',  '/audit-log'),

  changeRole:   (id, role)         => request('PATCH', `/admin/users/${id}/role`, { body: { role } }),

  classify: async (file) => {
    const fd = new FormData()
    fd.append('file', file)
    const res = await fetch(`${BASE}/classify`, {
      method: 'POST',
      headers: authHeaders(),
      body: fd,
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      const message = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail)
      throw Object.assign(new Error(message || 'Classification failed'), { status: res.status })
    }
    return res.json()
  },
}
