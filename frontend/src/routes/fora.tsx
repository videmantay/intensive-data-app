import { createFileRoute } from '@tanstack/react-router'
import type { CustomCellEditorProps } from 'ag-grid-react'
import type { CellEditRequestEvent, ColDef, ICellRendererParams } from 'ag-grid-community'
import {
  ChevronDown,
  CircleCheck,
  Minus,
  MoveRight,
  Plus,
  Search,
  Send,
  ShieldCheck,
  Trash2,
  TrendingDown,
  TrendingUp,
  type LucideIcon,
} from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { DataGrid } from '@/components/DataGrid'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

export const Route = createFileRoute('/fora')({
  component: ForaInputPage,
})

const STATUS_OPTIONS = ['Operational', 'Degraded', 'Offline', 'Maintenance', 'Not Observed']

// Placeholder site list — swap for your real location source.
const LOCATION_OPTIONS = ['North Plant', 'East Yard', 'Riverside Depot', 'Central Warehouse', 'South Campus']

const RISK_OPTIONS = [
  { value: 'green', label: 'Green', color: '#16a34a' },
  { value: 'amber', label: 'Amber', color: '#d97706' },
  { value: 'red', label: 'Red', color: '#dc2626' },
] as const

const TREND_OPTIONS = [
  { value: 'improving', label: 'Improving', Icon: TrendingUp, color: '#16a34a' },
  { value: 'stable', label: 'Stable', Icon: MoveRight, color: '#64748b' },
  { value: 'declining', label: 'Declining', Icon: TrendingDown, color: '#dc2626' },
] as const

type Risk = (typeof RISK_OPTIONS)[number]['value']
type Trend = (typeof TREND_OPTIONS)[number]['value']

interface FormRow {
  id: string
  statusType: string
  location: string
  riskColor: Risk | ''
  trend: Trend | ''
  comments: string
  user: string
  approved: boolean
}

// Sample data for the "See previous records" panel.
const PREVIOUS_RECORDS: { statusType: string; location: string; risk: Risk; trend: Trend; user: string }[] = [
  { statusType: 'Operational', location: 'North Plant', risk: 'green', trend: 'stable', user: 'j.torres' },
  { statusType: 'Degraded', location: 'East Yard', risk: 'amber', trend: 'declining', user: 'a.nguyen' },
  { statusType: 'Maintenance', location: 'Riverside Depot', risk: 'green', trend: 'improving', user: 'r.khan' },
]

let _seq = 0
const nextId = () => `row-${++_seq}`

const emptyRow = (): FormRow => ({
  id: nextId(),
  statusType: '',
  location: '',
  riskColor: '',
  trend: '',
  comments: '',
  user: '',
  approved: false,
})

function RiskDot({ color }: { color: string }) {
  return <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: color }} />
}

const riskMeta = (value: Risk) => RISK_OPTIONS.find((r) => r.value === value)!
const trendMeta = (value: Trend) => TREND_OPTIONS.find((t) => t.value === value)!

/** What a dropdown cell shows: its value (or a "Select" hint) and a chevron, like an Excel list cell. */
function SelectCell({ children }: { children?: ReactNode }) {
  return (
    <span className="flex h-full items-center justify-between gap-2">
      {children ?? <span className="text-muted-foreground">Select</span>}
      <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
    </span>
  )
}

/**
 * A column that edits through a dropdown of `values`. Columns without one take free text.
 * `label` turns a stored value into what the user sees (e.g. 'amber' -> 'Amber').
 */
function dropdown(values: readonly string[], label: (v: string) => string = (v) => v): ColDef<FormRow> {
  return {
    cellEditor: 'agSelectCellEditor',
    cellEditorParams: { values: ['', ...values], formatValue: (v: string) => (v ? label(v) : '—') },
    singleClickEdit: true,
    valueFormatter: (p) => (p.value ? label(p.value) : ''),
  }
}

interface ListOption {
  value: string
  label: string
  icon: ReactNode
}

/**
 * Dropdown editor that shows an icon next to each choice. AG Grid's built-in select editor
 * can only show text. Arrow keys move the choice, Enter or a click picks it, Escape cancels.
 */
function IconListEditor({
  value,
  onValueChange,
  stopEditing,
  options,
}: CustomCellEditorProps<FormRow, string> & { options: ListOption[] }) {
  const choices: ListOption[] = [{ value: '', label: '—', icon: null }, ...options]
  const listRef = useRef<HTMLDivElement>(null)
  useEffect(() => listRef.current?.focus(), [])

  const move = (step: number) => {
    const i = choices.findIndex((o) => o.value === (value ?? ''))
    const next = choices[Math.min(Math.max(i + step, 0), choices.length - 1)]
    onValueChange(next.value)
  }

  return (
    <div
      ref={listRef}
      tabIndex={0}
      role="listbox"
      className="min-w-40 rounded-md border bg-popover p-1 text-popover-foreground shadow-md outline-none"
      onKeyDown={(e) => {
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
          e.preventDefault()
          move(e.key === 'ArrowDown' ? 1 : -1)
        }
      }}
    >
      {choices.map((o) => (
        <div
          key={o.value}
          role="option"
          aria-selected={o.value === (value ?? '')}
          className="flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-accent aria-selected:bg-accent"
          onClick={() => {
            onValueChange(o.value)
            stopEditing()
          }}
        >
          {o.icon}
          <span className={o.value ? undefined : 'text-muted-foreground'}>{o.label}</span>
        </div>
      ))}
    </div>
  )
}

/** Like `dropdown`, but each choice carries an icon, both in the list and in the cell. */
function iconDropdown(options: ListOption[]): ColDef<FormRow> {
  const find = (v: string) => options.find((o) => o.value === v)
  return {
    cellEditor: IconListEditor,
    cellEditorPopup: true,
    cellEditorParams: { options },
    singleClickEdit: true,
    valueFormatter: (p) => find(p.value)?.label ?? '',
    cellRenderer: (p: ICellRendererParams<FormRow>) => {
      const o = find(p.value)
      return (
        <SelectCell>
          {o && (
            <span className="flex items-center gap-2">
              {o.icon}
              {o.label}
            </span>
          )}
        </SelectCell>
      )
    },
  }
}

const RISK_LIST: ListOption[] = RISK_OPTIONS.map((o) => ({ ...o, icon: <RiskDot color={o.color} /> }))
const TREND_LIST: ListOption[] = TREND_OPTIONS.map((o) => ({
  ...o,
  icon: <o.Icon className="h-4 w-4" style={{ color: o.color }} />,
}))

function ForaInputPage() {
  const [rows, setRows] = useState<FormRow[]>(() => [emptyRow(), emptyRow(), emptyRow(), emptyRow()])
  const [approveMode, setApproveMode] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [status, setStatus] = useState<{ type: 'ok' | 'warn'; text: string } | null>(null)

  const addRow = () => setRows((rs) => [...rs, emptyRow()])
  const removeRow = (id: string) => setRows((rs) => (rs.length > 1 ? rs.filter((r) => r.id !== id) : rs))
  const removeLast = () => setRows((rs) => (rs.length > 1 ? rs.slice(0, -1) : rs))

  const rowFilled = (r: FormRow) => r.statusType && r.location && r.riskColor && r.trend

  // The grid never edits rows itself (readOnlyEdit); apply each edit to local state.
  // TODO: send to the backend once the FORA endpoints exist.
  const handleCellEdit = (event: CellEditRequestEvent<FormRow>) => {
    const field = event.colDef.field
    if (!field || !event.data) return
    const id = event.data.id
    setRows((rs) => rs.map((r) => (r.id === id ? { ...r, [field]: event.newValue ?? '' } : r)))
  }

  const columns: ColDef<FormRow>[] = [
    {
      field: 'statusType',
      headerName: 'Status Type',
      minWidth: 160,
      ...dropdown(STATUS_OPTIONS),
      cellRenderer: (p: ICellRendererParams<FormRow>) => <SelectCell>{p.valueFormatted || undefined}</SelectCell>,
    },
    {
      field: 'location',
      minWidth: 170,
      ...dropdown(LOCATION_OPTIONS),
      cellRenderer: (p: ICellRendererParams<FormRow>) => <SelectCell>{p.valueFormatted || undefined}</SelectCell>,
    },
    {
      field: 'riskColor',
      headerName: 'Risk Color',
      minWidth: 140,
      ...iconDropdown(RISK_LIST),
    },
    {
      field: 'trend',
      minWidth: 150,
      ...iconDropdown(TREND_LIST),
    },
    // Free-text cells: type to start editing, as in Excel.
    { field: 'comments', flex: 2, minWidth: 220, cellEditor: 'agLargeTextCellEditor', cellEditorPopup: true },
    { field: 'user', minWidth: 130 },
    { field: 'approved', headerName: 'Approve', width: 100, hide: !approveMode },
    {
      headerName: '',
      width: 60,
      editable: false,
      sortable: false,
      filter: false,
      resizable: false,
      cellRenderer: (p: ICellRendererParams<FormRow>) => (
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-muted-foreground hover:text-red-600"
          onClick={() => p.data && removeRow(p.data.id)}
          disabled={rows.length <= 1}
          aria-label="Delete row"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      ),
    },
  ]

  const handleSubmit = () => {
    const ready = rows.filter(rowFilled)
    if (ready.length === 0) {
      setStatus({
        type: 'warn',
        text: 'Add a status, location, risk, and trend to at least one row before submitting.',
      })
      return
    }
    // TODO: POST to the backend once the FORA endpoints exist
    setStatus({
      type: 'ok',
      text: `${ready.length} record${ready.length > 1 ? 's' : ''} submitted for review.`,
    })
  }

  return (
    <div>
      {/* Brand banner */}
      <div className="flex items-center justify-between rounded-lg bg-brand px-6 py-5 text-brand-foreground shadow-sm">
        <div>
          <h1 className="text-xl font-semibold tracking-wide">FORA Input App</h1>
          <p className="text-sm text-slate-300">Field Observation &amp; Risk Assessment</p>
        </div>
        <ShieldCheck className="h-8 w-8 text-slate-200" />
      </div>

      {/* Row controls */}
      <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button onClick={addRow} className="gap-2 bg-brand text-brand-foreground hover:bg-brand/90">
            <Plus className="h-4 w-4" />
            Add data row
          </Button>
          <div className="flex items-center gap-1 rounded-md border bg-background p-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={removeLast}
              disabled={rows.length <= 1}
              aria-label="Remove last row"
            >
              <Minus className="h-4 w-4" />
            </Button>
            <span className="w-10 text-center text-sm font-medium tabular-nums">{rows.length}</span>
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={addRow} aria-label="Add row">
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <span className="text-sm text-muted-foreground">
          {rows.filter(rowFilled).length} of {rows.length} rows ready
        </span>
      </div>

      {/* Data grid: click a list cell to pick from its dropdown; type into a text cell to edit it */}
      <div className="mt-4">
        <DataGrid<FormRow>
          height="auto"
          domLayout="autoHeight"
          rowData={rows}
          columnDefs={columns}
          getRowId={(p) => p.data.id}
          onCellEditRequest={handleCellEdit}
          defaultColDef={{ editable: true, sortable: false, filter: false, flex: 1 }}
          enterNavigatesVertically
          enterNavigatesVerticallyAfterEdit
          stopEditingWhenCellsLoseFocus
          popupParent={document.body}
        />
      </div>

      {/* Submit + status */}
      <div className="mt-4 flex flex-wrap items-center justify-end gap-3">
        {status && (
          <span
            className={`flex items-center gap-2 text-sm ${
              status.type === 'ok' ? 'text-emerald-600' : 'text-amber-600'
            }`}
          >
            <CircleCheck className="h-4 w-4" />
            {status.text}
          </span>
        )}
        <Button onClick={handleSubmit} className="gap-2 bg-brand text-brand-foreground hover:bg-brand/90">
          <Send className="h-4 w-4" />
          Submit for Review
        </Button>
      </div>

      <Separator className="my-8" />

      {/* Workflow toggles */}
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <Switch id="approve" checked={approveMode} onCheckedChange={setApproveMode} />
          <Label htmlFor="approve" className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-emerald-600" />
            Approve records
          </Label>
        </div>

        <div className="flex items-center gap-3">
          <Switch id="history" checked={showHistory} onCheckedChange={setShowHistory} />
          <Label htmlFor="history" className="flex items-center gap-2">
            <Search className="h-4 w-4 text-sky-600" />
            See previous records
          </Label>
        </div>
      </div>

      {/* Previous records panel */}
      {showHistory && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="text-base">Previous records</CardTitle>
          </CardHeader>
          <CardContent>
            <PreviousRecordsTable />
          </CardContent>
        </Card>
      )}

    </div>
  )
}

function PreviousRecordsTable() {
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Status Type</TableHead>
            <TableHead>Location</TableHead>
            <TableHead>Risk</TableHead>
            <TableHead>Trend</TableHead>
            <TableHead>User</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {PREVIOUS_RECORDS.map((r, i) => {
            const rm = riskMeta(r.risk)
            const tm: { Icon: LucideIcon; color: string; label: string } = trendMeta(r.trend)
            return (
              <TableRow key={i}>
                <TableCell>{r.statusType}</TableCell>
                <TableCell>{r.location}</TableCell>
                <TableCell>
                  <span className="flex items-center gap-2">
                    <RiskDot color={rm.color} />
                    {rm.label}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="flex items-center gap-2">
                    <tm.Icon className="h-4 w-4" style={{ color: tm.color }} />
                    {tm.label}
                  </span>
                </TableCell>
                <TableCell className="text-muted-foreground">{r.user}</TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}
