import json
from typing import List, Dict, Any

def create_folium_map(geojson_features: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not geojson_features:
        return {"type": "FeatureCollection", "features": []}

    return {
        "type": "FeatureCollection",
        "features": geojson_features
    }
