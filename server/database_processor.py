import psycopg2
import os
from typing import List, Tuple, Any

# --- Supabase Configuration from Environment ---
DB_HOST = os.getenv('SUPABASE_DB_HOST')
DB_PORT = os.getenv('SUPABASE_DB_PORT')
DB_NAME = os.getenv('SUPABASE_DB_NAME')
DB_USER = os.getenv('SUPABASE_DB_USER')
DB_PASSWORD = os.getenv('SUPABASE_DB_PASSWORD')

def execute_query_raw(sql_query: str) -> Tuple[List[str], List[Tuple[Any, ...]]]:
    """
    Executes a single raw SQL query against the Supabase database.
    
    Args:
        sql_query: The SQL query string to execute.
    
    Returns:
        A tuple: (list of header strings, list of result rows (tuples)).
    
    Raises:
        ValueError: If the SQL query validation fails (e.g., non-SELECT).
        RuntimeError: If database connection or execution fails.
    """
    if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD, DB_PORT]):
          raise RuntimeError("Database connection details are incomplete.")

    # Validation: Ensure only a single SELECT query is executed for safety
    cleaned_query = sql_query.strip().upper()
    if not cleaned_query.startswith("SELECT"):
        raise ValueError("SQL validation failed: only SELECT queries allowed")
        
    # CRITICAL FIX: Ensure only one statement exists by checking for multiple semicolons 
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
        
        # Ensure pg_trgm extension is enabled (safe to run repeatedly)
        cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        conn.commit()

        print(f"Executing SQL: {sql_query}")
        cur.execute(sql_query)
        
        # ⚠️ FIX: Capture headers if results are present
        if cur.description:
             headers = [desc[0] for desc in cur.description]

        rows = cur.fetchall()
        
        # ⚠️ FIX: Return both headers and rows
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

