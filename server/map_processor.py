import folium
import json
from typing import List, Dict, Any

def create_folium_map(geojson_features: List[Dict[str, Any]]) -> str:
    if not geojson_features:
        return ""

    start_lat, start_lon = 19.0760, 72.8777 
    
    for feature in geojson_features:
        geom = feature.get('geometry')
        if geom and 'coordinates' in geom:
            coords = geom['coordinates']
            geom_type = geom['type']
            
            if geom_type == 'Point' and len(coords) >= 2:
                start_lat, start_lon = coords[1], coords[0]
                break
            
    m = folium.Map(location=[start_lat, start_lon], zoom_start=13, tiles='CartoDB.DarkMatter')

    geojson_layer = {
        "type": "FeatureCollection",
        "features": geojson_features
    }

    def style_function(feature):
        return {
            'fillColor': '#42b883', 
            'color': '#111827',
            'weight': 1,
            'fillOpacity': 0.5
        }
    
    folium.GeoJson(
        geojson_layer,
        name='OSM Data',
        style_function=style_function,
        tooltip=folium.GeoJsonTooltip(
            fields=[k for k in geojson_features[0]['properties'].keys()],
            aliases=[k.replace('_', ' ').title() for k in geojson_features[0]['properties'].keys()],
            localize=True
        ) if geojson_features and geojson_features[0].get('properties') else None
    ).add_to(m)
    
    coords_for_bounds = []
    
    for feature in geojson_features:
        geom = feature.get('geometry')
        if not geom: continue
        
        geom_type = geom['type']
        coords = geom['coordinates']
        
        if geom_type == 'Point':
            coords_for_bounds.append([coords[1], coords[0]]) 
        elif geom_type in ['LineString', 'MultiPoint']:
            for lon, lat in coords:
                 coords_for_bounds.append([lat, lon])
        elif geom_type in ['Polygon']:
            for lon, lat in coords[0]:
                 coords_for_bounds.append([lat, lon])


    if coords_for_bounds:
        lats = [c[0] for c in coords_for_bounds]
        lons = [c[1] for c in coords_for_bounds]
        m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])

    return m._repr_html_()

