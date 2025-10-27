import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse 
import uvicorn
import google.genai as genai

from server.gemini_processor import initialize_sql_chat, generate_sql_query_from_chat, client 
from server.database_processor import execute_query_raw 
from server.map_processor import create_folium_map 

app = FastAPI()

global_chat_session = None

@app.on_event("startup")
async def startup_event():
    """Initializes the single global chat session when the server starts."""
    global global_chat_session
    try:
        global_chat_session = initialize_sql_chat(client)
        print("✅ Gemini Chat Session Initialized successfully.")
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Could not initialize Gemini Chat Session: {e}")

origins = ["*"]
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
    global global_chat_session
    
    if global_chat_session is None:
        raise HTTPException(status_code=503, detail="Gemini service is not available (Chat session failed to initialize).")

    query = request.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    try:
        sql = generate_sql_query_from_chat(global_chat_session, query)
        print(f"Generated SQL: {sql}")

        headers, db_rows = execute_query_raw(sql)
        
        display_rows = []
        geojson_features = []
        geom_col_index = None

        for i, h in enumerate(headers):
            h_lower = h.lower()
            if h_lower in ["geojson", "st_asgeojson", "coordinates"] or 'st_asgeojson(' in h_lower:
                geom_col_index = i
                break
            
        for row in db_rows:
            display_row = list(row)
            
            if geom_col_index is not None:
                geojson_str = row[geom_col_index]
                if geojson_str:
                    try:
                        geojson_obj = json.loads(geojson_str)
                    except (json.JSONDecodeError, TypeError) as decode_err:
                        print(f"Error decoding GeoJSON string: {decode_err} from data: {geojson_str[:100]}...")
                        continue
                        
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

        final_geojson_dict = create_folium_map(geojson_features)
        
        print(f"GeoJSON Features Count: {len(geojson_features)}")

        return JSONResponse(content={
            "sql": sql, 
            "rows_count": len(db_rows), 
            "headers": display_headers,
            "display_rows": display_rows,
            "geo_json_features": final_geojson_dict, 
            "map_html": final_geojson_dict 
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
