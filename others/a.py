import streamlit as st
import ee
import os
import requests
import geemap.foliumap as geemap
from datetime import datetime
import time
import folium
import pydeck as pdk

# Set page config as the first Streamlit command
st.set_page_config(
    page_title="Interactive Globe Satellite Image Capturing and Natural Disaster Predictor",
    layout="wide"
)

# Initialize Earth Engine with service account credentials
service_account = 'mayank-mittal@satellite-viewer-439814.iam.gserviceaccount.com'
credentials = ee.ServiceAccountCredentials(service_account, 'key/satellite-viewer-439814-f53069cfb451.json')

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

        # Lat/Lng coordinates displayed on hover
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

        # Click event to capture coordinates (using LatLngPopup)
        if st.session_state.marker_location is None:
            st.warning("Click on the map to select a location.")

        # User can capture a satellite image by clicking
        if st.session_state.marker_location:
            lat, lon = st.session_state.marker_location
            st.markdown(f"Coordinates: {lat:.4f}, {lon:.4f}")

        # Add 3D Globe Visualization using pydeck
        st.header("3D Globe Visualization")
        view_state = pdk.ViewState(
            latitude=st.session_state.latitude or 20,
            longitude=st.session_state.longitude or 0,
            zoom=1,
            pitch=45,
            bearing=0,
        )

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=[{
                'position': [st.session_state.longitude, st.session_state.latitude],
                'size': 1000,  # Adjust the size of the point
                'color': [255, 0, 0],
                'label': 'Selected Location'
            }],
            get_position='[longitude, latitude]',
            get_radius="size",
            radius_scale=10,
            pickable=True,
            extruded=True,
            elevation_scale=50,
            get_fill_color='color',
            get_line_color=[0, 0, 0],
        )

        deck = pdk.Deck(layers=[layer], initial_view_state=view_state)
        st.pydeck_chart(deck)

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
        lat = st.number_input("Enter Latitude", value=st.session_state.latitude, format="%.6f", step=0.000001)
        lon = st.number_input("Enter Longitude", value=st.session_state.longitude, format="%.6f", step=0.000001)
        
        if st.button("Select Location"):
            st.session_state.marker_location = (lat, lon)
            st.experimental_rerun()

        # Capture Satellite Image Button
        if st.session_state.marker_location:
            if st.button("Capture Satellite Image"):
                image_path, error_message, image_date = get_satellite_image(lat, lon)
                if error_message:
                    st.error(error_message)
                else:
                    st.image(image_path, caption=f"Satellite Image captured on {image_date}")

if __name__ == "__main__":
    main()
