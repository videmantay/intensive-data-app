import { useQuery } from '@tanstack/react-query'
import { createFileRoute } from '@tanstack/react-router'
import { healthOptions, itemQuantityChartOptions } from '@/api/generated/@tanstack/react-query.gen'
import { PlotlyChart } from '@/components/PlotlyChart'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export const Route = createFileRoute('/')({
  component: DashboardPage,
})

function DashboardPage() {
  const health = useQuery(healthOptions())
  const chart = useQuery(itemQuantityChartOptions())

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <h1 className="mr-auto text-2xl font-semibold">Dashboard</h1>
        {health.isPending && <Badge variant="secondary">Checking API…</Badge>}
        {health.isError && <Badge variant="destructive">API unreachable</Badge>}
        {health.data && <Badge variant="outline">DB: {health.data.database}</Badge>}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Inventory</CardTitle>
        </CardHeader>
        <CardContent>
          {chart.isPending && <p className="text-muted-foreground">Loading chart…</p>}
          {chart.isError && <p className="text-destructive">Failed to load chart.</p>}
          {chart.data && <PlotlyChart figure={chart.data} />}
        </CardContent>
      </Card>
    </div>
  )
}
