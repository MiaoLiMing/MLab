import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { ChatMessage } from '@/types/api'

import MessageBubble from './MessageBubble.vue'

function message(role: ChatMessage['role'], content: string): ChatMessage {
  return {
    id: 'message-1',
    conversation_id: 'conversation-1',
    parent_id: null,
    role,
    content,
    status: 'completed',
    model: null,
    input_tokens: 0,
    output_tokens: 0,
    error_code: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    attachments: [],
  }
}

describe('MessageBubble', () => {
  it('渲染带语法高亮的代码块', () => {
    const wrapper = mount(MessageBubble, {
      props: { message: message('assistant', '```js\nconst answer = 42\n```') },
    })
    expect(wrapper.find('.markdown > code').exists()).toBe(true)
    expect(wrapper.find('.hljs-keyword').text()).toBe('const')
  })

  it('允许编辑用户消息并提交重新生成', async () => {
    const source = message('user', '旧问题')
    const wrapper = mount(MessageBubble, { props: { message: source } })
    await wrapper.get('[title="编辑后重新生成"]').trigger('click')
    await wrapper.get('textarea').setValue('新问题')
    await wrapper.get('[title="保存并重新生成"]').trigger('click')
    expect(wrapper.emitted('edit')?.[0]).toEqual([source, '新问题'])
  })
})
