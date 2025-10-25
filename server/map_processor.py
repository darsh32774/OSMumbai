# server/map_processor.py
import folium
import json
from typing import List, Dict, Any

def create_folium_map(geojson_features: List[Dict[str, Any]]) -> str:
    """
    Creates a Folium map centered on Mumbai and adds GeoJSON features.
    
    Args:
        geojson_features: List of GeoJSON Feature dictionaries (pre-processed by server).
    
    Returns:
        HTML string of the Folium map.
    """
    if not geojson_features:
        return ""

    # Determine initial map center from the first feature's geometry
    start_lat, start_lon = 19.0760, 72.8777 # Default center (Mumbai)
    
    # Try to find a sensible center based on the features
    for feature in geojson_features:
        geom = feature.get('geometry')
        if geom and 'coordinates' in geom:
            coords = geom['coordinates']
            geom_type = geom['type']
            
            if geom_type == 'Point' and len(coords) >= 2:
                # Folium uses (lat, lon), GeoJSON uses (lon, lat)
                start_lat, start_lon = coords[1], coords[0]
                break
            # For polygons/lines, calculating a center is complex, so we'll rely on fit_bounds later.
            
    # 1. Initialize Map
    m = folium.Map(location=[start_lat, start_lon], zoom_start=13, tiles='CartoDB.DarkMatter')

    # 2. Prepare GeoJSON FeatureCollection
    geojson_layer = {
        "type": "FeatureCollection",
        "features": geojson_features
    }

    # Style function for non-point geometries
    def style_function(feature):
        return {
            'fillColor': '#42b883', # Tailwind green/blue-ish
            'color': '#111827',
            'weight': 1,
            'fillOpacity': 0.5
        }
    
    # 3. Add GeoJson layer
    # We use a single GeoJson layer for all features (points, lines, polygons)
    folium.GeoJson(
        geojson_layer,
        name='OSM Data',
        style_function=style_function,
        # Create tooltip using all properties except 'geojson'
        tooltip=folium.GeoJsonTooltip(
            fields=[k for k in geojson_features[0]['properties'].keys()],
            aliases=[k.replace('_', ' ').title() for k in geojson_features[0]['properties'].keys()],
            localize=True
        ) if geojson_features and geojson_features[0].get('properties') else None
    ).add_to(m)
    
    # 4. Fit map bounds to show all data
    # We must calculate bounds manually as Folium GeoJson doesn't auto-fit reliably
    coords_for_bounds = []
    
    for feature in geojson_features:
        geom = feature.get('geometry')
        if not geom: continue
        
        geom_type = geom['type']
        coords = geom['coordinates']
        
        if geom_type == 'Point':
            coords_for_bounds.append([coords[1], coords[0]]) # lat, lon
        elif geom_type in ['LineString', 'MultiPoint']:
            for lon, lat in coords:
                 coords_for_bounds.append([lat, lon])
        elif geom_type in ['Polygon']:
            # Use the first ring's coordinates
            for lon, lat in coords[0]:
                 coords_for_bounds.append([lat, lon])


    if coords_for_bounds:
        lats = [c[0] for c in coords_for_bounds]
        lons = [c[1] for c in coords_for_bounds]
        m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])

    # ⚠️ FIX: Return only the HTML content
    return m._repr_html_()

