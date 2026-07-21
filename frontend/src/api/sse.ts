export interface SSEMessage {
  event: string
  data: Record<string, unknown>
}

export async function* readSSE(response: Response): AsyncGenerator<SSEMessage> {
  if (!response.body) throw new Error('浏览器不支持流式响应')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value, { stream: !done })
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() ?? ''
    for (const block of blocks) {
      let event = 'message'
      let data = '{}'
      for (const line of block.split('\n')) {
        if (line.startsWith('event:')) event = line.slice(6).trim()
        if (line.startsWith('data:')) data = line.slice(5).trim()
      }
      yield { event, data: JSON.parse(data) as Record<string, unknown> }
    }
    if (done) break
  }
}

