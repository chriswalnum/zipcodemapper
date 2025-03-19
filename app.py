import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import pandas as pd
import time
import requests
import geopandas as gpd
from shapely.geometry import Point

# Cache the town boundaries so we don't download them repeatedly.
@st.cache_data
def load_ct_town_boundaries():
    """
    Load Connecticut town boundaries from a public ArcGIS GeoJSON endpoint.
    Returns a GeoDataFrame with polygons for each town.
    """
    url = (
        "https://opendata.arcgis.com/api/v3/datasets/"
        "7f3da7fa4fe2484c90e010b0b8453927_0/"
        "downloads/data?format=geojson&spatialRefId=4326"
    )
    gdf = gpd.read_file(url)
    return gdf

# Cache geocoding results to avoid repeated lookups for the same ZIP code.
@st.cache_data
def geocode_zip(zip_code):
    """
    Geocode a ZIP code using Nominatim, returning a (lat, lon) tuple or None.
    """
    geolocator = Nominatim(user_agent="zip_mapper")
    try:
        location = geolocator.geocode({"postalcode": zip_code, "country": "USA"})
        if location:
            return (location.latitude, location.longitude)
    except Exception:
        pass
    return None

def main():
    st.title("Zip Code Mapper")

    st.write(
        "Enter one or more ZIP codes (comma-separated), choose your desired zoom level, "
        "and then click Submit. If the ZIP code is in Connecticut, the town boundary will "
        "be highlighted on the map."
    )

    # Create a form so the user has a single "Submit" button
    with st.form("zip_form"):
        zip_input = st.text_area("Enter comma-separated ZIP codes", "06106, 06604, 06840, 06804")
        zoom_option = st.selectbox("Map Zoom Level", ["Connecticut", "National"])
        submitted = st.form_submit_button("Submit")

    # Load town boundaries once (cached)
    ct_towns = load_ct_town_boundaries()

    # Initialize the map
    if zoom_option == "Connecticut":
        # Center roughly on CT
        m = folium.Map(location=[41.6032, -73.0877], zoom_start=8)
    else:
        # Center on the US
        m = folium.Map(location=[37.0902, -95.7129], zoom_start=4)

    if submitted:
        # Parse ZIP codes from user input
        zip_codes = [z.strip() for z in zip_input.split(",") if z.strip()]

        st.write(f"Mapping {len(zip_codes)} ZIP code(s)...")

        for z in zip_codes:
            coords = geocode_zip(z)
            time.sleep(1)  # Throttle requests to Nominatim

            if coords:
                lat, lon = coords
                point = Point(lon, lat)

                # Find which CT town (if any) contains this geocoded point
                # Note: Some ZIPs in border areas might not match perfectly
                matching_towns = ct_towns[ct_towns.geometry.contains(point)]

                if not matching_towns.empty:
                    # Highlight the polygon(s) for this town
                    folium.GeoJson(
                        matching_towns.geometry.__geo_interface__,
                        style_function=lambda x: {
                            "fillColor": "#ff0000",
                            "color": "#ff0000",
                            "fillOpacity": 0.4,
                        },
                        highlight_function=lambda x: {
                            "fillColor": "#ffff00",
                            "color": "#ffff00",
                        },
                        name=f"Town for {z}",
                    ).add_to(m)

                    # Optionally add a marker for the ZIP's geocoded center
                    folium.Marker(
                        [lat, lon],
                        popup=f"Zip: {z}"
                    ).add_to(m)
                else:
                    st.warning(f"ZIP {z} is not within CT boundaries or no matching polygon found.")
            else:
                st.error(f"Could not geocode ZIP: {z}")

    # Render the map
    st_folium(m, width=700)

if __name__ == "__main__":
    main()
