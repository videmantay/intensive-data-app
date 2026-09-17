import { AllCommunityModule, colorSchemeVariable, ModuleRegistry, themeQuartz } from 'ag-grid-community'
import { AgGridReact, type AgGridReactProps } from 'ag-grid-react'

ModuleRegistry.registerModules([AllCommunityModule])

// Follows the app's light/dark mode via the data-ag-theme-mode attribute set in ThemeProvider
const gridTheme = themeQuartz.withPart(colorSchemeVariable).withParams({ fontFamily: 'inherit' })

type DataGridProps<T> = AgGridReactProps<T> & {
  height?: number | string
}

/**
 * App-wide AG Grid wrapper with shared defaults. Pass normal AG Grid props.
 *
 * Editing: the grid never changes row data itself (`readOnlyEdit`). Handle
 * `onCellEditRequest` by saving to the API; the refetched data then flows back in.
 */
export function DataGrid<T>({ height = 500, defaultColDef, ...props }: DataGridProps<T>) {
  return (
    <div style={{ height }}>
      <AgGridReact<T>
        theme={gridTheme}
        readOnlyEdit
        defaultColDef={{ sortable: true, filter: true, resizable: true, ...defaultColDef }}
        {...props}
      />
    </div>
  )
}
