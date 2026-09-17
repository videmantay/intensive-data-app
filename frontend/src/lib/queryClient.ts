import { MutationCache, QueryClient } from '@tanstack/react-query'

export const queryClient: QueryClient = new QueryClient({
  // Simple rule: after any successful create/update/delete, refetch whatever data is
  // on screen. Queries that aren't currently displayed are just marked stale.
  mutationCache: new MutationCache({
    onSuccess: () => queryClient.invalidateQueries(),
  }),
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
})
