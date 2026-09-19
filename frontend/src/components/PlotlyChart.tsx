import { useEffect, useRef } from 'react'
import type { PlotlyFigure } from '@/api/generated'
import { useTheme } from '@/lib/theme'
import { cn } from '@/lib/utils'

// The backend draws with the light-mode palette (app/analytics/render.py). In dark
// mode each color is swapped for the same hue stepped for a dark background.
const DARK_STEPS: Record<string, string> = {
  '#2a78d6': '#3987e5',
  '#eb6834': '#d95926',
  '#1baf7a': '#199e70',
  '#eda100': '#c98500',
  '#e87ba4': '#d55181',
  '#4a3aa7': '#9085e9',
  '#e34948': '#e66767',
}

function toDark(value: unknown): unknown {
  if (typeof value === 'string') return DARK_STEPS[value.toLowerCase()] ?? value
  if (Array.isArray(value)) return value.map(toDark)
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, toDark(v)]))
  }
  return value
}

/**
 * Renders a Plotly figure built by the backend (`figure_response(fig)` in Python).
 * Plotly is large, so it is downloaded only when a chart is first shown. The chart
 * fills its container and redraws when the container is resized (e.g. a dashboard tile).
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
      const copy = structuredClone(figure)
      const { data, layout } = theme === 'dark' ? (toDark(copy) as PlotlyFigure) : copy
      const text = getComputedStyle(el).color
      const grid = theme === 'dark' ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.1)'
      const axis = (a: unknown) => ({ ...(a as object), gridcolor: grid, zerolinecolor: grid, linecolor: grid })
      const polar = layout.polar as Record<string, unknown> | undefined

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
          ...(polar && {
            polar: {
              ...polar,
              bgcolor: 'rgba(0,0,0,0)',
              radialaxis: axis(polar.radialaxis),
              angularaxis: axis(polar.angularaxis),
            },
          }),
        },
        { responsive: true, displaylogo: false },
      )
    })

    return () => {
      cancelled = true
    }
  }, [figure, theme])

  // Plotly's `responsive` only follows window resizes; dashboard tiles resize on their own
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const observer = new ResizeObserver(() => {
      if (el.querySelector('.plot-container')) {
        import('plotly.js-dist-min').then(({ default: Plotly }) => Plotly.Plots.resize(el))
      }
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  // Free Plotly's memory on unmount. The purge happens after an async import, so skip
  // it if the component was mounted again meanwhile (React StrictMode does exactly that
  // in development), or it would wipe the freshly drawn chart.
  const mounted = useRef(false)
  useEffect(() => {
    const el = ref.current
    mounted.current = true
    return () => {
      mounted.current = false
      if (el) {
        import('plotly.js-dist-min').then(({ default: Plotly }) => {
          if (!mounted.current) Plotly.purge(el)
        })
      }
    }
  }, [])

  return <div ref={ref} className={cn('h-[400px] w-full', className)} />
}
