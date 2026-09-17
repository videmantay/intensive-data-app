"""Shared helpers for returning Plotly figures from endpoints."""

import json
from typing import Any

from plotly.graph_objects import Figure
from pydantic import BaseModel


class PlotlyFigure(BaseModel):
    """A Plotly figure as JSON (the same shape as `fig.to_json()`)."""

    data: list[dict[str, Any]]
    layout: dict[str, Any]


def figure_response(fig: Figure) -> PlotlyFigure:
    # Round-trip through Plotly's JSON encoder so numpy/pandas values serialize correctly
    return PlotlyFigure.model_validate(json.loads(fig.to_json()))
