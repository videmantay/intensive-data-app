import { createFileRoute } from '@tanstack/react-router'
import {
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
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'

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

function ForaInputPage() {
  const [rows, setRows] = useState<FormRow[]>(() => [emptyRow(), emptyRow(), emptyRow(), emptyRow()])
  const [approveMode, setApproveMode] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [status, setStatus] = useState<{ type: 'ok' | 'warn'; text: string } | null>(null)

  const update = <K extends keyof FormRow>(id: string, field: K, value: FormRow[K]) =>
    setRows((rs) => rs.map((r) => (r.id === id ? { ...r, [field]: value } : r)))

  const addRow = () => setRows((rs) => [...rs, emptyRow()])
  const removeRow = (id: string) => setRows((rs) => (rs.length > 1 ? rs.filter((r) => r.id !== id) : rs))
  const removeLast = () => setRows((rs) => (rs.length > 1 ? rs.slice(0, -1) : rs))

  const rowFilled = (r: FormRow) => r.statusType && r.location && r.riskColor && r.trend

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

      {/* Data table */}
      <Card className="mt-4 overflow-hidden">
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted hover:bg-muted">
                  <TableHead className="min-w-[150px]">Status Type</TableHead>
                  <TableHead className="min-w-[150px]">Location</TableHead>
                  <TableHead className="min-w-[140px]">Risk Color</TableHead>
                  <TableHead className="min-w-[150px]">Trend</TableHead>
                  <TableHead className="min-w-[220px]">Comments</TableHead>
                  <TableHead className="min-w-[130px]">User</TableHead>
                  {approveMode && <TableHead className="w-[90px] text-center">Approve</TableHead>}
                  <TableHead className="w-[52px]" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((row) => {
                  const rm = row.riskColor ? riskMeta(row.riskColor) : undefined
                  const tm = row.trend ? trendMeta(row.trend) : undefined
                  return (
                    <TableRow key={row.id}>
                      {/* Status Type */}
                      <TableCell>
                        <Select value={row.statusType} onValueChange={(v) => update(row.id, 'statusType', v)}>
                          <SelectTrigger>
                            <SelectValue placeholder="Select" />
                          </SelectTrigger>
                          <SelectContent>
                            {STATUS_OPTIONS.map((o) => (
                              <SelectItem key={o} value={o}>
                                {o}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </TableCell>

                      {/* Location */}
                      <TableCell>
                        <Select value={row.location} onValueChange={(v) => update(row.id, 'location', v)}>
                          <SelectTrigger>
                            <SelectValue placeholder="Select" />
                          </SelectTrigger>
                          <SelectContent>
                            {LOCATION_OPTIONS.map((o) => (
                              <SelectItem key={o} value={o}>
                                {o}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </TableCell>

                      {/* Risk Color */}
                      <TableCell>
                        <Select value={row.riskColor} onValueChange={(v: Risk) => update(row.id, 'riskColor', v)}>
                          <SelectTrigger>
                            <SelectValue placeholder="Select">
                              {rm && (
                                <span className="flex items-center gap-2">
                                  <RiskDot color={rm.color} />
                                  {rm.label}
                                </span>
                              )}
                            </SelectValue>
                          </SelectTrigger>
                          <SelectContent>
                            {RISK_OPTIONS.map((o) => (
                              <SelectItem key={o.value} value={o.value}>
                                <span className="flex items-center gap-2">
                                  <RiskDot color={o.color} />
                                  {o.label}
                                </span>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </TableCell>

                      {/* Trend */}
                      <TableCell>
                        <Select value={row.trend} onValueChange={(v: Trend) => update(row.id, 'trend', v)}>
                          <SelectTrigger>
                            <SelectValue placeholder="Select">
                              {tm && (
                                <span className="flex items-center gap-2">
                                  <tm.Icon className="h-4 w-4" style={{ color: tm.color }} />
                                  {tm.label}
                                </span>
                              )}
                            </SelectValue>
                          </SelectTrigger>
                          <SelectContent>
                            {TREND_OPTIONS.map((o) => (
                              <SelectItem key={o.value} value={o.value}>
                                <span className="flex items-center gap-2">
                                  <o.Icon className="h-4 w-4" style={{ color: o.color }} />
                                  {o.label}
                                </span>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </TableCell>

                      {/* Comments */}
                      <TableCell>
                        <Textarea
                          value={row.comments}
                          onChange={(e) => update(row.id, 'comments', e.target.value)}
                          placeholder="Add a note"
                          rows={1}
                          className="min-h-9 resize-none"
                        />
                      </TableCell>

                      {/* User */}
                      <TableCell>
                        <Input
                          value={row.user}
                          onChange={(e) => update(row.id, 'user', e.target.value)}
                          placeholder="username"
                        />
                      </TableCell>

                      {/* Approve */}
                      {approveMode && (
                        <TableCell className="text-center">
                          <Checkbox
                            checked={row.approved}
                            onCheckedChange={(v) => update(row.id, 'approved', Boolean(v))}
                            aria-label="Approve record"
                          />
                        </TableCell>
                      )}

                      {/* Delete */}
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-muted-foreground hover:text-red-600"
                          onClick={() => removeRow(row.id)}
                          disabled={rows.length <= 1}
                          aria-label="Delete row"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

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
