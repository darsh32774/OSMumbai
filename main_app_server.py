import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse 
import uvicorn

from server.gemini_processor import generate_sql_query
from server.database_processor import execute_query_raw 
from server.map_processor import create_folium_map

app = FastAPI()

origins = [
    "*", 
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
        sql = generate_sql_query(query)
        print(f"Generated SQL: {sql}")

        headers, db_rows = execute_query_raw(sql)

        display_rows = []
        geojson_features = []
        geom_col_index = None

        for i, h in enumerate(headers):
            if h.lower() in ["geojson", "st_asgeojson", "coordinates"]:
                geom_col_index = i
                break
        
        for row in db_rows:
            display_row = list(row)
            
            if geom_col_index is not None:
                geojson_str = row[geom_col_index]
                if geojson_str:
                    geojson_obj = json.loads(geojson_str)
                    
                    properties = {
                        headers[i]: value
                        for i, value in enumerate(row) if i != geom_col_index
                    }
                    geojson_features.append({
                        "type": "Feature",
                        "geometry": geojson_obj,
                        "properties": properties
                    })
                
                if geom_col_index < len(display_row):
                     display_row.pop(geom_col_index)
            
            display_rows.append(display_row)

        if geom_col_index is not None:
             display_headers = [h for i, h in enumerate(headers) if i != geom_col_index]
        else:
             display_headers = headers

        map_html = None
        if geojson_features:
            map_html = create_folium_map(geojson_features)

        return JSONResponse(content={
            "sql": sql, 
            "rows_count": len(db_rows), 
            "headers": display_headers,
            "display_rows": display_rows,
            "map_html": map_html
        })

    except RuntimeError as e:
        print(f"Runtime error during processing: {e}")
        raise HTTPException(status_code=500, detail=f"Database or LLM processing failed: {e}")
    except ValueError as e:
        print(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid query or data structure: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
        
