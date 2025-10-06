import psycopg2
from tabulate import tabulate
import folium
import json
import google.generativeai as genai
from dotenv import load_dotenv
import os
import re

# Load environment variables
load_dotenv()

class GeminiQueryProcessor:
    def __init__(self):
        # Configure Gemini API
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        
        # Database connection
        self.conn = psycopg2.connect(
            host="localhost",
            database="mumbai",
            user="your-username",
            password="your-password"
        )
        self.cur = self.conn.cursor()
        
        # Ensure pg_trgm extension is enabled
        self.cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
        self.conn.commit()
        
        # Database schema information for context
        self.schema_info = """
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
        
        Key relationships:
        - Use ST_Within() to find points within polygons (e.g., amenities in suburbs)
        - Use ST_DWithin() for proximity searches
        - Use similarity() with pg_trgm for fuzzy text matching
        - Always transform coordinates to WGS84 (EPSG:4326) using ST_Transform(way, 4326)
        - Use ST_AsGeoJSON() to get coordinates for mapping
        
        Common query patterns:
        - Find amenities in a specific area: JOIN point and polygon tables with ST_Within()
        - Find nearby amenities: Use ST_DWithin() for distance-based searches
        - Fuzzy text matching: Use similarity() function with pg_trgm
        - Get coordinates: ST_AsGeoJSON(ST_Transform(way, 4326))
        """
    
    def generate_sql_query(self, natural_language_query):
        """Convert natural language query to SQL using Gemini"""
        
        prompt = f"""
        You are a SQL expert for a PostgreSQL database containing Mumbai OpenStreetMap data.
        
        Database Schema:
        {self.schema_info}
        
        User Query: '{natural_language_query}'
        
        Generate a SQL query that answers this question. Follow these guidelines:
        
        1. Always use proper JOINs between planet_osm_point and planet_osm_polygon when searching for amenities in areas
        2. Use ST_Within() to find points within polygons
        3. Use similarity() for fuzzy text matching on names
        4. Always transform coordinates to WGS84: ST_Transform(way, 4326)
        5. Use ST_AsGeoJSON() to get coordinates for mapping
        6. Include LIMIT to prevent overwhelming results (typically 50-100)
        7. Order results by relevance (similarity scores, distance, etc.)
        8. Embed the actual values directly in the query (no placeholders)
        9. Use single quotes around string values
        10. For location matching, use similarity() with a threshold of 0.3 or higher
        
        Return ONLY the SQL query, no explanations or markdown formatting.
        The query should be ready to execute directly.
        
        Example format:
        SELECT a.name, a.amenity, ST_AsGeoJSON(ST_Transform(a.way, 4326)) AS geom, b.name AS suburb
        FROM planet_osm_point a
        JOIN planet_osm_polygon b ON ST_Within(a.way, b.way)
        WHERE a.amenity = 'restaurant' AND similarity(b.name, 'bandra') > 0.3
        ORDER BY similarity(b.name, 'bandra') DESC
        LIMIT 50;
        """
        
        try:
            response = self.model.generate_content(prompt)
            sql_query = response.text.strip()
            
            # Clean up the response (remove markdown formatting if present)
            sql_query = re.sub(r'^```sql\s*', '', sql_query)
            sql_query = re.sub(r'\s*```$', '', sql_query)
            
            return sql_query
        except Exception as e:
            raise Exception(f"Error generating SQL query: {e}")
    
    
    def execute_query(self, sql_query):
        """Execute the SQL query directly"""
        try:
            print(f"Executing SQL: {sql_query}")
            self.cur.execute(sql_query)
            results = self.cur.fetchall()
            return results
        except Exception as e:
            print(f"Query execution failed: {e}")
            raise Exception(f"Error executing query: {e}")
    
    def find_geometry_column(self, result):
        """Find which column contains the geometry data by checking for JSON format"""
        for i, column in enumerate(result):
            if column and isinstance(column, str):
                try:
                    data = json.loads(column)
                    if isinstance(data, dict) and data.get('type') in ['Point', 'Polygon', 'LineString'] and 'coordinates' in data:
                        return i
                except (json.JSONDecodeError, TypeError):
                    continue
        return None
    
    def extract_coordinates(self, geom_data):
        """Extract longitude and latitude from geometry data (Point, Polygon, or LineString)"""
        try:
            geom_type = geom_data.get('type')
            coords = geom_data.get('coordinates')
            
            if geom_type == 'Point' and coords and len(coords) >= 2:
                return coords[0], coords[1]  # lon, lat
            elif geom_type == 'Polygon' and coords and len(coords) > 0:
                # For polygon, use the centroid of the first ring
                ring = coords[0]
                if len(ring) > 0:
                    # Calculate centroid
                    lons = [point[0] for point in ring]
                    lats = [point[1] for point in ring]
                    centroid_lon = sum(lons) / len(lons)
                    centroid_lat = sum(lats) / len(lats)
                    return centroid_lon, centroid_lat
            elif geom_type == 'LineString' and coords and len(coords) > 0:
                # For line, use the first point
                return coords[0][0], coords[0][1]  # lon, lat
        except (IndexError, TypeError, KeyError):
            pass
        return None, None
    
    def create_map(self, results, query_description):
        """Create a map with the query results"""
        if not results:
            return None
        
        try:
            # Find which column contains the geometry data
            geom_col = self.find_geometry_column(results[0])
            if geom_col is None:
                print("No valid geometry data found in results")
                return None, 0
            
            # Parse first result to get initial coordinates
            first_geom = json.loads(results[0][geom_col])
            lon, lat = self.extract_coordinates(first_geom)
            
            if lon is not None and lat is not None:
                if 18.0 <= lat <= 20.0 and 72.0 <= lon <= 74.0:
                    m = folium.Map(location=[lat, lon], zoom_start=15)
                else:
                    m = folium.Map(location=[19.0760, 72.8777], zoom_start=15)
            else:
                m = folium.Map(location=[19.0760, 72.8777], zoom_start=15)
            
            # Add markers for all results
            valid_coords = []
            for i, result in enumerate(results):
                try:
                    if len(result) > geom_col:  # Ensure we have geometry data
                        geom = result[geom_col]
                        name = result[0]  # Name is always first column
                        amenity = result[1] if len(result) > 1 else "Unknown"  # Amenity is usually second
                        
                        coords_data = json.loads(geom)
                        lon, lat = self.extract_coordinates(coords_data)
                        
                        if lon is not None and lat is not None and 18.0 <= lat <= 20.0 and 72.0 <= lon <= 74.0:
                            # Find area column (usually the last column that's not geometry)
                            suburb = "Unknown"
                            for j, col in enumerate(result):
                                if j != geom_col and j != 0 and j != 1 and col and not col.startswith('{'):
                                    suburb = col
                                    break
                            
                            popup_text = f"<b>{name}</b><br>Type: {amenity}<br>Area: {suburb}<br>Coords: {lat:.6f}, {lon:.6f}"
                            
                            folium.Marker(
                                [lat, lon], 
                                popup=popup_text,
                                tooltip=f"{name} ({amenity})"
                            ).add_to(m)
                            
                            valid_coords.append([lat, lon])
                except Exception as e:
                    print(f"Warning: Could not add marker for result {i}: {e}")
                    continue
            
            # Fit map bounds to show all markers
            if valid_coords:
                lats = [coord[0] for coord in valid_coords]
                lons = [coord[1] for coord in valid_coords]
                
                bounds = [
                    [min(lats), min(lons)],
                    [max(lats), max(lons)]
                ]
                m.fit_bounds(bounds)
            
            # Save map
            map_filename = f"map_{query_description.replace(' ', '_')}.html"
            m.save(map_filename)
            return map_filename, len(valid_coords)
            
        except Exception as e:
            print(f"Error creating map: {e}")
            return None, 0
    
    def process_query(self, natural_language_query):
        """Main method to process a natural language query"""
        try:
            print(f"\nProcessing query: '{natural_language_query}'")
            print("=" * 50)
            
            # Generate SQL query with embedded values
            print("Generating SQL query...")
            sql_query = self.generate_sql_query(natural_language_query)
            print(f"Generated SQL: {sql_query}")
            
            # Execute query directly
            print("Executing query...")
            results = self.execute_query(sql_query)
            
            if results:
                print(f"\nFound {len(results)} results:")
                print("=" * 50)
                
                # Display results in table format
                headers = ["Name", "Type", "Geometry", "Area"] if len(results[0]) > 3 else ["Name", "Type", "Geometry"]
                display_results = []
                for result in results:
                    if len(result) > 3:
                        display_results.append([result[0], result[1], "Point", result[3]])
                    else:
                        display_results.append([result[0], result[1], "Point", "Unknown"])
                
                print(tabulate(display_results, headers=headers, tablefmt="psql"))
                
                # Create map
                print("\nCreating map...")
                map_info = self.create_map(results, natural_language_query[:30])
                if map_info:
                    map_filename, marker_count = map_info
                    print(f"Map saved as '{map_filename}' with {marker_count} markers")
                
            else:
                print("No results found for your query.")
            
            return results
            
        except Exception as e:
            print(f"Error processing query: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def close(self):
        """Close database connection"""
        self.cur.close()
        self.conn.close()

def main():
    """Main function to run the query processor"""
    try:
        # Initialize the processor
        processor = GeminiQueryProcessor()
        
        print("Mumbai OpenStreetMap Query Processor")
        print("Using Google Gemini AI for natural language processing")
        print("=" * 50)
        
        while True:
            try:
                # Get user input
                query = input("\nEnter your query (or 'quit' to exit): ").strip()
                
                if query.lower() in ['quit', 'exit', 'q']:
                    break
                
                if not query:
                    print("Please enter a valid query.")
                    continue
                
                # Process the query
                processor.process_query(query)
                
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
                continue
        
        # Close connections
        processor.close()
        print("Goodbye!")
        
    except Exception as e:
        print(f"Failed to initialize: {e}")
        print("Make sure you have set the GEMINI_API_KEY environment variable.")

if __name__ == "__main__":
    main()
