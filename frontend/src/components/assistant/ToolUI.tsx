import { useAui, type ToolCallMessagePartComponent, type ToolCallMessagePartProps } from '@assistant-ui/react'
import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { Check, Pencil, Star } from 'lucide-react'
import { useState } from 'react'
import type { WidgetSpec } from '@/api/generated'
import { ToolFallback } from '@/components/assistant-ui/elements/tool-fallback.aui'
import { AddToDashboardMenu } from '@/components/dashboard/AddToDashboardMenu'
import { WidgetBuilder } from '@/components/widgets/WidgetBuilder'
import { WidgetView } from '@/components/widgets/WidgetView'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import type { AddedToDashboardResult, ChartToolResult } from '@/lib/assistantChat'
import { chartTypeLabel, errorMessage, previewOptions } from '@/lib/widgets'

/**
 * How the assistant's tool calls look in the chat. Charts and "added to dashboard"
 * get their own cards; the lookups it does along the way use the collapsed default.
 * Pass as `<Thread components={{ ToolFallback: ToolUI }} />`.
 */
export const ToolUI: ToolCallMessagePartComponent = (props) => {
  switch (props.toolName) {
    case 'make_chart':
      return <ChartCard {...props} />
    case 'add_chart_to_dashboard':
      return <AddedCard {...props} />
    default:
      return <ToolFallback {...props} />
  }
}

function ChartCard({ result, status }: ToolCallMessagePartProps) {
  const chart = result as ChartToolResult | undefined
  if (!chart?.spec) {
    if (status.type === 'incomplete') return <ToolFallback {...({ result, status } as ToolCallMessagePartProps)} />
    return <Skeleton className="my-3 h-72 w-full rounded-lg" />
  }
  return <ChartCardBody chart={chart} />
}

function ChartCardBody({ chart }: { chart: ChartToolResult }) {
  const aui = useAui()
  // "Edit chart" changes this card's chart; "Add to dashboard" then pins the edited one
  const [spec, setSpec] = useState<WidgetSpec>(chart.spec)
  const [title, setTitle] = useState(chart.spec.chart?.title ?? '')
  const [editing, setEditing] = useState(false)
  const preview = useQuery(previewOptions(spec))

  const drawn = preview.data?.chart_type ?? chart.chart_type
  const suggestBetter = chart.requested_feasible && chart.recommended !== drawn && spec === chart.spec
  const shownTitle = title || preview.data?.title || chart.title

  return (
    <div className="my-3 overflow-hidden rounded-lg border bg-card">
      <div className="flex items-baseline gap-2 border-b px-3 py-2">
        <span className="min-w-0 flex-1 truncate text-sm font-medium" title={shownTitle}>
          {shownTitle}
        </span>
        <span className="shrink-0 text-xs text-muted-foreground">{chartTypeLabel(drawn)}</span>
      </div>

      {!chart.requested_feasible && chart.user_requested && spec === chart.spec && (
        <p className="border-b bg-muted/40 px-3 py-1.5 text-xs text-muted-foreground">
          Showing a {chartTypeLabel(drawn).toLowerCase()}: {chart.requested_note}.
        </p>
      )}

      <div className="h-72 p-2">
        {preview.isPending && <Skeleton className="h-full w-full" />}
        {preview.isError && <p className="p-2 text-sm text-destructive">{errorMessage(preview.error)}</p>}
        {preview.data && <WidgetView result={preview.data} className="h-full" />}
      </div>

      <div className="flex flex-wrap items-center gap-2 border-t px-3 py-2">
        <AddToDashboardMenu spec={{ ...spec, chart: { ...spec.chart, title } }} title={shownTitle} />
        <Button variant="ghost" size="sm" className="gap-1.5" onClick={() => setEditing(true)}>
          <Pencil className="h-4 w-4" /> Edit chart
        </Button>
        {suggestBetter && (
          <Button
            variant="ghost"
            size="sm"
            className="ml-auto gap-1.5 text-muted-foreground"
            title={chart.recommended_reason}
            onClick={() => aui.thread.append(`Show that as a ${chartTypeLabel(chart.recommended).toLowerCase()} chart instead.`)}
          >
            <Star className="h-3.5 w-3.5" /> Try {chartTypeLabel(chart.recommended).toLowerCase()}
          </Button>
        )}
      </div>

      <WidgetBuilder
        open={editing}
        onOpenChange={setEditing}
        heading="Edit chart"
        initial={{ title, spec }}
        onSave={(newTitle, newSpec) => {
          setTitle(newTitle)
          setSpec(newSpec)
          setEditing(false)
        }}
      />
    </div>
  )
}

function AddedCard(props: ToolCallMessagePartProps) {
  const result = props.result as AddedToDashboardResult | undefined
  if (!result?.added || result.dashboard_id === null) return <ToolFallback {...props} />
  return (
    <div className="my-2 flex items-center gap-2 rounded-md border px-3 py-2 text-sm">
      <Check className="h-4 w-4 text-emerald-600" />
      <span>Added to</span>
      <Link to="/" search={{ d: result.dashboard_id }} className="font-medium underline">
        {result.dashboard_name}
      </Link>
    </div>
  )
}
