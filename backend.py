import psycopg2
import os

DATABASE_URL = os.environ.get("postgresql://gamemodedb_user:ahln2WBXAacau5ipSVIOfzfly5QxBQj5@dpg-d6879nogjchc73bdu4mg-a/gamemodedb")  # Set this in Render

def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    c = conn.cursor()
    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            tier TEXT NOT NULL
        )
    """)
    # Suggestions table
    c.execute("""
        CREATE TABLE IF NOT EXISTS suggestions (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL,
            idea TEXT NOT NULL,
            email TEXT,
            status TEXT NOT NULL DEFAULT 'pending'
        )
    """)
    conn.commit()
    conn.close()
