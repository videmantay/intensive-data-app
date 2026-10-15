import { AssistantRuntimeProvider, useAui } from '@assistant-ui/react'
import { useQuery } from '@tanstack/react-query'
import type { UIMessage } from 'ai'
import { threadMessagesOptions } from '@/api/generated/@tanstack/react-query.gen'
import { Thread } from '@/components/assistant-ui/elements/thread.aui'
import { ToolUI } from '@/components/assistant/ToolUI'
import { Skeleton } from '@/components/ui/skeleton'
import { TooltipProvider } from '@/components/ui/tooltip'
import { useAssistantChat } from '@/lib/assistantChat'
import { errorMessage } from '@/lib/widgets'

const EXAMPLES = [
  'Total quantity by category',
  'Which items have the most stock? Show the top 5',
  'How is quantity per item distributed?',
  'Show quantity by category as a radar chart',
]

/**
 * One chat thread: loads its saved messages, then shows the conversation. With
 * `threadId` null it's a new chat; the thread is created when the first message is
 * sent. Give it `key={threadId}` so switching threads starts a fresh chat.
 */
export function ChatView({
  threadId,
  onThreadCreated,
}: {
  threadId: number | null
  onThreadCreated?: (id: number) => void
}) {
  const saved = useQuery({
    ...threadMessagesOptions({ path: { thread_id: threadId ?? 0 } }),
    enabled: threadId !== null,
    staleTime: Infinity, // the chat owns the messages once it's open
    refetchOnWindowFocus: false,
  })

  if (threadId !== null && saved.isPending) {
    return (
      <div className="mx-auto w-full max-w-2xl space-y-4 p-6">
        <Skeleton className="ml-auto h-9 w-2/5" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }
  if (saved.isError) return <p className="p-6 text-destructive">{errorMessage(saved.error)}</p>

  return (
    <Chat
      threadId={threadId}
      initialMessages={saved.data?.messages as UIMessage[] | undefined}
      onThreadCreated={onThreadCreated}
    />
  )
}

function Chat(props: Parameters<typeof useAssistantChat>[0]) {
  const runtime = useAssistantChat(props)
  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <TooltipProvider>
        <Thread components={{ ToolFallback: ToolUI, Welcome }} />
      </TooltipProvider>
    </AssistantRuntimeProvider>
  )
}

function Welcome() {
  const aui = useAui()
  return (
    <div className="mb-6 space-y-3 px-2">
      <p className="text-2xl font-medium tracking-tight">What do you want to know?</p>
      <p className="text-sm text-muted-foreground">
        Ask about your inventory. Charts can be pinned to a dashboard.
      </p>
      <div className="flex flex-wrap gap-2">
        {EXAMPLES.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => aui.thread.append(q)}
            className="rounded-full border px-3 py-1 text-left text-sm hover:bg-muted"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}
