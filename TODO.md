# FieldOps TODO

Working agreement: **read this file before deciding how to proceed on any change**, and
update it as part of the work: add what you discover, and when an item is finished, **move
it to [DONE.md](DONE.md)** (dated, newest first) rather than ticking it here. Keep this file
to open work only. Newest decisions win; if something here contradicts the code, trust the
code and fix the entry.

Status key: `[ ]` open · `[~]` in progress

---

## Bugs (from the audit of `main...feature/explorer`, 2026-10-15)

- [ ] **Dependencies for auth were removed from `pyproject.toml`.** `backend/pyproject.toml:8`
  A staged edit dropped `pwdlib[argon2]` and `itsdangerous`, and `uv.lock` was regenerated
  without them. `app/auth/service.py` imports `pwdlib`; Starlette's `SessionMiddleware`
  (`app/main.py`) requires `itsdangerous`. A fresh `uv sync` on any other machine yields an
  app that won't import — this only passes here because the existing `.venv` still has the
  old wheels. The same edit adds `bleach>=6.0`, which nothing imports.
  *Fix:* put both back (with their comments), re-lock, then `uv sync` and run the tests.
  Decide whether `bleach` is wanted; drop it if it was accidental.

- [ ] **`evals/charting.py` crashes before the first case.** `backend/evals/charting.py:73`
  `user.id` is read after the `with Session(...)` block closes, so SQLAlchemy raises
  `DetachedInstanceError` (`expire_on_commit` is the default here).
  *Fix:* capture `user_id = user.id` inside the block.

- [ ] **One chart color has no dark-mode step.** `frontend/src/components/PlotlyChart.tsx:8`
  `DARK_STEPS` maps 7 of the 8 colors in `render.py`'s `SERIES`; `#008300` (green, slot 6)
  falls through, so a chart with 6+ series shows one dark-green series on a dark background.
  *Fix:* add the slot-6 entry, or drop the color from `SERIES`. These two lists must stay in
  step — `render.py`'s docstring says so.

- [ ] **Multi-measure bars skip the "Other" fold.** `backend/app/analytics/render.py:86`
  A multi-measure bar sets `color` to the synthetic `"measure"` column, which makes the
  `_is_categorical(p, x) and not color` guard false, so the MAX_BARS top-15 fold never runs:
  29 categories draw 29 bars per measure. The single-measure version of the same query folds
  correctly.
  *Fix:* fold on `x` before melting, or test the x-column kind rather than "no color".

- [ ] **`_fold` can emit several "Other" rows.** `backend/app/analytics/render.py:67`
  It groups by every column except the value column, so when `chart.y` is a strict subset of
  `query.measures`, the unused measure acts as a grouping key and "Other" splits into one row
  per distinct value of it.
  *Fix:* group only by the dimension columns in play.

## Unverified / gaps

- [ ] **HANA has never been exercised.** `time_bucket` (`app/analytics/query.py`) is the only
  per-dialect SQL. Run the analytics tests once with `DB_BACKEND=hana` before trusting it.
- [ ] **No OpenAI key configured here, so prompts are untested against a real model.** With a
  key set, run `uv run python -m evals.charting` (after fixing the crash above) and tune
  `app/assistant/prompts.py` / `app/assistant/skills/charting.md` from the results.
- [ ] **Assistant API routes still answer** even though the UI is hidden. Decide whether to
  gate the assistant router in `app/main.py` behind a setting.
- [ ] **`items` is the only dataset.** Time-series and "who did it" questions have nothing to
  show until a second dataset (e.g. shipments) exists — see `.claude/skills/add-dataset`.

- [ ] **FORA page has no backend.** `frontend/src/routes/fora.tsx` keeps rows in `useState`
  and Submit only shows a message. Needs a `fora` feature (models, service, router) following
  `items`; the dropdown lists (status, locations) should then come from the API, and the
  backend should validate values (all cells are plain strings for now).

- [ ] **Docs site not yet run on GitLab.** `origin` is still GitHub, which ignores
  `.gitlab-ci.yml`. After pushing to GitLab, check the first `pages` run and the URL under
  Deploy → Pages, and that runners can reach PyPI (or point pip at the internal mirror).
- [ ] **Material for MkDocs is in maintenance mode** and MkDocs 2.0 drops hooks. Fine while
  pinned (`docs/requirements.txt`); revisit if a 1.x security fix stops coming.

## Decisions pending

- [ ] Dashboards and chats created while signed in as a real user (e.g. `lee`) are invisible
  to the demo user, since they belong to that account. Decide whether to reassign them to the
  demo user in existing databases, or start fresh.
- [ ] Keep the agent hidden, or re-enable it? Un-hiding = revert the redirect in
  `frontend/src/routes/explore.tsx` and the commented block in `frontend/src/routes/__root.tsx`.
- [ ] Tag a course snapshot for the spring course (e.g. `git tag course-2026-spring`) so the
  teaching version is frozen without maintaining a second frontend.
- [ ] Separate repo: migrate RTK → TanStack Query incrementally (pilot one screen first).
  Mantine → shadcn is a separate, later call.

## Housekeeping

- [ ] `C:\Users\videm\OneDrive\Desktop\LM-Mock\` holds an orphaned `backend/.venv` and no
  code; deleting it stops shells picking up the wrong `VIRTUAL_ENV`.
