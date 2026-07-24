import { beforeEach, describe, expect, it, vi } from 'vitest'

import { authenticatedFetch } from './client'

describe('authenticatedFetch', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('并发请求过期时只刷新一次令牌，并让所有请求重试成功', async () => {
    localStorage.setItem('mlab_access_token', 'expired-access')
    localStorage.setItem('mlab_refresh_token', 'valid-refresh')
    let refreshCount = 0

    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
        const url = String(input)
        if (url.endsWith('/auth/refresh')) {
          refreshCount += 1
          await new Promise((resolve) => setTimeout(resolve, 5))
          return new Response(
            JSON.stringify({
              access_token: 'fresh-access',
              refresh_token: 'fresh-refresh',
            }),
            { status: 200, headers: { 'Content-Type': 'application/json' } },
          )
        }

        const authorization = new Headers(init?.headers).get('Authorization')
        if (authorization === 'Bearer expired-access') {
          return new Response(null, { status: 401 })
        }
        return new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }),
    )

    const [first, second] = await Promise.all([
      authenticatedFetch('/conversations'),
      authenticatedFetch('/model-configs'),
    ])

    expect(first.status).toBe(200)
    expect(second.status).toBe(200)
    expect(refreshCount).toBe(1)
    expect(localStorage.getItem('mlab_access_token')).toBe('fresh-access')
    expect(localStorage.getItem('mlab_refresh_token')).toBe('fresh-refresh')
  })
})
