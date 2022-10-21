from sqlalchemy.sql import text as sql_text


def parse_sql_text(sql: str) -> str:
    return sql_text(sql)
