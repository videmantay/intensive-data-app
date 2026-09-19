import { useChatRuntime } from '@assistant-ui/ai-sdk'
import { DefaultChatTransport, type UIMessage } from 'ai'
import { useEffect, useRef, useState } from 'react'
import { createThread, type WidgetSpec } from '@/api/generated'
import type { ChartType } from '@/lib/widgets'
import { queryClient } from '@/lib/queryClient'

/** What the `make_chart` tool returns (ChartResult in backend/app/analytics/tools.py). */
export type ChartToolResult = {
  spec: WidgetSpec
  title: string
  chart_type: ChartType
  user_requested: ChartType | null
  requested_feasible: boolean
  requested_note: string
  recommended: ChartType
  recommended_reason: string
  row_count: number
}

/** What `add_chart_to_dashboard` returns (backend/app/dashboards/tools.py). */
export type AddedToDashboardResult = {
  added: boolean
  message: string
  dashboard_id: number | null
  dashboard_name: string | null
}

/** What `run_query` returns (backend/app/analytics/tools.py). */
export type QueryToolResult = {
  columns: string[]
  rows: Record<string, unknown>[]
  row_count: number
  truncated: boolean
}

/**
 * The assistant-ui runtime for one chat thread, talking to POST /api/assistant/chat.
 *
 * With `threadId` null, the thread is created on the server when the first message is
 * sent, and `onThreadCreated` is called once the reply has finished. The server keeps
 * the history, so only the newest user message is sent.
 */
export function useAssistantChat({
  threadId,
  initialMessages,
  onThreadCreated,
}: {
  threadId: number | null
  initialMessages?: UIMessage[]
  onThreadCreated?: (id: number) => void
}) {
  const threadRef = useRef(threadId)
  const createdRef = useRef(false)
  const callbackRef = useRef(onThreadCreated)
  useEffect(() => {
    callbackRef.current = onThreadCreated
  }, [onThreadCreated])

  // Created once per chat; it reads the thread id from the ref when a message is sent
  const [transport] = useState(
    () =>
      new DefaultChatTransport({
        api: '/api/assistant/chat',
        prepareSendMessagesRequest: async ({ id, messages, trigger }) => {
          if (threadRef.current === null) {
            const { data } = await createThread({ throwOnError: true })
            threadRef.current = data.id
            createdRef.current = true
          }
          const lastUser = messages.findLast((m) => m.role === 'user')
          return { body: { id, trigger, threadId: threadRef.current, messages: lastUser ? [lastUser] : [] } }
        },
      }),
  )

  return useChatRuntime({
    transport,
    messages: initialMessages,
    onFinish: () => {
      // New thread title, and any chart the assistant pinned to a dashboard
      queryClient.invalidateQueries()
      if (createdRef.current && threadRef.current !== null) {
        createdRef.current = false
        callbackRef.current?.(threadRef.current)
      }
    },
  })
}
