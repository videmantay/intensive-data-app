# FieldOps developer docs

FieldOps is a FastAPI + React data app that replaces a Streamlit app. The rule of thumb:
**logic stays in Python** (queries, calculations, Plotly charts), and the frontend fetches and
displays.

- **[Developer guide](dev.md)**: how a database table becomes a chart on a dashboard, and how
  to make a new table explorable.
- **[Library best practices](libraries.md)**: the official guidance for each library the app
  is built on, and how this codebase applies it.

For running the app and the step-by-step "add a feature" recipe, see `README.md` and
`CLAUDE.md` in the repository.

!!! note "How this site is built"
    Every commit to the default branch rebuilds it (the `pages` job in `.gitlab-ci.yml`).
    The developer guide is the repo's `DEV.md`; edit it there, not here. The other pages
    live in `docs/`.
