import { useMutation } from '@tanstack/react-query'
import { useMemo } from 'react'
import ReactGridLayout, { useContainerWidth, type Layout } from 'react-grid-layout'
import 'react-grid-layout/css/styles.css'
import type { WidgetPublic } from '@/api/generated'
import { saveDashboardLayoutMutation } from '@/api/generated/@tanstack/react-query.gen'
import { DRAG_HANDLE, WidgetCard } from '@/components/dashboard/WidgetCard'

const COLS = 12
const ROW_HEIGHT = 40 // px per grid row; a widget's `h` is in rows
const NARROW = 700 // below this width, tiles stack in one column

/**
 * Dashboard tiles on a 12-column grid. In edit mode, tiles can be dragged by their
 * title bar and resized from the corner; the new positions are saved when you let go.
 */
export function DashboardGrid({
  dashboardId,
  widgets,
  editing,
}: {
  dashboardId: number
  widgets: WidgetPublic[]
  editing: boolean
}) {
  const { width, containerRef, mounted } = useContainerWidth()
  const saveLayout = useMutation(saveDashboardLayoutMutation())

  const layout = useMemo(
    () => widgets.map((w) => ({ i: String(w.id), x: w.x, y: w.y, w: w.w, h: w.h, minW: 2, minH: 3 })),
    [widgets],
  )

  const save = (next: Layout) =>
    saveLayout.mutate({
      path: { dashboard_id: dashboardId },
      body: next.map((item) => ({ id: Number(item.i), x: item.x, y: item.y, w: item.w, h: item.h })),
    })

  if (mounted && width < NARROW) {
    return (
      <div ref={containerRef} className="space-y-4">
        {widgets.map((w) => (
          <div key={w.id} style={{ height: Math.max(w.h, 6) * ROW_HEIGHT }}>
            <WidgetCard widget={w} editing={false} />
          </div>
        ))}
      </div>
    )
  }

  return (
    <div ref={containerRef}>
      {mounted && (
        <ReactGridLayout
          layout={layout}
          width={width}
          gridConfig={{ cols: COLS, rowHeight: ROW_HEIGHT, margin: [16, 16], containerPadding: [0, 0] }}
          dragConfig={{ enabled: editing, handle: `.${DRAG_HANDLE}` }}
          resizeConfig={{ enabled: editing }}
          onDragStop={save}
          onResizeStop={save}
        >
          {widgets.map((w) => (
            <div key={String(w.id)}>
              <WidgetCard widget={w} editing={editing} />
            </div>
          ))}
        </ReactGridLayout>
      )}
    </div>
  )
}
