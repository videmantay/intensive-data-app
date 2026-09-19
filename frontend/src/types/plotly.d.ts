// Minimal typings for the parts of plotly.js we call. Figures come from the backend
// as JSON, so we don't need Plotly's full type definitions.
declare module 'plotly.js-dist-min' {
  type Obj = Record<string, unknown>

  const Plotly: {
    react(el: HTMLElement, data: Obj[], layout?: Obj, config?: Obj): Promise<HTMLElement>
    purge(el: HTMLElement): void
    Plots: { resize(el: HTMLElement): void }
  }
  export default Plotly
}
