import { useMutation, useQuery } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { createRootRoute, Link, Outlet, redirect, useNavigate, useRouterState } from '@tanstack/react-router'
import { TanStackRouterDevtools } from '@tanstack/react-router-devtools'
import { LogOut, MessageSquare } from 'lucide-react'
import { useState } from 'react'
import { currentUserOptions, logoutMutation } from '@/api/generated/@tanstack/react-query.gen'
import { AssistantPanel } from '@/components/assistant/AssistantPanel'
import { Button } from '@/components/ui/button'
import { queryClient } from '@/lib/queryClient'
import { useTheme } from '@/lib/theme'

export const Route = createRootRoute({
  // Every page except /login needs a signed-in user
  beforeLoad: async ({ location }) => {
    if (location.pathname === '/login') return
    try {
      await queryClient.ensureQueryData(currentUserOptions())
    } catch {
      throw redirect({ to: '/login', search: { redirect: location.href } })
    }
  },
  component: RootLayout,
})

function RootLayout() {
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  if (pathname === '/login') return <Outlet />
  return <AppLayout />
}

function AppLayout() {
  const { theme, toggleTheme } = useTheme()
  const [assistantOpen, setAssistantOpen] = useState(false)
  const user = useQuery(currentUserOptions())
  const navigate = useNavigate()
  const logout = useMutation({
    ...logoutMutation(),
    onSuccess: () => {
      queryClient.clear()
      navigate({ to: '/login' })
    },
  })

  return (
    <div className="flex h-svh flex-col bg-background text-foreground">
      <header className="border-b">
        <nav className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3">
          <span className="font-semibold">FieldOps</span>
          <Link to="/" className="text-sm [&.active]:font-semibold">
            Dashboard
          </Link>
          <Link to="/explore" className="text-sm [&.active]:font-semibold">
            Explore
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
            {user.data && <span className="text-sm text-muted-foreground">{user.data.display_name}</span>}
            <Button variant="ghost" size="icon" onClick={() => logout.mutate({})} aria-label="Sign out">
              <LogOut className="h-4 w-4" />
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
