import { describe, expect, it } from 'vitest'

import { readSSE } from './sse'

describe('readSSE', () => {
  it('parses events split across transport chunks', async () => {
    const encoder = new TextEncoder()
    const body = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('event: message.delta\ndata: {"content":"你'))
        controller.enqueue(encoder.encode('好"}\n\nevent: message.done\ndata: {"status":"completed"}\n\n'))
        controller.close()
      },
    })
    const events = []
    for await (const event of readSSE(new Response(body))) events.push(event)
    expect(events).toEqual([
      { event: 'message.delta', data: { content: '你好' } },
      { event: 'message.done', data: { status: 'completed' } },
    ])
  })
})

