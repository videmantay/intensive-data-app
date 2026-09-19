import { useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'

/** Asks for a name (new dashboard, rename). */
export function NameDialog({
  open,
  onOpenChange,
  title,
  initial = '',
  submitLabel = 'Save',
  onSubmit,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: string
  initial?: string
  submitLabel?: string
  onSubmit: (name: string) => void
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        {open && <NameForm title={title} initial={initial} submitLabel={submitLabel} onSubmit={onSubmit} />}
      </DialogContent>
    </Dialog>
  )
}

function NameForm({
  title,
  initial,
  submitLabel,
  onSubmit,
}: {
  title: string
  initial: string
  submitLabel: string
  onSubmit: (name: string) => void
}) {
  const [name, setName] = useState(initial)
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (name.trim()) onSubmit(name.trim())
  }
  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <DialogHeader>
        <DialogTitle>{title}</DialogTitle>
      </DialogHeader>
      <Input autoFocus value={name} maxLength={100} onChange={(e) => setName(e.target.value)} placeholder="Name" />
      <DialogFooter>
        <Button type="submit" disabled={!name.trim()}>
          {submitLabel}
        </Button>
      </DialogFooter>
    </form>
  )
}
