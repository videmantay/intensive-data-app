import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Plus, Star, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { DatasetInfo, DimensionRef, Filter, WidgetSpec } from '@/api/generated'
import { listDatasetsOptions } from '@/api/generated/@tanstack/react-query.gen'
import { WidgetView } from '@/components/widgets/WidgetView'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'
import {
  CHART_TYPES,
  chartTypeLabel,
  errorMessage,
  previewOptions,
  withoutBlankFilters,
  type ChartType,
} from '@/lib/widgets'

const GRAINS = ['day', 'week', 'month', 'quarter', 'year'] as const
const NO_GRAIN = 'none'

const FILTER_OPS: { value: Filter['op']; label: string }[] = [
  { value: 'eq', label: 'is' },
  { value: 'ne', label: 'is not' },
  { value: 'in', label: 'is one of' },
  { value: 'contains', label: 'contains' },
  { value: 'gte', label: '≥' },
  { value: 'lte', label: '≤' },
  { value: 'relative', label: 'in period' },
]

const PERIODS = [
  'today', 'yesterday', 'this_week', 'last_week', 'last_n_days:7', 'last_n_days:30', 'this_month',
  'last_month', 'last_n_months:3', 'this_quarter', 'last_quarter', 'ytd', 'this_year', 'last_year',
]

/** Waits until `value` stops changing, so typing a filter value doesn't query on every key. */
function useDebounced<T>(value: T, ms = 400): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => {
      // Keep the old object when nothing changed, so this doesn't re-render forever
      setDebounced((prev) => (JSON.stringify(prev) === JSON.stringify(value) ? prev : value))
    }, ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return debounced
}

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Widget to edit, or a chart from the chat; empty for a new widget */
  initial?: { title: string; spec: WidgetSpec }
  heading?: string
  saving?: boolean
  onSave: (title: string, spec: WidgetSpec) => void
}

/**
 * Point-and-click chart builder: pick a dataset, group-bys, measures, filters and a
 * chart type, with a live preview. It edits the same `WidgetSpec` the assistant writes.
 */
export function WidgetBuilder({ open, onOpenChange, ...props }: Props) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90svh] overflow-y-auto sm:max-w-5xl">
        {/* Mounted only while open, so it starts from `initial` every time */}
        {open && <LoadDatasets {...props} onCancel={() => onOpenChange(false)} />}
      </DialogContent>
    </Dialog>
  )
}

type FormProps = Omit<Props, 'open' | 'onOpenChange'> & { onCancel: () => void }

function LoadDatasets(props: FormProps) {
  const datasets = useQuery(listDatasetsOptions())
  if (datasets.isError) return <p className="text-destructive">{errorMessage(datasets.error)}</p>
  if (!datasets.data) return <p className="text-muted-foreground">Loading…</p>
  return <BuilderForm {...props} datasets={datasets.data} />
}

function BuilderForm({ initial, heading, saving, onSave, onCancel, datasets }: FormProps & { datasets: DatasetInfo[] }) {
  const [title, setTitle] = useState(initial?.title ?? '')
  // A new widget starts on the first dataset
  const [spec, setSpec] = useState<WidgetSpec>(() => initial?.spec ?? startingSpec(datasets[0]))

  const dataset = datasets.find((d) => d.name === spec.query.dataset)
  const query = spec.query
  const dims = query.dimensions ?? []
  const measures = query.measures ?? []
  const filters = query.filters ?? []
  const chartType = spec.chart?.type ?? 'bar'

  const setQuery = (patch: Partial<WidgetSpec['query']>) => setSpec((s) => ({ ...s, query: { ...s.query, ...patch } }))
  const setChartType = (type: ChartType) => setSpec((s) => ({ ...s, chart: { ...s.chart, type } }))

  const current = withoutBlankFilters(spec)
  const debounced = useDebounced(current)
  const ready = Boolean(debounced.query.dataset) && (dims.length > 0 || measures.length > 0)
  const preview = useQuery({ ...previewOptions(debounced), enabled: ready, placeholderData: keepPreviousData })
  const rec = preview.data?.recommendation
  // Save exactly what the preview shows, so wait until it has caught up with the form
  const upToDate = JSON.stringify(current) === JSON.stringify(debounced) && !preview.isFetching

  return (
    <>
      <DialogHeader>
        <DialogTitle>{heading ?? (initial ? 'Edit widget' : 'New widget')}</DialogTitle>
      </DialogHeader>

      <div className="grid gap-6 md:grid-cols-[320px_1fr]">
        <div className="space-y-5">
          <Field label="Dataset">
            <Select value={query.dataset} onValueChange={(name) => setSpec(startingSpec(datasets.find((d) => d.name === name)!))}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Choose data" />
              </SelectTrigger>
              <SelectContent>
                {datasets.map((d) => (
                  <SelectItem key={d.name} value={d.name}>
                    {d.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>

          {dataset && (
            <>
              <Field label="Group by">
                {dims.map((dim, i) => (
                  <DimensionRow
                    key={i}
                    dataset={dataset}
                    value={dim}
                    onChange={(d) => setQuery({ dimensions: dims.map((x, j) => (j === i ? d : x)) })}
                    onRemove={() => setQuery({ dimensions: dims.filter((_, j) => j !== i) })}
                  />
                ))}
                {dims.length < 2 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="gap-1"
                    onClick={() => {
                      const unused = dataset.dimensions.find((d) => !dims.some((x) => x.field === d.name))
                      if (unused) setQuery({ dimensions: [...dims, { field: unused.name }] })
                    }}
                  >
                    <Plus className="h-4 w-4" /> Add grouping
                  </Button>
                )}
              </Field>

              <Field label="Measures">
                {dataset.measures.map((m) => (
                  <label key={m.name} className="flex items-center gap-2 text-sm">
                    <Checkbox
                      checked={measures.includes(m.name)}
                      onCheckedChange={(on) =>
                        setQuery({ measures: on ? [...measures, m.name] : measures.filter((x) => x !== m.name) })
                      }
                    />
                    {m.label}
                  </label>
                ))}
              </Field>

              <Field label="Filters">
                {filters.map((f, i) => (
                  <FilterRow
                    key={i}
                    dataset={dataset}
                    value={f}
                    onChange={(nf) => setQuery({ filters: filters.map((x, j) => (j === i ? nf : x)) })}
                    onRemove={() => setQuery({ filters: filters.filter((_, j) => j !== i) })}
                  />
                ))}
                <Button
                  variant="ghost"
                  size="sm"
                  className="gap-1"
                  onClick={() => setQuery({ filters: [...filters, { field: dataset.dimensions[0].name, op: 'eq', value: '' }] })}
                >
                  <Plus className="h-4 w-4" /> Add filter
                </Button>
              </Field>
            </>
          )}

          <Field label="Chart">
            <div className="grid grid-cols-3 gap-1">
              {CHART_TYPES.map((c) => (
                <Button
                  key={c.value}
                  variant={chartType === c.value ? 'default' : 'outline'}
                  size="sm"
                  className={cn('gap-1', rec && !rec.alternatives?.includes(c.value) && rec.best !== c.value && chartType !== c.value && 'text-muted-foreground')}
                  onClick={() => setChartType(c.value)}
                >
                  {rec?.best === c.value && <Star className="h-3 w-3 fill-current" aria-label="Recommended" />}
                  {c.label}
                </Button>
              ))}
            </div>
          </Field>

          <Field label="Title">
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder={preview.data?.title ?? 'Automatic'} />
          </Field>
        </div>

        <div className="min-w-0 space-y-3">
          {rec && (
            <div className="rounded-md border bg-muted/40 px-3 py-2 text-sm">
              {!rec.feasible ? (
                <>
                  Can't draw a {chartTypeLabel(rec.requested).toLowerCase()} here: {rec.requested_note}. Showing a{' '}
                  {chartTypeLabel(rec.best).toLowerCase()} instead.
                </>
              ) : rec.best !== rec.requested ? (
                <>
                  <Star className="mr-1 inline h-3 w-3 fill-current" />A {chartTypeLabel(rec.best).toLowerCase()} would
                  read better: {rec.reason}.{' '}
                  <button className="underline" onClick={() => setChartType(rec.best)}>
                    Switch
                  </button>
                </>
              ) : (
                <>
                  <Star className="mr-1 inline h-3 w-3 fill-current" />
                  Good choice: {rec.reason}.
                </>
              )}
            </div>
          )}
          <div className="h-[380px] rounded-md border p-2">
            {!ready && <p className="p-4 text-sm text-muted-foreground">Pick a grouping or a measure to see a chart.</p>}
            {ready && preview.isError && <p className="p-4 text-sm text-destructive">{errorMessage(preview.error)}</p>}
            {ready && preview.data && <WidgetView result={preview.data} className="h-full" />}
          </div>
          {preview.data?.truncated && (
            <p className="text-xs text-muted-foreground">Showing the first {preview.data.row_count} rows.</p>
          )}
        </div>
      </div>

      <DialogFooter>
        <Button variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button
          disabled={!ready || !upToDate || saving || preview.isError}
          onClick={() => onSave(title, { ...debounced, chart: { ...debounced.chart, type: preview.data?.chart_type ?? chartType } })}
        >
          {saving ? 'Saving…' : 'Save widget'}
        </Button>
      </DialogFooter>
    </>
  )
}

function startingSpec(dataset: DatasetInfo): WidgetSpec {
  const firstCategorical = dataset.dimensions.find((d) => d.kind === 'categorical') ?? dataset.dimensions[0]
  return {
    query: {
      dataset: dataset.name,
      dimensions: firstCategorical ? [{ field: firstCategorical.name }] : [],
      measures: dataset.measures.slice(0, 1).map((m) => m.name),
      filters: [],
    },
    chart: { type: 'bar' },
  }
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2">
      <Label className="text-xs uppercase tracking-wide text-muted-foreground">{label}</Label>
      <div className="space-y-2">{children}</div>
    </div>
  )
}

function RemoveButton({ onClick }: { onClick: () => void }) {
  return (
    <Button variant="ghost" size="icon" className="h-9 w-9 shrink-0" onClick={onClick} aria-label="Remove">
      <X className="h-4 w-4" />
    </Button>
  )
}

function DimensionRow({
  dataset,
  value,
  onChange,
  onRemove,
}: {
  dataset: DatasetInfo
  value: DimensionRef
  onChange: (d: DimensionRef) => void
  onRemove: () => void
}) {
  const kind = dataset.dimensions.find((d) => d.name === value.field)?.kind
  return (
    <div className="flex gap-1">
      <Select value={value.field} onValueChange={(field) => onChange({ field })}>
        <SelectTrigger className="min-w-0 flex-1">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {dataset.dimensions.map((d) => (
            <SelectItem key={d.name} value={d.name}>
              {d.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {kind === 'temporal' && (
        <Select
          value={value.grain ?? NO_GRAIN}
          onValueChange={(g) => onChange({ ...value, grain: g === NO_GRAIN ? null : (g as DimensionRef['grain']) })}
        >
          <SelectTrigger className="w-28">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={NO_GRAIN}>exact</SelectItem>
            {GRAINS.map((g) => (
              <SelectItem key={g} value={g}>
                by {g}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
      <RemoveButton onClick={onRemove} />
    </div>
  )
}

function FilterRow({
  dataset,
  value,
  onChange,
  onRemove,
}: {
  dataset: DatasetInfo
  value: Filter
  onChange: (f: Filter) => void
  onRemove: () => void
}) {
  const kind = dataset.dimensions.find((d) => d.name === value.field)?.kind
  const ops = FILTER_OPS.filter((o) => (o.value === 'relative' ? kind === 'temporal' : true))
  const text = Array.isArray(value.value) ? value.value.join(', ') : String(value.value ?? '')

  return (
    <div className="flex flex-wrap gap-1 rounded-md border p-1">
      <Select value={value.field} onValueChange={(field) => onChange({ field, op: 'eq', value: '' })}>
        <SelectTrigger className="min-w-0 flex-1">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {dataset.dimensions.map((d) => (
            <SelectItem key={d.name} value={d.name}>
              {d.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select
        value={value.op}
        onValueChange={(op) => onChange({ ...value, op: op as Filter['op'], value: op === 'relative' ? 'last_n_days:30' : '' })}
      >
        <SelectTrigger className="w-28">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {ops.map((o) => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <RemoveButton onClick={onRemove} />
      {value.op === 'relative' ? (
        <Select value={String(value.value)} onValueChange={(v) => onChange({ ...value, value: v })}>
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PERIODS.map((p) => (
              <SelectItem key={p} value={p}>
                {p.replaceAll('_', ' ').replace(':', ' ')}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      ) : (
        <Input
          className="w-full"
          value={text}
          type={kind === 'temporal' ? 'date' : 'text'}
          placeholder={value.op === 'in' ? 'a, b, c' : 'value'}
          onChange={(e) => {
            const raw = e.target.value
            const parsed =
              value.op === 'in'
                ? raw.split(',').map((s) => s.trim()).filter(Boolean)
                : kind === 'numeric' && raw !== '' && !Number.isNaN(Number(raw))
                  ? Number(raw)
                  : raw
            onChange({ ...value, value: parsed })
          }}
        />
      )}
    </div>
  )
}
