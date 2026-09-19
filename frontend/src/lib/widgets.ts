import { queryOptions } from '@tanstack/react-query'
import { previewWidget, type ChartSpec, type WidgetSpec } from '@/api/generated'

export type ChartType = NonNullable<ChartSpec['type']>

export const CHART_TYPES: { value: ChartType; label: string }[] = [
  { value: 'bar', label: 'Bar' },
  { value: 'line', label: 'Line' },
  { value: 'area', label: 'Area' },
  { value: 'scatter', label: 'Scatter' },
  { value: 'histogram', label: 'Histogram' },
  { value: 'box', label: 'Box plot' },
  { value: 'donut', label: 'Donut' },
  { value: 'pie', label: 'Pie' },
  { value: 'heatmap', label: 'Heatmap' },
  { value: 'treemap', label: 'Treemap' },
  { value: 'radar', label: 'Radar' },
  { value: 'funnel', label: 'Funnel' },
  { value: 'kpi', label: 'KPI' },
  { value: 'table', label: 'Table' },
]

export const chartTypeLabel = (type: ChartType) => CHART_TYPES.find((c) => c.value === type)?.label ?? type

/**
 * Run a widget spec without saving it (builder preview, charts in the chat).
 *
 * The endpoint is a POST, but it only reads data, so it's used as a query: a mutation
 * would make queryClient refetch everything on screen after every preview.
 */
export const previewOptions = (spec: WidgetSpec) =>
  queryOptions({
    queryKey: ['previewWidget', spec],
    queryFn: async ({ signal }) => {
      const { data } = await previewWidget({ body: spec, signal, throwOnError: true })
      return data
    },
    retry: false,
  })

/** Drops filters the user hasn't filled in yet, so a half-typed filter doesn't fail the query. */
export function withoutBlankFilters(spec: WidgetSpec): WidgetSpec {
  const filters = (spec.query.filters ?? []).filter((f) =>
    Array.isArray(f.value) ? f.value.length > 0 : f.value !== '' && f.value != null,
  )
  return { ...spec, query: { ...spec.query, filters } }
}

/** The `detail` text of a FastAPI error, for showing to the user. */
export function errorMessage(error: unknown): string {
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = (error as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map((d) => d?.msg ?? String(d)).join('; ')
  }
  if (error instanceof Error) return error.message
  return 'Something went wrong'
}
