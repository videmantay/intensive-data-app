import { defineConfig } from '@hey-api/openapi-ts'

// Generates a typed API client + TanStack Query helpers from the FastAPI schema.
// Run `npm run gen:api` after changing backend endpoints or Pydantic models.
export default defineConfig({
  input: './openapi.json',
  output: 'src/api/generated',
  plugins: ['@hey-api/client-fetch', '@tanstack/react-query'],
})
