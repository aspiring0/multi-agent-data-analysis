/**
 * API 客户端 - 与后端 FastAPI 通信
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface ApiResponse<T = Record<string, unknown>> {
  ok: boolean
  data: T | null
  error?: string
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type JsonData = Record<string, any>

// ---- Session API ----

export async function createSession(name: string): Promise<ApiResponse<JsonData>> {
  const res = await fetch(`${API_BASE}/api/sessions/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    return { ok: false, data: null, error: err.detail }
  }
  const data = await res.json()
  return { ok: true, data }
}

export async function listSessions(): Promise<ApiResponse<JsonData[]>> {
  const res = await fetch(`${API_BASE}/api/sessions/`)
  if (!res.ok) {
    return { ok: false, data: null, error: res.statusText }
  }
  const data = await res.json()
  return { ok: true, data }
}

export async function getSession(sessionId: string): Promise<ApiResponse<JsonData>> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    return { ok: false, data: null, error: err.detail }
  }
  const data = await res.json()
  return { ok: true, data }
}

export async function deleteSession(sessionId: string): Promise<ApiResponse<JsonData>> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}`, {
    method: 'DELETE',
  })
  if (!res.ok) {
    return { ok: false, data: null, error: res.statusText }
  }
  const data = await res.json()
  return { ok: true, data }
}

export async function updateSessionName(sessionId: string, name: string): Promise<ApiResponse<JsonData>> {
  const res = await fetch(`${API_BASE}/api/sessions/${sessionId}/name?name=${encodeURIComponent(name)}`, {
    method: 'PATCH',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    return { ok: false, data: null, error: err.detail }
  }
  const data = await res.json()
  return { ok: true, data }
}

// ---- Chat API ----

export async function sendChat(
  sessionId: string,
  message: string,
): Promise<ApiResponse<JsonData>> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    return { ok: false, data: null, error: err.detail }
  }
  const data = await res.json()
  return { ok: true, data }
}

// ---- Upload API ----

export async function uploadFile(
  sessionId: string,
  file: File,
): Promise<ApiResponse<JsonData>> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${API_BASE}/api/upload/${sessionId}/`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    return { ok: false, data: null, error: err.detail }
  }
  const data = await res.json()
  return { ok: true, data }
}

// ---- Health Check ----

export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`)
    return res.ok
  } catch {
    return false
  }
}
