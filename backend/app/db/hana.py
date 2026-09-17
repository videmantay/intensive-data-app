"""SAP HANA adapter (requires the `hana` extra: `uv sync --extra hana`).

SQL is passed through untouched since it is already written in HANA dialect.
"""

from typing import Any

from app.config import Settings
from app.db.base import Params, Row


class HanaConnection:
    dialect = "hana"

    def __init__(self, raw: Any) -> None:
        self._conn = raw

    def _rows(self, cursor: Any, rows: list[tuple]) -> list[Row]:
        names = [d[0].lower() for d in cursor.description or ()]
        return [dict(zip(names, row, strict=True)) for row in rows]

    def fetch_all(self, sql: str, params: Params = ()) -> list[Row]:
        with self._conn.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            return self._rows(cursor, cursor.fetchall())

    def fetch_one(self, sql: str, params: Params = ()) -> Row | None:
        with self._conn.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            row = cursor.fetchone()
            return self._rows(cursor, [tuple(row)])[0] if row else None

    def execute(self, sql: str, params: Params = ()) -> int:
        with self._conn.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            return cursor.rowcount

    def insert(self, sql: str, params: Params = ()) -> int:
        with self._conn.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            cursor.execute("SELECT CURRENT_IDENTITY_VALUE() FROM DUMMY")
            return int(cursor.fetchone()[0])

    def table_exists(self, name: str) -> bool:
        row = self.fetch_one(
            "SELECT 1 AS found FROM SYS.TABLES WHERE SCHEMA_NAME = CURRENT_SCHEMA AND TABLE_NAME = UPPER(?)",
            (name,),
        )
        return row is not None

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()


class HanaDatabase:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def connect(self) -> HanaConnection:
        from hdbcli import dbapi

        s = self.settings
        raw = dbapi.connect(
            address=s.hana_host,
            port=s.hana_port,
            user=s.hana_user,
            password=s.hana_password,
            encrypt=s.hana_encrypt,
            **({"currentSchema": s.hana_schema} if s.hana_schema else {}),
        )
        raw.setautocommit(False)
        return HanaConnection(raw)

    def ping(self) -> bool:
        conn = self.connect()
        try:
            return conn.fetch_one("SELECT 1 AS ok FROM DUMMY") is not None
        finally:
            conn.close()
