# Choosing a chart

Pick by the shape of the result, not for variety. `make_chart` applies these same
rules (app/analytics/recommend.py), so when you leave `chart_type` empty you get the
"Best" column. Keep this table and recommend.py in step.

| Result shape | Best | Also fine |
|---|---|---|
| Totals, no grouping (1-4 measures) | kpi | table |
| 1 categorical dimension + 1 measure, up to 15 values | bar, sorted largest first | donut (up to 7 slices), treemap |
| ... more than 15 values | bar of the top 15, the rest folded into "Other" | treemap |
| 1 time dimension (with a grain) + measure(s) | line | area; bar if 12 periods or fewer |
| time + 1 categorical dimension + 1 measure, up to 7 groups | line, one per group | area (stacked) |
| ... more than 7 groups | heatmap | line of the top 7 + Other |
| 2 categorical dimensions + 1 measure, one of them up to 7 values | bar, stacked or grouped | heatmap |
| ... both with many values | heatmap | table |
| 1 categorical dimension + 2 measures, more than 5 values | scatter (one measure against the other) | grouped bar |
| 1 categorical dimension + 3-8 measures, up to 5 values | grouped bar | radar |
| raw values of one numeric field (no measure) | histogram | box |
| raw numeric field split by a category (no measure) | box | histogram |
| ordered stages (the user says it's a pipeline/funnel) | funnel | bar |
| detail rows, exact lookups, 3+ dimensions | table | — |

## Time

- Group time with a grain: `{"field": "created_at", "grain": "week"}`. Use day for up
  to a month, week for up to about 6 months, month beyond that.
- Filter with relative periods (`{"op": "relative", "value": "last_week"}`), not
  literal dates, so a pinned chart keeps meaning "last week". Periods: today, yesterday,
  this_week, last_week, this_month, last_month, this_quarter, last_quarter, this_year,
  last_year, ytd, last_n_days:N, last_n_weeks:N, last_n_months:N. Weeks start Monday.

## When the user asks for a specific chart type

1. Call `make_chart` with that `chart_type`.
2. If `requested_feasible` is true and `recommended` is the same type: just show it.
3. If `requested_feasible` is true but `recommended` differs: show theirs, then add ONE
   sentence, e.g. "A bar chart would show this more clearly because {recommended_reason}.
   Want me to switch?" Don't lecture, and don't switch on your own.
4. If `requested_feasible` is false, the recommended chart was drawn instead. Say why in
   one sentence using `requested_note`, and offer what would make their type possible
   (e.g. "a line needs a time axis; I can chart this by week if you like").

## Always

- Sort bars by value unless the axis is time or has a natural order.
- Keep to 7 colors; more groups get folded into "Other". Don't split into more series
  than the question needs.
- Use one measure per axis. Never propose a dual-axis chart; use two charts instead.
- Don't ask for pie charts of more than 7 slices, or of values that don't add up to a
  meaningful whole.
