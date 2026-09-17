import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { createRootRoute, Link, Outlet } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools'
import { MessageSquare } from 'lucide-react'
import { useState } from 'react'
import { AssistantPanel } from '@/components/assistant/AssistantPanel'
import { Button } from '@/components/ui/button'
import { useTheme } from '@/lib/theme'

export const Route = createRootRoute({
  component: RootLayout,
})

function RootLayout() {
  const { theme, toggleTheme } = useTheme()
  const [assistantOpen, setAssistantOpen] = useState(false)

  return (
    <div className="flex h-svh flex-col bg-background text-foreground">
      <header className="border-b">
        <nav className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3">
          <span className="font-semibold">FieldOps</span>
          <Link to="/" className="text-sm [&.active]:font-semibold">
            Dashboard
          </Link>
          <Link to="/items" className="text-sm [&.active]:font-semibold">
            Items
          </Link>
          <Link to="/fora" className="text-sm [&.active]:font-semibold">
            FORA
          </Link>
          <div className="ml-auto flex items-center gap-2">
            <Button variant="outline" size="sm" className="gap-2" onClick={() => setAssistantOpen((o) => !o)}>
              <MessageSquare className="h-4 w-4" />
              Assistant
            </Button>
            <Button variant="outline" size="sm" onClick={toggleTheme}>
              {theme === 'light' ? 'Dark' : 'Light'} mode
            </Button>
          </div>
        </nav>
      </header>

      <div className="flex min-h-0 flex-1">
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-6xl px-4 py-6">
            <Outlet />
          </div>
        </main>
        {assistantOpen && (
          <div className="w-[380px] shrink-0">
            <AssistantPanel onClose={() => setAssistantOpen(false)} />
          </div>
        )}
      </div>

      {import.meta.env.DEV && (
        <>
          <TanStackRouterDevtools position="bottom-left" />
          <ReactQueryDevtools buttonPosition="bottom-right" />
        </>
      )}
    </div>
  )
}
