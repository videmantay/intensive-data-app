import { useMutation, useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { Check, LayoutGrid, Plus } from 'lucide-react'
import { useState } from 'react'
import type { WidgetSpec } from '@/api/generated'
import {
  createDashboardMutation,
  createWidgetMutation,
  listDashboardsOptions,
} from '@/api/generated/@tanstack/react-query.gen'
import { NameDialog } from '@/components/dashboard/NameDialog'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

/** "Add to dashboard ▾": pins a chart spec to one of the user's dashboards, or a new one. */
export function AddToDashboardMenu({ spec, title }: { spec: WidgetSpec; title: string }) {
  const dashboards = useQuery(listDashboardsOptions())
  const addWidget = useMutation(createWidgetMutation())
  const createDashboard = useMutation(createDashboardMutation())
  const [naming, setNaming] = useState(false)
  const [addedTo, setAddedTo] = useState<{ id: number; name: string } | null>(null)

  const add = (dashboard: { id: number; name: string }) =>
    addWidget.mutate(
      { path: { dashboard_id: dashboard.id }, body: { title: spec.chart?.title ?? '', spec } },
      { onSuccess: () => setAddedTo(dashboard) },
    )

  if (addedTo) {
    return (
      <Button variant="ghost" size="sm" className="gap-1.5" asChild>
        <Link to="/" search={{ d: addedTo.id }}>
          <Check className="h-4 w-4 text-emerald-600" /> Added to {addedTo.name}
        </Link>
      </Button>
    )
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="gap-1.5" disabled={addWidget.isPending}>
            <LayoutGrid className="h-4 w-4" /> Add to dashboard
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          <DropdownMenuLabel className="max-w-64 truncate text-xs text-muted-foreground">{title}</DropdownMenuLabel>
          {dashboards.data?.map((d) => (
            <DropdownMenuItem key={d.id} onSelect={() => add(d)}>
              {d.name}
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={() => setNaming(true)}>
            <Plus className="h-4 w-4" /> New dashboard…
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <NameDialog
        open={naming}
        onOpenChange={setNaming}
        title="New dashboard"
        submitLabel="Create and add"
        onSubmit={(name) =>
          createDashboard.mutate(
            { body: { name } },
            {
              onSuccess: (dashboard) => {
                setNaming(false)
                add(dashboard)
              },
            },
          )
        }
      />
    </>
  )
}
