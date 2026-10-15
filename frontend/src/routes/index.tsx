import { useMutation, useQuery } from '@tanstack/react-query'
import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { Check, LayoutGrid, MoreHorizontal, Pencil, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import {
  createDashboardMutation,
  createWidgetMutation,
  deleteDashboardMutation,
  getDashboardOptions,
  listDashboardsOptions,
  renameDashboardMutation,
} from '@/api/generated/@tanstack/react-query.gen'
import { DashboardGrid } from '@/components/dashboard/DashboardGrid'
import { NameDialog } from '@/components/dashboard/NameDialog'
import { WidgetBuilder } from '@/components/widgets/WidgetBuilder'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { errorMessage } from '@/lib/widgets'

export const Route = createFileRoute('/')({
  // ?d=3 selects a dashboard, so links from the assistant can open the right one
  validateSearch: (search: Record<string, unknown>): { d?: number } => ({
    d: Number(search.d) > 0 ? Number(search.d) : undefined,
  }),
  component: DashboardPage,
})

type DialogName = 'new' | 'rename' | 'widget' | null

function DashboardPage() {
  const { d } = Route.useSearch()
  const navigate = useNavigate({ from: '/' })
  const [editing, setEditing] = useState(false)
  const [dialog, setDialog] = useState<DialogName>(null)

  const dashboards = useQuery(listDashboardsOptions())
  const dashboardId = dashboards.data?.find((x) => x.id === d)?.id ?? dashboards.data?.[0]?.id
  const detail = useQuery({
    ...getDashboardOptions({ path: { dashboard_id: dashboardId ?? 0 } }),
    enabled: dashboardId !== undefined,
  })

  const select = (id: number) => navigate({ search: { d: id } })
  const create = useMutation({ ...createDashboardMutation(), onSuccess: (dash) => select(dash.id) })
  const rename = useMutation(renameDashboardMutation())
  const remove = useMutation({ ...deleteDashboardMutation(), onSuccess: () => navigate({ search: {} }) })
  const addWidget = useMutation(createWidgetMutation())

  const error = dashboards.error ?? detail.error
  const current = detail.data

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <LayoutGrid className="h-5 w-5 text-muted-foreground" />
        <Select value={dashboardId ? String(dashboardId) : undefined} onValueChange={(v) => select(Number(v))}>
          <SelectTrigger className="h-9 w-auto min-w-48 border-none px-1 text-xl font-semibold shadow-none">
            <SelectValue placeholder="Dashboard" />
          </SelectTrigger>
          <SelectContent>
            {dashboards.data?.map((x) => (
              <SelectItem key={x.id} value={String(x.id)}>
                {x.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Dashboard menu">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            <DropdownMenuItem onSelect={() => setDialog('new')}>
              <Plus className="h-4 w-4" /> New dashboard
            </DropdownMenuItem>
            <DropdownMenuItem disabled={!current} onSelect={() => setDialog('rename')}>
              <Pencil className="h-4 w-4" /> Rename
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              variant="destructive"
              disabled={!current}
              onSelect={() => {
                if (current && confirm(`Delete "${current.name}" and all its widgets?`)) {
                  remove.mutate({ path: { dashboard_id: current.id } })
                }
              }}
            >
              <Trash2 className="h-4 w-4" /> Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <div className="ml-auto flex gap-2">
          <Button variant={editing ? 'default' : 'outline'} size="sm" className="gap-2" onClick={() => setEditing((e) => !e)}>
            {editing ? <Check className="h-4 w-4" /> : <LayoutGrid className="h-4 w-4" />}
            {editing ? 'Done' : 'Edit layout'}
          </Button>
          <Button size="sm" className="gap-2" disabled={!current} onClick={() => setDialog('widget')}>
            <Plus className="h-4 w-4" /> Add widget
          </Button>
        </div>
      </div>

      {editing && (
        <p className="text-sm text-muted-foreground">Drag tiles by their title bar and resize them from the corner.</p>
      )}
      {error && <p className="text-destructive">{errorMessage(error)}</p>}
      {(dashboards.isPending || detail.isPending) && !error && <p className="text-muted-foreground">Loading…</p>}

      {current && current.widgets.length === 0 && (
        <div className="rounded-lg border border-dashed p-10 text-center text-muted-foreground">
          <p>This dashboard is empty.</p>
          <p className="text-sm">
            Add a widget, or ask the Assistant a question and pin its chart here.
          </p>
        </div>
      )}
      {current && <DashboardGrid dashboardId={current.id} widgets={current.widgets} editing={editing} />}

      <NameDialog
        open={dialog === 'new'}
        onOpenChange={(open) => setDialog(open ? 'new' : null)}
        title="New dashboard"
        submitLabel="Create"
        onSubmit={(name) => create.mutate({ body: { name } }, { onSuccess: () => setDialog(null) })}
      />
      <NameDialog
        open={dialog === 'rename'}
        onOpenChange={(open) => setDialog(open ? 'rename' : null)}
        title="Rename dashboard"
        initial={current?.name}
        onSubmit={(name) =>
          current &&
          rename.mutate({ path: { dashboard_id: current.id }, body: { name } }, { onSuccess: () => setDialog(null) })
        }
      />
      <WidgetBuilder
        open={dialog === 'widget'}
        onOpenChange={(open) => setDialog(open ? 'widget' : null)}
        saving={addWidget.isPending}
        onSave={(title, spec) =>
          current &&
          addWidget.mutate(
            { path: { dashboard_id: current.id }, body: { title, spec } },
            { onSuccess: () => setDialog(null) },
          )
        }
      />
    </div>
  )
}
