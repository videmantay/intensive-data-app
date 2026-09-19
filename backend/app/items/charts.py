"""Plotly charts for items.

Build charts here exactly as you would in Streamlit. Endpoints return them with
`figure_response(fig)` and the frontend's <PlotlyChart> renders them as-is.
"""

import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure
from sqlmodel import Session

from app.items import service


def quantity_by_category(session: Session) -> Figure:
    totals = service.totals_by_category(session)
    df = pd.DataFrame([t.model_dump() for t in totals])
    fig = px.bar(
        df,
        x="category",
        y="total_quantity",
        hover_data=["item_count"],
        labels={"category": "Category", "total_quantity": "Total quantity", "item_count": "Items"},
    )
    fig.update_layout(title="Quantity by category")
    return fig
