import type { ColDef } from 'ag-grid-community'
import type { WidgetResult } from '@/api/generated'
import { DataGrid } from '@/components/DataGrid'
import { PlotlyChart } from '@/components/PlotlyChart'

/** Draws a widget's result: its Plotly figure, or a grid for tables and empty results. */
export function WidgetView({ result, className }: { result: WidgetResult; className?: string }) {
  if (result.figure) {
    return <PlotlyChart figure={result.figure} className={className} />
  }
  if (result.row_count === 0) {
    return <p className="p-4 text-sm text-muted-foreground">No rows match this query.</p>
  }
  const columns: ColDef<Record<string, unknown>>[] = result.columns.map((c) => ({
    field: c.name,
    headerName: c.label,
    flex: 1,
    type: c.kind === 'measure' || c.kind === 'numeric' ? 'numericColumn' : undefined,
    valueFormatter:
      c.kind === 'temporal'
        ? (p) => (p.value ? new Date(p.value as string).toLocaleDateString() : '')
        : c.kind === 'measure'
          ? (p) => (typeof p.value === 'number' ? p.value.toLocaleString() : String(p.value ?? ''))
          : undefined,
  }))
  return (
    <div className={className}>
      <DataGrid rowData={result.rows} columnDefs={columns} height="100%" />
    </div>
  )
}
