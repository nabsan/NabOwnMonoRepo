import re

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create)\b",
    re.IGNORECASE,
)

def guard_sql(sql: str, max_limit: int = 1000):
    if not sql.strip().lower().startswith("select"):
        raise ValueError("Only SELECT is allowed")

    if FORBIDDEN.search(sql):
        raise ValueError("Forbidden SQL keyword detected")

    if not re.search(r"\blimit\b", sql, re.IGNORECASE):
        sql = f"{sql.rstrip(';')} LIMIT {max_limit}"

    return sql

