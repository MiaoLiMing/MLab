import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api, authenticatedFetch } from '@/api/client'
import { readSSE } from '@/api/sse'
import type { ChatMessage, ConversationDetail } from '@/types/api'

import { useChatStore } from './chat'

vi.mock('@/api/client', () => ({ api: vi.fn(), authenticatedFetch: vi.fn() }))
vi.mock('@/api/sse', () => ({ readSSE: vi.fn() }))

const userMessage: ChatMessage = {
  id: 'user-1',
  conversation_id: 'conversation-1',
  parent_id: null,
  role: 'user',
  content: '旧问题',
  status: 'completed',
  model: null,
  input_tokens: 0,
  output_tokens: 0,
  error_code: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
  attachments: [],
}

function conversation(messages: ChatMessage[]): ConversationDetail {
  return {
    id: 'conversation-1',
    assistant_id: null,
    model_config_id: null,
    title: '测试会话',
    archived_at: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    messages,
  }
}

describe('chat store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(api).mockReset()
    vi.mocked(authenticatedFetch).mockReset()
    vi.mocked(readSSE).mockReset()
  })

  it('拼接流式消息并携带编辑来源消息', async () => {
    const store = useChatStore()
    store.current = conversation([
      { ...userMessage },
      { ...userMessage, id: 'old-answer', role: 'assistant', content: '旧回答' },
    ])
    vi.mocked(authenticatedFetch).mockResolvedValue(new Response('{}', { status: 200 }))
    vi.mocked(readSSE).mockImplementation(async function* () {
      yield { event: 'message.start', data: { message_id: 'new-answer' } }
      yield { event: 'message.delta', data: { content: '新回答' } }
      yield { event: 'message.done', data: { status: 'completed' } }
    })
    vi.mocked(api)
      .mockResolvedValueOnce(
        conversation([
          { ...userMessage, content: '新问题' },
          { ...userMessage, id: 'new-answer', role: 'assistant', content: '新回答' },
        ]) as never,
      )
      .mockResolvedValueOnce([] as never)

    await store.send('新问题', undefined, [], 'user-1')

    const request = vi.mocked(authenticatedFetch).mock.calls[0]
    expect(JSON.parse(String(request[1]?.body))).toMatchObject({
      content: '新问题',
      source_message_id: 'user-1',
    })
    expect(store.current?.messages.map((item) => item.content)).toEqual(['新问题', '新回答'])
    expect(store.streaming).toBe(false)
  })
})
