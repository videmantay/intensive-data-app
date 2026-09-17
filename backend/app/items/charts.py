"""Plotly charts for items.

Build charts here exactly as you would in Streamlit. Endpoints return them with
`figure_response(fig)` and the frontend's <PlotlyChart> renders them as-is.
"""

import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure

from app.db.base import Connection
from app.items import service


def quantity_by_category(conn: Connection) -> Figure:
    df = pd.DataFrame(service.totals_by_category(conn), columns=["category", "total_quantity", "item_count"])
    fig = px.bar(
        df,
        x="category",
        y="total_quantity",
        hover_data=["item_count"],
        labels={"category": "Category", "total_quantity": "Total quantity", "item_count": "Items"},
    )
    fig.update_layout(title="Quantity by category")
    return fig
