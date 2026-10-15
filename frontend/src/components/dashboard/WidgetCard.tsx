import { useMutation, useQuery } from '@tanstack/react-query'
import { Copy, GripVertical, MoreHorizontal, Pencil, RefreshCw, Trash2 } from 'lucide-react'
import { useState } from 'react'
import type { WidgetPublic } from '@/api/generated'
import {
  createWidgetMutation,
  deleteWidgetMutation,
  updateWidgetMutation,
  widgetDataOptions,
} from '@/api/generated/@tanstack/react-query.gen'
import { WidgetBuilder } from '@/components/widgets/WidgetBuilder'
import { WidgetView } from '@/components/widgets/WidgetView'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'
import { errorMessage } from '@/lib/widgets'

/** CSS class of the part of a card you drag it by (see DashboardGrid). */
export const DRAG_HANDLE = 'widget-drag-handle'

/** One dashboard tile: title bar with a menu, and the widget's live chart. */
export function WidgetCard({ widget, editing }: { widget: WidgetPublic; editing: boolean }) {
  const data = useQuery(widgetDataOptions({ path: { widget_id: widget.id } }))
  const [editOpen, setEditOpen] = useState(false)
  const update = useMutation(updateWidgetMutation())
  const duplicate = useMutation(createWidgetMutation())
  const remove = useMutation(deleteWidgetMutation())

  const title = widget.title || data.data?.title || 'Untitled'

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-lg border bg-card shadow-xs">
      <div className={cn('flex items-center gap-1 border-b py-1 pr-1 pl-3', editing && `${DRAG_HANDLE} cursor-move`)}>
        {editing && <GripVertical className="h-4 w-4 shrink-0 text-muted-foreground" />}
        <h3 className="min-w-0 flex-1 truncate text-sm font-medium" title={title}>
          {title}
        </h3>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-7 w-7" aria-label="Widget menu">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onSelect={() => setEditOpen(true)}>
              <Pencil className="h-4 w-4" /> Edit
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => data.refetch()}>
              <RefreshCw className="h-4 w-4" /> Refresh
            </DropdownMenuItem>
            <DropdownMenuItem
              onSelect={() =>
                duplicate.mutate({
                  path: { dashboard_id: widget.dashboard_id },
                  body: { title: widget.title && `${widget.title} (copy)`, spec: widget.spec, w: widget.w, h: widget.h },
                })
              }
            >
              <Copy className="h-4 w-4" /> Duplicate
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              variant="destructive"
              onSelect={() => {
                if (confirm(`Remove "${title}" from this dashboard?`)) remove.mutate({ path: { widget_id: widget.id } })
              }}
            >
              <Trash2 className="h-4 w-4" /> Remove
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <div className="min-h-0 flex-1 p-2">
        {data.isPending && <p className="p-2 text-sm text-muted-foreground">Loading…</p>}
        {data.isError && <p className="p-2 text-sm text-destructive">{errorMessage(data.error)}</p>}
        {data.data && <WidgetView result={data.data} className="h-full" />}
      </div>

      <WidgetBuilder
        open={editOpen}
        onOpenChange={setEditOpen}
        initial={{ title: widget.title, spec: widget.spec }}
        saving={update.isPending}
        onSave={(newTitle, spec) =>
          update.mutate(
            { path: { widget_id: widget.id }, body: { title: newTitle, spec } },
            { onSuccess: () => setEditOpen(false) },
          )
        }
      />
    </div>
  )
}
