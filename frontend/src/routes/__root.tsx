import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { createRootRoute, Link, Outlet } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools'
import { Button } from '@/components/ui/button'
import { useTheme } from '@/lib/theme'

export const Route = createRootRoute({
  // Login is bypassed for the demo: the API treats anonymous requests as a demo user
  // (backend/app/auth/deps.py). To require sign-in again, restore the beforeLoad guard
  // from git history and the /login route.
  component: AppLayout,
})

/**
 * The assistant is hidden for now: no Explore link, no Assistant button, no side panel.
 * Nothing was deleted. To bring it back, restore in this file:
 *   - `const [assistantOpen, setAssistantOpen] = useState(false)`
 *   - the header Button that toggles it (MessageSquare icon)
 *   - `{assistantOpen && <div className="w-[380px] shrink-0"><AssistantPanel onClose={...} /></div>}`
 *   - the <Link to="/explore"> nav entry
 * and drop the redirect in routes/explore.tsx.
 */
function AppLayout() {
  const { theme, toggleTheme } = useTheme()

  return (
    <div className="flex h-svh flex-col bg-background text-foreground">
      <header className="border-b">
        <nav className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3">
          <span className="font-semibold">FieldOps</span>
          <Link to="/" className="text-sm [&.active]:font-semibold">
            Dashboard
          </Link>
          {/* Explore (the full-page agent view) is hidden for now; the route still
              works at /explore. Put this link back to show it again. */}
          <Link to="/items" className="text-sm [&.active]:font-semibold">
            Items
          </Link>
          <Link to="/fora" className="text-sm [&.active]:font-semibold">
            FORA
          </Link>
          <div className="ml-auto flex items-center gap-2">
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
