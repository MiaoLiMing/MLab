import type { ApiErrorBody } from '@/types/api'

// 基础服务前缀，优先从环境变量读取，默认自动挂载 MLab 专用接口路径
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://114.132.64.216/api/v1/mlab'

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number,
  ) {
    super(message)
  }
}

let refreshRequest: Promise<boolean> | null = null

async function requestAccessTokenRefresh(): Promise<boolean> {
  const refreshToken = localStorage.getItem('mlab_refresh_token')
  if (!refreshToken) return false
  const response = await fetch(`${API_BASE}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
  if (!response.ok) return false
  const data = (await response.json()) as {
    access_token: string
    refresh_token: string
  }
  localStorage.setItem('mlab_access_token', data.access_token)
  localStorage.setItem('mlab_refresh_token', data.refresh_token)
  return true
}

async function refreshAccessToken(): Promise<boolean> {
  if (!refreshRequest) {
    refreshRequest = requestAccessTokenRefresh().finally(() => {
      refreshRequest = null
    })
  }
  return refreshRequest
}

export async function authenticatedFetch(
  path: string,
  init: RequestInit = {},
  retry = true,
): Promise<Response> {
  const token = localStorage.getItem('mlab_access_token')
  const headers = new Headers(init.headers)
  if (!(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers })
  if (response.status === 401 && retry && (await refreshAccessToken())) {
    return authenticatedFetch(path, init, false)
  }
  return response
}

export async function api<T>(
  path: string,
  init: RequestInit = {},
  retry = true,
): Promise<T> {
  const response = await authenticatedFetch(path, init, retry)
  if (!response.ok) {
    let body: ApiErrorBody | null = null
    try {
      body = (await response.json()) as ApiErrorBody
    } catch {
      // Upstream gateways may return a non-JSON body.
    }
    throw new ApiError(body?.error?.code ?? 'REQUEST_FAILED', body?.error?.message ?? '请求失败', response.status)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export { API_BASE }
