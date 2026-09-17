import { useMutation, useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import type { CellEditRequestEvent, ColDef } from 'ag-grid-community'
import { useState, type FormEvent } from 'react'
import type { Item } from '@/api/generated'
import {
  createItemMutation,
  deleteItemMutation,
  listItemsOptions,
  updateItemMutation,
} from '@/api/generated/@tanstack/react-query.gen'
import { DataGrid } from '@/components/DataGrid'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

export const Route = createFileRoute('/items')({
  component: ItemsPage,
})

function ItemsPage() {
  const items = useQuery(listItemsOptions({ query: { limit: 1000 } }))
  const createItem = useMutation(createItemMutation())
  const updateItem = useMutation(updateItemMutation())
  const deleteItem = useMutation(deleteItemMutation())

  const columns: ColDef<Item>[] = [
    { field: 'id', headerName: 'ID', width: 90 },
    { field: 'name', editable: true, flex: 2 },
    { field: 'category', editable: true, flex: 1 },
    { field: 'description', editable: true, flex: 2 },
    { field: 'quantity', editable: true, width: 130 },
    { field: 'created_at', headerName: 'Created', width: 180, valueFormatter: (p) => formatDate(p.value) },
    {
      headerName: '',
      width: 100,
      sortable: false,
      filter: false,
      cellRenderer: (p: { data: Item }) => (
        <Button variant="ghost" size="sm" onClick={() => deleteItem.mutate({ path: { item_id: p.data.id } })}>
          Delete
        </Button>
      ),
    },
  ]

  // Save an edited cell to the API. The refetched list then updates the grid.
  const handleCellEdit = (event: CellEditRequestEvent<Item>) => {
    const field = event.colDef.field
    if (!field || !event.data) return
    updateItem.mutate({ path: { item_id: event.data.id }, body: { [field]: event.newValue } })
  }

  const error = items.error ?? createItem.error ?? updateItem.error ?? deleteItem.error

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Items</h1>
      <AddItemForm onAdd={(body) => createItem.mutate({ body })} saving={createItem.isPending} />
      {error && <p className="text-destructive">Something went wrong: {errorMessage(error)}</p>}
      <DataGrid<Item>
        rowData={items.data}
        columnDefs={columns}
        getRowId={(p) => String(p.data.id)}
        onCellEditRequest={handleCellEdit}
        loading={items.isPending}
      />
    </div>
  )
}

function AddItemForm({
  onAdd,
  saving,
}: {
  onAdd: (item: { name: string; category: string; quantity: number }) => void
  saving: boolean
}) {
  const [name, setName] = useState('')
  const [category, setCategory] = useState('General')
  const [quantity, setQuantity] = useState('1')

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    onAdd({ name: name.trim(), category: category.trim() || 'General', quantity: Number(quantity) || 0 })
    setName('')
    setQuantity('1')
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap gap-2">
      <Input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} className="max-w-xs" />
      <Input placeholder="Category" value={category} onChange={(e) => setCategory(e.target.value)} className="w-40" />
      <Input type="number" min={0} value={quantity} onChange={(e) => setQuantity(e.target.value)} className="w-24" />
      <Button type="submit" disabled={saving}>
        Add item
      </Button>
    </form>
  )
}

function formatDate(value: string | undefined) {
  return value ? new Date(value + 'Z').toLocaleString() : ''
}

function errorMessage(error: unknown) {
  if (error instanceof Error) return error.message
  return JSON.stringify(error)
}
