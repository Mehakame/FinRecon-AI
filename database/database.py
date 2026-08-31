import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "finrecon_audit.db"


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS review_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            invoice TEXT,
            decision TEXT NOT NULL,
            reviewer_note TEXT,
            risk_score INTEGER,
            risk_level TEXT
        )
        """)


def save_review(invoice, decision, reviewer_note, risk_score=None, risk_level=None):
    init_db()
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO review_log(timestamp, invoice, decision, reviewer_note, risk_score, risk_level) VALUES(?,?,?,?,?,?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), invoice, decision, reviewer_note, risk_score, risk_level),
        )


def get_reviews() -> pd.DataFrame:
    init_db()
    with sqlite3.connect(DB_PATH) as con:
        return pd.read_sql_query("SELECT * FROM review_log ORDER BY id DESC", con)
