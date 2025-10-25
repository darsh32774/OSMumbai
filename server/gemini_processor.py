import google.generativeai as genai
from dotenv import load_dotenv
import os
import re

load_dotenv()

MODEL_NAME = 'gemini-2.5-pro'

API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set.")
genai.configure(api_key=API_KEY)

try:
    _model = genai.GenerativeModel(MODEL_NAME)
except Exception as e:
    raise RuntimeError(f"Failed to initialize Gemini Model: {e}")

SQL_SCHEMA = """
Database Schema for Mumbai OpenStreetMap data:

Tables:
1. planet_osm_point - Contains point features like amenities, shops, etc.
   - name: Name of the location
   - amenity: Type of amenity (restaurant, hospital, school, etc.)
   - way: Geometry column (PostGIS)
   - shop: Type of shop
   - tourism: Tourism-related features
   - leisure: Leisure facilities
   - education: Educational institutions
   
2. planet_osm_polygon - Contains area features like suburbs, neighborhoods
   - name: Name of the area (suburb, locality)
   - way: Geometry column (PostGIS)
   - place: Type of place (suburb, city, etc.)
   - admin_level: Administrative level
   
3. planet_osm_line - Contains linear features like roads
   - name: Name of the road
   - highway: Type of highway
   - way: Geometry column (PostGIS)

Key relationships and functions to use:
- Use ST_Within() to find points within polygons (e.g., amenities in suburbs)
- Use ST_DWithin() for proximity searches (PostGIS is projected, use meters)
- Use similarity() with pg_trgm for fuzzy text matching
- Always transform coordinates to WGS84 (EPSG:4326) using ST_Transform(way, 4326)
- Use ST_AsGeoJSON() to get coordinates for mapping

Common query patterns:
- Find amenities in a specific area: JOIN point and polygon tables with ST_Within()
- Find nearby amenities: Use ST_DWithin() for distance-based searches
- Get coordinates: ST_AsGeoJSON(ST_Transform(way, 4326))
"""

def generate_sql_query(natural_language_query: str) -> str:
    prompt = f"""
You are a SQL expert for a PostgreSQL database containing Mumbai OpenStreetMap data.

Database Schema:
{SQL_SCHEMA}

User Query: "{natural_language_query}"

Generate a SQL query that answers this question. Follow these guidelines:

1. Use proper JOINs between planet_osm_point and planet_osm_polygon when searching for amenities in areas.
2. Use ST_Within() to find points within polygons.
3. Use similarity() for fuzzy text matching on names.
4. Always transform coordinates to WGS84: ST_Transform(way, 4326).
5. Use ST_AsGeoJSON() to get coordinates for mapping.
6. Include LIMIT to prevent overwhelming results (typically 50-100).
7. Order results by relevance (similarity scores, distance, etc.)
8. Embed the actual values directly in the query (no placeholders).
9. Use single quotes around string values.
10. For location matching, use similarity() with a threshold of 0.3 or higher.

Return ONLY the SQL query, no explanations or markdown formatting.
The query should be ready to execute directly. DO NOT include a semicolon (;) at the end of the query.
"""
    
    try:
        response = _model.generate_content(prompt)
        sql_query = response.text.strip()
        
        sql_query = re.sub(r'^```sql\s*', '', sql_query, flags=re.MULTILINE)
        sql_query = re.sub(r'\s*```$', '', sql_query, flags=re.MULTILINE)
        
        sql_query = sql_query.split(';')[0].strip()
        
        if not sql_query.upper().startswith("SELECT"):
            raise ValueError(f"Gemini returned non-SELECT output: {sql_query[:50]}...")
            
        return sql_query
    except Exception as e:
        raise RuntimeError(f"Error generating SQL query for '{natural_language_query}': {e}")

