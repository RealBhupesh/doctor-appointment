"""Database abstraction: SQLite for local dev, PostgreSQL for Vercel."""
from __future__ import annotations

import os

_POSTGRES_URL = os.environ.get("POSTGRES_URL") or os.environ.get("DATABASE_URL")
_USE_POSTGRES = bool(_POSTGRES_URL)

if _USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor


class _DbConnection:
    """Wrapper to provide a unified interface for SQLite and Postgres."""

    def __init__(self):
        if _USE_POSTGRES:
            self._conn = psycopg2.connect(_POSTGRES_URL)
        else:
            import sqlite3
            self._conn = sqlite3.connect(
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "appointments.db")
            )
            self._conn.row_factory = sqlite3.Row

    def _adapt(self, sql: str) -> str:
        return sql.replace("?", "%s") if _USE_POSTGRES else sql

    def execute(self, sql: str, params=None):
        sql = self._adapt(sql)
        params = params or ()
        if _USE_POSTGRES:
            cur = self._conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(sql, params)
            return cur
        return self._conn.execute(sql, params)

    def executemany(self, sql: str, params_list):
        sql = self._adapt(sql)
        if _USE_POSTGRES:
            cur = self._conn.cursor(cursor_factory=RealDictCursor)
            cur.executemany(sql, params_list)
            return cur
        return self._conn.executemany(sql, params_list)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


def get_db_connection():
    return _DbConnection()


# Schema for init - Postgres uses SERIAL, SQLite uses AUTOINCREMENT
_SCHEMA_SQLITE = [
    """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        is_admin INTEGER NOT NULL DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        specialty TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        doctor_name TEXT NOT NULL,
        appointment_date TEXT NOT NULL,
        appointment_time TEXT NOT NULL,
        reason TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )""",
]

_SCHEMA_POSTGRES = [
    """CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        full_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        is_admin INTEGER NOT NULL DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS doctors (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        specialty TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS appointments (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        doctor_name TEXT NOT NULL,
        appointment_date TEXT NOT NULL,
        appointment_time TEXT NOT NULL,
        reason TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )""",
]


def init_schema(conn: _DbConnection) -> None:
    """Create tables using the appropriate schema."""
    schema = _SCHEMA_POSTGRES if _USE_POSTGRES else _SCHEMA_SQLITE
    for sql in schema:
        conn.execute(sql)
    conn.commit()
