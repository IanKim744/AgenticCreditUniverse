from __future__ import annotations

import sqlite3
from collections.abc import Iterator

from fastapi import Depends

from .settings import Settings, get_settings


def get_db(s: Settings = Depends(get_settings)) -> Iterator[sqlite3.Connection]:
    con = sqlite3.connect(s.db_path)
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.close()
