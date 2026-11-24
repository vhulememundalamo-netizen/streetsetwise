"""Create tables and apply row-level security. Run with the OWNER role: python -m app.migrate

For a team project, replace create_all with Alembic migrations; keep rls.sql as the last step.
"""
import os
from pathlib import Path

from sqlalchemy import create_engine, text

from . import models  # noqa: F401  (register tables)
from .db import Base


def run(owner_url: str | None = None) -> None:
    url = owner_url or os.environ["OWNER_DATABASE_URL"]
    eng = create_engine(url)
    Base.metadata.create_all(eng)
    sql = (Path(__file__).parent / "sql" / "rls.sql").read_text()
    with eng.begin() as conn:
        conn.exec_driver_sql(sql.replace("%", "%%"))  # psycopg treats % as a placeholder


if __name__ == "__main__":
    run()
    print("Schema and row-level security applied.")
