import { useEffect, useRef } from 'react'
import type { PlotlyFigure } from '@/api/generated'
import { useTheme } from '@/lib/theme'
import { cn } from '@/lib/utils'

/**
 * Renders a Plotly figure built by the backend (`figure_response(fig)` in Python).
 * Plotly is large, so it is downloaded only when a chart is first shown.
 */
export function PlotlyChart({ figure, className }: { figure: PlotlyFigure; className?: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const { theme } = useTheme()

  useEffect(() => {
    const el = ref.current
    if (!el) return
    let cancelled = false

    import('plotly.js-dist-min').then(({ default: Plotly }) => {
      if (cancelled) return
      // Plotly writes into the objects it is given, so hand it a copy of the cached data
      const { data, layout } = structuredClone(figure)
      const text = getComputedStyle(el).color
      const grid = theme === 'dark' ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.1)'
      const axis = (a: unknown) => ({ ...(a as object), gridcolor: grid, zerolinecolor: grid })

      Plotly.react(
        el,
        data,
        {
          ...layout,
          autosize: true,
          paper_bgcolor: 'rgba(0,0,0,0)',
          plot_bgcolor: 'rgba(0,0,0,0)',
          font: { ...(layout.font as object), color: text },
          xaxis: axis(layout.xaxis),
          yaxis: axis(layout.yaxis),
        },
        { responsive: true, displaylogo: false },
      )
    })

    return () => {
      cancelled = true
    }
  }, [figure, theme])

  useEffect(() => {
    const el = ref.current
    return () => {
      if (el) import('plotly.js-dist-min').then(({ default: Plotly }) => Plotly.purge(el))
    }
  }, [])

  return <div ref={ref} className={cn('h-[400px] w-full', className)} />
}
