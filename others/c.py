import streamlit as st
import ee
import os
import requests
import geemap.foliumap as geemap
from datetime import datetime

# Set page config as the first Streamlit command
st.set_page_config(
    page_title="Interactive Globe Satellite Image Capture",
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

# def get_satellite_image(lat, lon, size_km=100):
#     """
#     Fetch a satellite image of a specified region using Google Earth Engine.
#     """
#     try:
#         # Convert size from km to degrees (approximate)
#         km_to_deg = size_km / 10
        
#         # Define the region (size_km x size_km square)
#         region = ee.Geometry.Rectangle([
#             lon - km_to_deg / 2, lat - km_to_deg / 2,
#             lon + km_to_deg / 2, lat + km_to_deg / 2
#         ])

#         # Get the most recent Sentinel-2 image
#         image = (ee.ImageCollection('COPERNICUS/S2_SR')
#                 .filterBounds(region)
#                 .filterDate(ee.Date('2024-01-01'), ee.Date(datetime.now().strftime('%Y-%m-%d')))
#                 .sort('system:time_start', False)
#                 .first())

#         # Create visualization parameters
#         vis_params = {
#             'min': 0,
#             'max': 3000,
#             'bands': ['B4', 'B3', 'B2']
#         }

#         # Generate download URL
#         url = image.getThumbURL({
#             'region': region,
#             'dimensions': '512',
#             'format': 'png',
#             'bands': ['B4', 'B3', 'B2'],
#             'min': 0,
#             'max': 3000
#         })

#         # Download and save the image
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#         filename = f"satellite_images/sat_{lat:.4f}_{lon:.4f}_{timestamp}.png"
        
#         response = requests.get(url)
#         with open(filename, 'wb') as f:
#             f.write(response.content)

#         return filename, None

#     except Exception as e:
#         return None, str(e)
def get_satellite_image(lat, lon, size_km=5):  # Changed to 20 km for better quality
    """
    Fetch a satellite image of a specified region using Google Earth Engine.
    """
    try:
        # Convert size from km to degrees (approximate)
        km_to_deg = size_km / 111.32
        
        # Define the region (size_km x size_km square)
        region = ee.Geometry.Rectangle([
            lon - km_to_deg / 2, lat - km_to_deg / 2,
            lon + km_to_deg / 2, lat + km_to_deg / 2
        ])

        # Get the most recent Sentinel-2 image with less than 20% cloud cover
        image = (ee.ImageCollection('COPERNICUS/S2_SR')
                .filterBounds(region)
                .filterDate(ee.Date('2024-01-01'), ee.Date(datetime.now().strftime('%Y-%m-%d')))
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))  # Filter for cloud cover
                .sort('system:time_start', False)
                .first())

        # Create visualization parameters
        vis_params = {
            'min': 0,
            'max': 3000,
            'bands': ['B4', 'B3', 'B2']
        }

        # Generate download URL
        url = image.getThumbURL({
            'region': region,
            'dimensions': '512',  # You can adjust this for different resolutions
            'format': 'png',
            'bands': ['B4', 'B3', 'B2'],
            'min': 0,
            'max': 3000
        })

        # Download and save the image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"satellite_images/sat_{lat:.4f}_{lon:.4f}_{timestamp}.png"
        
        response = requests.get(url)
        with open(filename, 'wb') as f:
            f.write(response.content)

        return filename, None

    except Exception as e:
        return None, str(e)


def main():
    st.title("🌍 Interactive Globe Satellite Image Capture")

    # Create two columns for layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Add the Map interface
        m = geemap.Map()
        m.add_basemap('HYBRID')
        
        # Store location for marker and drawn rectangle
        marker_location = st.session_state.get('marker_location', None)
        drawn_bounds = st.session_state.get('drawn_bounds', None)
        
        # Add interactive marker to the map
        if 'marker_location' in st.session_state:
            marker_lat, marker_lon = st.session_state['marker_location']
            m.add_marker(location=(marker_lat, marker_lon), popup='Selected Location')

        # Display the map in Streamlit
        m.to_streamlit(height=600)

    with col2:
        st.header("Select Location")
        
        # Allow user to manually input coordinates
        lat = st.number_input("Enter Latitude", value=st.session_state.get('latitude', 0.0), format="%.6f")
        lon = st.number_input("Enter Longitude", value=st.session_state.get('longitude', 0.0), format="%.6f")
        
        # If manual input changes, update the session state
        if st.button("Update Location"):
            st.session_state['marker_location'] = (lat, lon)
            st.session_state['latitude'] = lat
            st.session_state['longitude'] = lon
            st.experimental_rerun()
        
        # Fetch satellite image button
        if st.button("Fetch Satellite Image"):
            if lat != 0.0 and lon != 0.0:
                with st.spinner("Fetching satellite image..."):
                    filename, error = get_satellite_image(lat, lon)
                    
                    if filename:
                        st.success("Image captured successfully!")
                        st.image(filename, caption="10x10 km² Satellite Image", use_column_width=True)
                        st.download_button(
                            label="Download Image",
                            data=open(filename, "rb").read(),
                            file_name=os.path.basename(filename),
                            mime="image/png"
                        )
                    else:
                        st.error(f"Error fetching image: {error}")
            else:
                st.warning("Please enter valid latitude and longitude.")

        # Handle rectangle-based download
        if st.session_state.get('drawn_bounds'):
            if st.button("Fetch Image for Drawn Area"):
                coords = st.session_state['drawn_bounds']
                center_lat = (coords[0][1] + coords[2][1]) / 2
                center_lon = (coords[0][0] + coords[2][0]) / 2
                with st.spinner("Fetching satellite image for drawn area..."):
                    filename, error = get_satellite_image(center_lat, center_lon)
                    
                    if filename:
                        st.success("Image captured successfully for drawn area!")
                        st.image(filename, caption="10x10 km² Satellite Image", use_column_width=True)
                        st.download_button(
                            label="Download Image",
                            data=open(filename, "rb").read(),
                            file_name=os.path.basename(filename),
                            mime="image/png"
                        )
                    else:
                        st.error(f"Error fetching image: {error}")

        # Add some helpful information
        st.markdown("---")
        st.markdown("""
        ### How to use:
        1. Navigate the map by dragging.
        2. Zoom in/out using scroll wheel.
        3. Enter the latitude and longitude manually or mark a point on the map.
        4. Draw a rectangle to fetch an image for a region.
        5. Click 'Fetch Satellite Image' to capture a 10x10 km² area.
        """)

if __name__ == "__main__":
    main()