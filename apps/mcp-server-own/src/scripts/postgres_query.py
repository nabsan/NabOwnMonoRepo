from fastmcp import tool
import psycopg2
import os
from core.query_guard import guard_sql

@tool
def postgres_query(sql: str, limit: int = 100):
    """Execute read-only query on PostgreSQL"""
    sql = guard_sql(sql, max_limit=limit)

    conn = psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT", "5432"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD"),
        dbname=os.getenv("PG_DB"),
        connect_timeout=5,
    )

    cur = conn.cursor()
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()

    return {"count": len(rows), "rows": rows}

