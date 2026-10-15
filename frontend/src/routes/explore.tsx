import { useMutation, useQuery } from '@tanstack/react-query'
import { createFileRoute, redirect, useNavigate } from '@tanstack/react-router'
import { MessageSquarePlus, MoreHorizontal, Pencil, Trash2 } from 'lucide-react'
import { useState } from 'react'
import {
  assistantStatusOptions,
  deleteThreadMutation,
  listThreadsOptions,
  renameThreadMutation,
} from '@/api/generated/@tanstack/react-query.gen'
import { ChatView } from '@/components/assistant/ChatView'
import { NameDialog } from '@/components/dashboard/NameDialog'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/explore')({
  // The agent view is hidden for now; the page below still works. Remove this to show it.
  beforeLoad: () => {
    throw redirect({ to: '/' })
  },
  // ?t=12 opens a saved thread; no `t` is a new chat
  validateSearch: (search: Record<string, unknown>): { t?: number } => ({
    t: Number(search.t) > 0 ? Number(search.t) : undefined,
  }),
  component: ExplorePage,
})

function ExplorePage() {
  const { t } = Route.useSearch()
  const navigate = useNavigate({ from: '/explore' })
  const threads = useQuery(listThreadsOptions())
  const status = useQuery(assistantStatusOptions())
  const [renaming, setRenaming] = useState<{ id: number; title: string } | null>(null)
  const rename = useMutation(renameThreadMutation())
  const remove = useMutation(deleteThreadMutation())

  const open = (id?: number) => navigate({ search: id ? { t: id } : {}, replace: false })

  return (
    // Break out of the page's max-width container to use the full height
    <div className="-mx-4 -my-6 flex h-[calc(100svh-57px)] border-t md:mx-[calc(50%-50vw)]">
      <aside className="hidden w-64 shrink-0 flex-col border-r md:flex">
        <div className="p-3">
          <Button variant="outline" className="w-full justify-start gap-2" onClick={() => open()}>
            <MessageSquarePlus className="h-4 w-4" /> New chat
          </Button>
        </div>
        <nav className="min-h-0 flex-1 space-y-0.5 overflow-y-auto px-2 pb-3">
          {threads.data?.length === 0 && <p className="px-2 text-sm text-muted-foreground">No saved chats yet.</p>}
          {threads.data?.map((thread) => (
            <div
              key={thread.id}
              className={cn(
                'group flex items-center rounded-md text-sm hover:bg-muted',
                thread.id === t && 'bg-muted font-medium',
              )}
            >
              <button className="min-w-0 flex-1 truncate px-2 py-1.5 text-left" onClick={() => open(thread.id)}>
                {thread.title}
              </button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 opacity-0 group-hover:opacity-100 data-[state=open]:opacity-100"
                    aria-label="Chat menu"
                  >
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onSelect={() => setRenaming(thread)}>
                    <Pencil className="h-4 w-4" /> Rename
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    variant="destructive"
                    onSelect={() =>
                      remove.mutate(
                        { path: { thread_id: thread.id } },
                        { onSuccess: () => thread.id === t && open() },
                      )
                    }
                  >
                    <Trash2 className="h-4 w-4" /> Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          ))}
        </nav>
      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        {status.data && !status.data.configured && (
          <p className="border-b bg-amber-50 px-4 py-2 text-xs text-amber-900 dark:bg-amber-950 dark:text-amber-200">
            Set <code>OPENAI_API_KEY</code> in <code>backend/.env</code> and restart the API to enable chat.
          </p>
        )}
        <div className="min-h-0 flex-1">
          <ChatView key={t ?? 'new'} threadId={t ?? null} onThreadCreated={(id) => navigate({ search: { t: id }, replace: true })} />
        </div>
      </section>

      <NameDialog
        open={renaming !== null}
        onOpenChange={(o) => !o && setRenaming(null)}
        title="Rename chat"
        initial={renaming?.title}
        onSubmit={(title) =>
          renaming &&
          rename.mutate({ path: { thread_id: renaming.id }, body: { title } }, { onSuccess: () => setRenaming(null) })
        }
      />
    </div>
  )
}
