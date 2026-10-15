# FieldOps DONE

Finished items moved out of [TODO.md](TODO.md) so that file stays short. Newest first.
Each entry keeps its date and enough detail to find the change again. Nobody needs to read
this before starting work; search it when you need the history of a decision.

---

## 2026-10-15

- [x] **Developer docs site on GitLab Pages.** `mkdocs.yml` + `docs/` (MkDocs, Material theme)
  publish `DEV.md` and a best-practices link page per library (`docs/libraries.md`).
  `docs/hooks.py` pulls in the root `DEV.md` and points its code links at the GitLab repo, so
  there is only one copy. `.gitlab-ci.yml`: `pages` deploys on the default branch; `docs`
  builds with `--strict` on merge requests. MkDocs is pinned below 2.0, which drops hooks.
- [x] **FORA input page is an AG Grid sheet.** `frontend/src/routes/fora.tsx` uses `<DataGrid>`
  instead of a table of shadcn inputs. Columns with a fixed list of values open a dropdown on
  one click: status and location use `agSelectCellEditor` (`dropdown()`); risk and trend use a
  small React editor, `IconListEditor` (`iconDropdown()`), because the built-in one can only
  show text and the list needs the risk dots and trend icons;
  other columns take free text (comments use the large-text popup). Edits go through
  `onCellEditRequest` into local state, since there is no FORA backend yet.
- [x] **Developer docs for dashboards and datasets.** Added `DEV.md`, linked from README and
  CLAUDE.md. Update it when `app/analytics/` or `app/dashboards/` change shape.
- [x] **Login for the demo: bypassed.** Anonymous requests act as a built-in demo user
  (`app/auth/service.py: demo_user`). The auth code, the users table and per-user scoping all
  stay; README "Sign-in (bypassed for the demo)" explains how to turn it back on.
- [x] **Audit of `main...feature/explorer`: checked, no action needed.** Owner scoping on
  dashboards, widgets and threads (including the cross-dashboard layout attack), "client
  history is ignored" in the chat endpoint, `time_bucket` on all five grains, relative-period
  math including year wrap, middleware order, react-grid-layout v2 API use, and
  OpenAPI/client drift. Open bugs from the same audit are in TODO.md.
