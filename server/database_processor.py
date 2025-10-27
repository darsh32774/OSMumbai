import psycopg2
import os
from typing import List, Tuple, Any

DB_HOST = os.getenv('SUPABASE_DB_HOST')
DB_PORT = os.getenv('SUPABASE_DB_PORT')
DB_NAME = os.getenv('SUPABASE_DB_NAME')
DB_USER = os.getenv('SUPABASE_DB_USER')
DB_PASSWORD = os.getenv('SUPABASE_DB_PASSWORD')

def execute_query_raw(sql_query: str) -> Tuple[List[str], List[Tuple[Any, ...]]]:
    if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT]):
        raise RuntimeError("Database connection details are incomplete.")

    cleaned_query = sql_query.strip().upper()
    if not cleaned_query.startswith(("SELECT", "WITH")):
        raise ValueError("SQL validation failed: only SELECT or WITH queries allowed")
        
    if len(sql_query.split(';')) > 1 and sql_query.strip().endswith(';'):
        sql_query = sql_query.strip().rstrip(';')

    conn = None
    cur = None
    headers = []
    rows = []

    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        cur = conn.cursor()
        
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        conn.commit()

        print(f"Executing SQL: {sql_query}")
        cur.execute(sql_query)
        
        if cur.description:
            headers = [desc[0] for desc in cur.description]

        rows = cur.fetchall()
        
        return headers, rows
        
    except psycopg2.Error as e:
        print(f"Database Query execution failed: {e}")
        print(f"Failed query: {sql_query}")
        raise RuntimeError(f"Database Query Failed: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
