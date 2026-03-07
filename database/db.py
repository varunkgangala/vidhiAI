import sqlite3
from datetime import datetime


def get_db(db_path="vidhiai.db"):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path="vidhiai.db"):
    conn = get_db(db_path)
    cur = conn.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            username  TEXT    NOT NULL UNIQUE,
            email     TEXT    NOT NULL UNIQUE,
            password  TEXT    NOT NULL,
            created_at TEXT   DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS analysis_history (
            analysis_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            document_name   TEXT    NOT NULL,
            compliance_score REAL   NOT NULL,
            risk_level      TEXT    NOT NULL,
            analysis_text   TEXT    NOT NULL,
            timestamp       TEXT    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
    """)
    conn.commit()
    conn.close()