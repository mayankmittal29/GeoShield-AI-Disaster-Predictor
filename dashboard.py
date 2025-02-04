import streamlit as st
import ee
import os
import requests
import geemap.foliumap as geemap
from datetime import datetime
import time
import folium

# Set page config as the first Streamlit command
st.set_page_config(
    page_title="Interactive Globe Satellite Image Capturing and Natural Disaster Predictor",
    layout="wide"
)

# Initialize Earth Engine with service account credentials
service_account = ''
credentials = ee.ServiceAccountCredentials(service_account, '')

try:
    ee.Initialize(credentials)
except Exception as e:
    st.error(f"Earth Engine initialization error: {e}")

# Create directory for storing images if it doesn't exist
os.makedirs("satellite_images", exist_ok=True)

def get_satellite_image(lat, lon, size_km=5):
    """
    Fetch a satellite image of a specified region using Google Earth Engine.
    """
    try:
        km_to_deg = size_km / 111.32
        region = ee.Geometry.Rectangle([
            lon - km_to_deg / 2, lat - km_to_deg / 2,
            lon + km_to_deg / 2, lat + km_to_deg / 2
        ])
        image = (ee.ImageCollection('COPERNICUS/S2_SR')
                .filterBounds(region)
                .filterDate(ee.Date('2024-01-01'), ee.Date(datetime.now().strftime('%Y-%m-%d')))
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
                .sort('system:time_start', False)
                .first())
        if image is None:
            return None, "No clear images available for this location", None

        vis_params = {
            'min': 0,
            'max': 3000,
            'bands': ['B4', 'B3', 'B2'],
            'gamma': 1.4
        }

        url = image.getThumbURL({
            'region': region,
            'dimensions': '2048',
            'format': 'png',
            'bands': ['B4', 'B3', 'B2'],
            'min': 0,
            'max': 3000,
            'gamma': 1.4
        })

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"satellite_images/sat_{lat:.4f}_{lon:.4f}_{timestamp}.png"
        
        response = requests.get(url)
        with open(filename, 'wb') as f:
            f.write(response.content)

        image_date = ee.Date(image.get('system:time_start')).format('YYYY-MM-dd').getInfo()
        return filename, None, image_date

    except Exception as e:
        return None, str(e), None

def create_lat_lon_graticules():
    """Create latitude and longitude graticules"""
    graticules = []
    
    for lat in range(-90, 91, 10):
        points = [[lat, lon] for lon in range(-180, 181, 2)]
        graticules.append({
            'coords': points,
            'label': f'{lat}°N' if lat > 0 else (f'{abs(lat)}°S' if lat < 0 else 'Equator')
        })
    
    for lon in range(-180, 181, 10):
        points = [[lat, lon] for lat in range(-90, 91, 2)]
        graticules.append({
            'coords': points,
            'label': f'{lon}°E' if lon > 0 else (f'{abs(lon)}°W' if lon < 0 else 'Prime Meridian')
        })
    
    return graticules

def get_current_location():
    """Fetch the user's current location based on IP address."""
    try:
        response = requests.get("https://ipinfo.io/json")
        data = response.json()
        location = data.get("loc").split(",")
        latitude = float(location[0])
        longitude = float(location[1])
        return latitude, longitude
    except Exception as e:
        st.error(f"Error fetching location: {e}")
        return None, None

def main():
    st.title("🌍 Interactive Globe Satellite Image Capturing and Natural Disaster Predictor")

    # Initialize session state variables if they don't exist
    if 'marker_location' not in st.session_state:
        st.session_state.marker_location = None
    if 'latitude' not in st.session_state:
        st.session_state.latitude = 0.0
    if 'longitude' not in st.session_state:
        st.session_state.longitude = 0.0
    if 'alert' not in st.session_state:
        st.session_state.alert = None
    if 'alert_time' not in st.session_state:
        st.session_state.alert_time = None

    # Create two columns for layout
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("Map View")
        # Add a dropdown to select map type
        map_type = st.selectbox("Select Map Type", ["Labeled Map", "Terrain Map"])

        # Create the Map with the selected type
        if map_type == "Labeled Map":
            m = geemap.Map(center=[20, 0], zoom=2)  # Using geemap for labeled map
            folium.TileLayer('OpenStreetMap', attr='OpenStreetMap contributors').add_to(m)
        else:  # Terrain Map
            m = geemap.Map(center=[20, 0], zoom=2, basemap='HYBRID')  # Using hybrid basemap
        folium.LayerControl().add_to(m)

        # Add graticules (lat/lon grid)
        graticules = create_lat_lon_graticules()
        for g in graticules:
            folium.PolyLine(
                locations=[[p[0], p[1]] for p in g['coords']],
                weight=0.5,
                color='white',
                opacity=0.5,
                popup=g['label']
            ).add_to(m)

        m.add_child(folium.LatLngPopup())

        # Add marker for selected location or current location
        if st.session_state.marker_location:
            folium.Marker(
                location=st.session_state.marker_location,
                popup='Selected Location'
            ).add_to(m)
        elif st.session_state.latitude and st.session_state.longitude:
            folium.Marker(
                location=(st.session_state.latitude, st.session_state.longitude),
                popup='Current Location',
                icon=folium.Icon(color='blue')
            ).add_to(m)

        # Display the map
        m.to_streamlit(height=600)

    with col2:
        st.header("Select Location")
        
        # Button to fetch real-time location
        if st.button("Get My Current Location"):
            lat, lon = get_current_location()
            if lat and lon:
                st.session_state.latitude = lat
                st.session_state.longitude = lon
                st.session_state.marker_location = (lat, lon)  # Mark on the map
                st.experimental_rerun()
            else:
                st.error("Could not retrieve your location.")

        # Coordinate inputs
        lat = st.number_input("Enter Latitude", value=st.session_state.latitude, format="%.6f")
        lon = st.number_input("Enter Longitude", value=st.session_state.longitude, format="%.6f")
        
        # Update location button
        if st.button("Update Location"):
            st.session_state.marker_location = (lat, lon)
            st.session_state.latitude = lat
            st.session_state.longitude = lon
            st.experimental_rerun()
        
        # Display temporary alerts
        current_time = time.time()
        if st.session_state.alert and st.session_state.alert_time:
            if current_time - st.session_state.alert_time < 3:
                if "error" in st.session_state.alert:
                    st.error(st.session_state.alert)
                elif "success" in st.session_state.alert:
                    st.success(st.session_state.alert)
            else:
                st.session_state.alert = None

        # Button to capture satellite image
        if st.button("Capture Satellite Image"):
            if st.session_state.marker_location or (st.session_state.latitude and st.session_state.longitude):
                lat = st.session_state.marker_location[0] if st.session_state.marker_location else st.session_state.latitude
                lon = st.session_state.marker_location[1] if st.session_state.marker_location else st.session_state.longitude
                filename, error_msg, image_date = get_satellite_image(lat, lon)
                if error_msg:
                    st.session_state.alert = f"Error: {error_msg}"
                    st.session_state.alert_time = time.time()
                else:
                    st.session_state.alert = f"Success: Image captured on {image_date}!"
                    st.session_state.alert_time = time.time()
                    st.image(filename, caption='Captured Satellite Image', use_column_width=True)
            else:
                st.error("Please select a location first.")
        st.markdown("---")
        st.markdown("""
        ### How to use:
        1. Navigate the map by dragging.
        2. Zoom in/out using scroll wheel.
        3. Enter the latitude and longitude manually and click on 'Update Location' or mark a point on the map to get its coordinates.
        4. Click on 'Get My Current Location' to get my device current coordinates and satellite image.
        5. Click 'Capture Satellite Image' to capture a 5x5 km² area.
        """)

if __name__ == "__main__":
    main()
