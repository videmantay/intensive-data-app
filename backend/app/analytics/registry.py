"""Every dataset the builder and the assistant can query. Add new ones to `DATASETS`."""

from app.analytics.datasets import Dataset, SpecError
from app.items.dataset import ITEMS

DATASETS: dict[str, Dataset] = {d.name: d for d in [ITEMS]}


def get_dataset(name: str) -> Dataset:
    if name not in DATASETS:
        raise SpecError(f"Unknown dataset {name!r}. Datasets: {', '.join(DATASETS)}")
    return DATASETS[name]


def catalog() -> str:
    """The datasets as text, for the assistant's instructions."""
    lines = []
    for ds in DATASETS.values():
        lines.append(f"## {ds.name}: {ds.label}\n{ds.description}\nDimensions (group/filter by):")
        for name, dim in ds.dimensions.items():
            note = f": {dim.description}" if dim.description else ""
            lines.append(f"- {name} ({dim.kind}) '{dim.label}'{note}")
        lines.append("Measures (aggregates):")
        for name, m in ds.measures.items():
            note = f": {m.description}" if m.description else ""
            lines.append(f"- {name} '{m.label}'{note}")
        lines.append("")
    return "\n".join(lines)
