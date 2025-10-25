import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse # Required for structured response
import uvicorn

# Import the processors
from server.gemini_processor import generate_sql_query
# NOTE: execute_query_raw must now return (headers, rows)
from server.database_processor import execute_query_raw 
from server.map_processor import create_folium_map # New essential import

# Initialize FastAPI app
app = FastAPI()

# Configure CORS
origins = [
    "*", # Allow all origins for development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Mumbai OSM NL-to-Map API"}

@app.post("/nl-to-map")
async def nl_to_map(request: dict):
    """
    Endpoint to convert a Natural Language query to a Map data.
    The response format is fixed to match the client's expectation: 
    {'sql', 'rows_count', 'headers', 'display_rows', 'map_html'}
    """
    query = request.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    try:
        # 1. Generate SQL query using Gemini
        sql = generate_sql_query(query)
        print(f"Generated SQL: {sql}")

        # 2. Execute SQL query. execute_query_raw now returns (headers, rows)
        headers, db_rows = execute_query_raw(sql)

        # 3. Process results: Separate tabular data from GeoJSON data
        display_rows = []
        geojson_features = []
        geom_col_index = None

        # Find the GeoJSON column index
        for i, h in enumerate(headers):
            if h.lower() in ["geojson", "st_asgeojson", "coordinates"]:
                geom_col_index = i
                break
        
        # Process rows: split into display data and map data
        for row in db_rows:
            display_row = list(row)
            
            if geom_col_index is not None:
                # Extract GeoJSON for mapping
                geojson_str = row[geom_col_index]
                if geojson_str:
                    geojson_obj = json.loads(geojson_str)
                    
                    # Create properties for map popup/tooltip by excluding the geometry column
                    properties = {
                        headers[i]: value
                        for i, value in enumerate(row) if i != geom_col_index
                    }
                    geojson_features.append({
                        "type": "Feature",
                        "geometry": geojson_obj,
                        "properties": properties
                    })
                
                # Remove the GeoJSON column from the tabular display data
                if geom_col_index < len(display_row):
                     display_row.pop(geom_col_index)
            
            # The tabular data for the client display
            display_rows.append(display_row)

        # 4. Update headers to exclude the GeoJSON column
        if geom_col_index is not None:
             # Make a copy of headers and remove the geometry column name
             display_headers = [h for i, h in enumerate(headers) if i != geom_col_index]
        else:
             display_headers = headers

        # 5. Generate map HTML if features exist
        map_html = None
        if geojson_features:
            map_html = create_folium_map(geojson_features)

        # 6. Correctly format and return the response dictionary with expected keys
        return JSONResponse(content={
            "sql": sql, # FIX: use 'sql' key
            "rows_count": len(db_rows), # FIX: use 'rows_count' key
            "headers": display_headers,
            "display_rows": display_rows,
            "map_html": map_html
        })

    except RuntimeError as e:
        # Catch errors from both gemini_processor and database_processor
        print(f"Runtime error during processing: {e}")
        # Return 500 status with error detail
        raise HTTPException(status_code=500, detail=f"Database or LLM processing failed: {e}")
    except ValueError as e:
        # Catch validation errors (like non-SELECT output)
        print(f"Validation error: {e}")
        # Return 400 status with error detail
        raise HTTPException(status_code=400, detail=f"Invalid query or data structure: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

