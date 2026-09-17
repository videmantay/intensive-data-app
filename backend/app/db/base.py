from collections.abc import Sequence
from typing import Any, Protocol

Params = Sequence[Any]
Row = dict[str, Any]


class Connection(Protocol):
    """A single database connection/transaction.

    All SQL passed in is SAP HANA dialect using qmark (`?`) parameters.
    Result rows are dicts keyed by lowercase column name.
    """

    dialect: str

    def fetch_all(self, sql: str, params: Params = ()) -> list[Row]: ...

    def fetch_one(self, sql: str, params: Params = ()) -> Row | None: ...

    def execute(self, sql: str, params: Params = ()) -> int:
        """Run a statement and return the affected row count."""
        ...

    def insert(self, sql: str, params: Params = ()) -> int:
        """Run an INSERT into a table with an identity column and return the new id."""
        ...

    def table_exists(self, name: str) -> bool: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def close(self) -> None: ...


class Database(Protocol):
    def connect(self) -> Connection: ...

    def ping(self) -> bool: ...
