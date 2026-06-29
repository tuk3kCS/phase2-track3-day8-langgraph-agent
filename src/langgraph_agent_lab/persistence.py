from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver


def build_checkpointer(
    kind: str = "memory", database_url: str | None = None
) -> BaseCheckpointSaver | None:
    """Return a LangGraph checkpointer.

    TODO(student): implement SQLite support for the persistence extension track.
    The starter provides MemorySaver only — SQLite/Postgres are extension tasks.

    For SQLite:
    - pip install langgraph-checkpoint-sqlite
    - Use SqliteSaver with sqlite3.connect() and WAL mode
    - See: https://langchain-ai.github.io/langgraph/how-tos/persistence/
    """
    if kind == "none":
        return None
    if kind == "memory":
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()
    if kind == "sqlite":
        import sqlite3

        from langgraph.checkpoint.sqlite import SqliteSaver

        db_path = "checkpoints.db"
        if database_url:
            if database_url.startswith("sqlite:///"):
                db_path = database_url[10:]
            elif not database_url.startswith("postgres"):
                db_path = database_url

        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        return SqliteSaver(conn=conn)
    if kind == "postgres":
        if not database_url:
            raise ValueError("Postgres checkpointer requires DATABASE_URL")
        from langgraph.checkpoint.postgres import PostgresSaver  # type: ignore
        from psycopg_pool import ConnectionPool  # type: ignore

        pool = ConnectionPool(conninfo=database_url, autocommit=True)
        saver = PostgresSaver(pool)
        saver.setup()
        return saver
    raise ValueError(f"Unknown checkpointer kind: {kind}")
