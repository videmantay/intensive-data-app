"""How a feature describes its data to the analytics engine.

A `Dataset` names the dimensions (fields to group and filter by) and measures
(aggregates) people can ask about, each mapped to a SQLAlchemy expression. Only these
names can appear in a `WidgetSpec`, so the agent and the builder can never reach a
column that isn't listed here. See `app/items/dataset.py` for an example, and add new
datasets to `registry.py`.
"""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.sql.elements import ColumnElement

from app.analytics.spec import DatasetInfo, DimensionInfo, FieldKind, MeasureInfo


class SpecError(ValueError):
    """A widget spec that doesn't fit its dataset (unknown field, wrong filter, ...)."""


@dataclass(frozen=True)
class Dimension:
    column: ColumnElement[Any]
    label: str
    kind: FieldKind
    description: str = ""


@dataclass(frozen=True)
class Measure:
    expr: ColumnElement[Any]  # an aggregate, e.g. func.sum(Item.quantity)
    label: str
    description: str = ""


@dataclass(frozen=True)
class Dataset:
    name: str
    label: str
    description: str
    table: Any  # the SQLModel table class to select from
    dimensions: dict[str, Dimension] = field(default_factory=dict)
    measures: dict[str, Measure] = field(default_factory=dict)

    def dimension(self, name: str) -> Dimension:
        if name not in self.dimensions:
            raise SpecError(
                f"{self.name!r} has no dimension {name!r}. Dimensions: {', '.join(self.dimensions)}"
                + (" (that's a measure)" if name in self.measures else "")
            )
        return self.dimensions[name]

    def measure(self, name: str) -> Measure:
        if name not in self.measures:
            raise SpecError(
                f"{self.name!r} has no measure {name!r}. Measures: {', '.join(self.measures)}"
                + (" (that's a dimension)" if name in self.dimensions else "")
            )
        return self.measures[name]

    def label_of(self, name: str) -> str:
        if name in self.dimensions:
            return self.dimensions[name].label
        if name in self.measures:
            return self.measures[name].label
        return name

    def info(self) -> DatasetInfo:
        return DatasetInfo(
            name=self.name,
            label=self.label,
            description=self.description,
            dimensions=[
                DimensionInfo(name=n, label=d.label, kind=d.kind, description=d.description)
                for n, d in self.dimensions.items()
            ],
            measures=[MeasureInfo(name=n, label=m.label, description=m.description) for n, m in self.measures.items()],
        )
