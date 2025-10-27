import google.genai as genai
from dotenv import load_dotenv
import os
import re
from typing import Any

load_dotenv()

MODEL_NAME = 'gemini-2.5-flash-lite'

API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set.")

try:
    client = genai.Client()
except Exception as e:
    raise RuntimeError(f"Failed to initialize Gemini Client: {e}")

SQL_SCHEMA_COMPRESSED = """
Tables (PostgreSQL/PostGIS):
1. planet_osm_point (name, amenity, shop, tourism, leisure, education, way:geometry)
2. planet_osm_polygon (name, place, admin_level, way:geometry)
3. planet_osm_line (name, highway, way:geometry)

Functions: ST_Within(point, poly), ST_DWithin(geom, geom, meters), similarity(col, text).
Output MUST be ST_AsGeoJSON(ST_Transform(way, 4326)).
Limit results to 50.
"""

SYSTEM_INSTRUCTION = f"""
You are a SQL expert for a PostgreSQL database containing Mumbai OpenStreetMap data.
Your sole purpose is to convert a user's natural language query into a single, executable SQL SELECT statement based on the following schema and rules.

Schema:
{SQL_SCHEMA_COMPRESSED}

Rules:
1. Always use single quotes for string values.
2. DO NOT include the final semicolon (;).
3. DO NOT use markdown, explanations, or any text other than the SQL query itself.
4. For general location matching, use similarity() (threshold >= 0.7).
5. **MANDATORY AREA SEARCH LOGIC (Must start with WITH/CTEs and use fuzzy matching):**
   When searching for features (e.g., 'hospitals', 'shops') *within* a named region (e.g., 'Goregaon'), you MUST define the boundary using two Common Table Expressions (CTEs): AreaCandidate and SelectedArea.
   - The query MUST begin with the WITH keyword defining AreaCandidate.
   - CTE 1 (AreaCandidate): UNION ALL of two lookups (Priority 1: Polygon, Priority 2: Point-Buffer). You MUST use the similarity function with a threshold of at least 0.1 on the 'name' column, replacing 'REGION_NAME' with the actual name from the user's query in all instances.
     - Priority 1: Polygon lookup (SELECT ST_COLLECT(way) AS geom, 1 AS priority FROM planet_osm_polygon WHERE similarity(name, 'REGION_NAME') > 0.3 AND (place IS NOT NULL OR admin_level IS NOT NULL) GROUP BY priority)
     - Priority 2: Point-Buffer lookup (SELECT ST_Transform(ST_Buffer(ST_Transform(way, 4326)::geography, 1000)::geometry, ST_SRID(way)) AS geom, 2 AS priority FROM planet_osm_point WHERE similarity(name, 'REGION_NAME') > 0.8)
   - CTE 2 (SelectedArea): Must follow AreaCandidate (e.g., , SelectedArea AS (SELECT geom FROM AreaCandidate ORDER BY priority LIMIT 1)).
   - Final SELECT: The final SELECT MUST include the feature's name and geometry (e.g., SELECT amenities.name, ST_AsGeoJSON(ST_Transform(amenities.way, 4326)) FROM ...). JOIN the feature table (e.g., planet_osm_point AS amenities) with SelectedArea ON ST_Intersects(amenities.way, SelectedArea.geom).
"""


def initialize_sql_chat(client: genai.Client):
    try:
        chat_session = client.chats.create(
            model=MODEL_NAME,
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION
            )
        )
        return chat_session
    except Exception as e:
        raise RuntimeError(f"Failed to initialize Gemini Chat Session: {e}")

def generate_sql_query_from_chat(chat_session: Any, natural_language_query: str) -> str:
    user_prompt = f"User Query: {natural_language_query}"
    
    try:
        response = chat_session.send_message(user_prompt)
        sql_query = response.text.strip()
        
        sql_query = re.sub(r'^```sql\s*', '', sql_query, flags=re.MULTILINE)
        sql_query = re.sub(r'\s*```$', '', sql_query, flags=re.MULTILINE)
        sql_query = sql_query.split(';')[0].strip()
        
        if not sql_query.upper().startswith(("SELECT", "WITH")):
            raise ValueError(f"Gemini returned an invalid SQL start keyword: {sql_query[:50]}...")
            
        return sql_query
    except Exception as e:
        raise RuntimeError(f"Error generating SQL query for '{natural_language_query}': {e}")
