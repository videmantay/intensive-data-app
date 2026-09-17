import type { ChatModelAdapter } from '@assistant-ui/react'

/** Pull the plain text out of an assistant-ui message (ignores images, tool calls, etc.). */
function textOf(message: { content: readonly { type: string; text?: string }[] }) {
  return message.content
    .filter((part) => part.type === 'text')
    .map((part) => part.text ?? '')
    .join('')
}

/**
 * Connects assistant-ui to POST /api/assistant/chat, which streams plain text
 * chunks from the OpenAI model. Each yield replaces the message content, so we
 * accumulate as chunks arrive.
 */
export const assistantAdapter: ChatModelAdapter = {
  async *run({ messages, abortSignal }) {
    const response = await fetch('/api/assistant/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: abortSignal,
      body: JSON.stringify({
        messages: messages
          .filter((m) => m.role === 'user' || m.role === 'assistant')
          .map((m) => ({ role: m.role, content: textOf(m) })),
      }),
    })

    if (!response.ok || !response.body) {
      const detail = await response.text().catch(() => '')
      throw new Error(detail ? JSON.parse(detail).detail ?? detail : `Request failed (${response.status})`)
    }

    const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
    let text = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      text += value
      yield { content: [{ type: 'text', text }] }
    }
  },
}
