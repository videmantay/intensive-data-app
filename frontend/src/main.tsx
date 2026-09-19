import { QueryClientProvider } from '@tanstack/react-query'
import { createRouter, RouterProvider } from '@tanstack/react-router'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { client } from '@/api/generated/client.gen'
import { queryClient } from '@/lib/queryClient'
import { ThemeProvider } from '@/lib/theme'
import './index.css'
import { routeTree } from './routeTree.gen'

const router = createRouter({ routeTree })

// If the session expires mid-use, any API call returns 401: go to the sign-in page
client.interceptors.response.use((response) => {
  const { pathname, href } = router.state.location
  if (response.status === 401 && pathname !== '/login') {
    queryClient.clear()
    router.navigate({ to: '/login', search: { redirect: href } })
  }
  return response
})

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <RouterProvider router={router} />
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>,
)
