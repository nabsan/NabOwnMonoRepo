from fastmcp import tool
import vertica_python
import os
from core.query_guard import guard_sql

@tool
def vertica_query(sql: str, limit: int = 100):
    """Execute read-only query on Vertica"""
    sql = guard_sql(sql, max_limit=limit)

    conn_info = {
        "host": os.getenv("VERTICA_HOST"),
        "port": int(os.getenv("VERTICA_PORT", "5433")),
        "user": os.getenv("VERTICA_USER"),
        "password": os.getenv("VERTICA_PASSWORD"),
        "database": os.getenv("VERTICA_DB"),
        "autocommit": True,
        "connection_timeout": 5,
    }

    with vertica_python.connect(**conn_info) as conn:
        cur = conn.cursor()
        cur.execute(sql)
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    return {"count": len(rows), "rows": rows}
