import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import pandas as pd
import time
import requests
import geopandas as gpd
from shapely.geometry import Point

#####################
#   STATE DATASET   #
#####################
@st.cache_data
def load_state_boundaries(state_abbrev: str) -> gpd.GeoDataFrame:
    """
    Fetch GeoJSON boundaries for the given state abbreviation.
    Currently implemented only for Connecticut (CT).
    Add more states as needed in the 'state_data_urls' dictionary.
    """
    state_data_urls = {
        # Example for CT Town Boundaries (ArcGIS FeatureServer)
        "CT": "https://services5.arcgis.com/8IcYZYgy9FrlXPLQ/arcgis/rest/services/Town_Boundaries/FeatureServer/0/query?where=1=1&outFields=*&f=geojson",
        # Add more states below, e.g. "MA": "some URL for Massachusetts data"
    }
    url = state_data_urls.get(state_abbrev)
    if not url:
        return None  # We don't have data for that state
    
    try:
        gdf = gpd.read_file(url)
        return gdf
    except Exception as e:
        st.warning(f"Failed to load boundaries for {state_abbrev}: {e}")
        return None

#####################
#    GEOCODING      #
#####################
@st.cache_data
def geocode_zip(zip_code: str):
    """
    Geocode a ZIP code using Nominatim, returning (lat, lon) or None.
    Caches results to avoid repeated lookups.
    """
    geolocator = Nominatim(user_agent="zip_mapper")
    try:
        location = geolocator.geocode({"postalcode": zip_code, "country": "USA"})
        if location:
            return (location.latitude, location.longitude)
    except:
        pass
    return None

def main():
    st.title("Zip Code Mapper")

    st.write(
        "Enter one or more ZIP codes (comma-separated), pick a zoom level, "
        "and click **Submit**. If boundaries are available for your chosen state, "
        "they will be highlighted."
    )

    #########################
    #   USER INPUT FORM     #
    #########################
    with st.form("zip_form"):
        zip_input = st.text_area(
            "Enter comma-separated ZIP codes",
            "06106, 06604, 06840, 06804"
        )

        # Let the user choose how to center/zoom the map
        zoom_choice = st.selectbox(
            "Map Zoom Level",
            ["National", "State", "Auto Region"]
        )

        # If "State" is chosen, ask which state to highlight
        # (only CT is demonstrated below; add more as needed)
        chosen_state = None
        if zoom_choice == "State":
            chosen_state = st.selectbox("Select a State (2-letter code)", ["CT", "MA", "NY"])
            # The code only has boundary data for CT by default.
            # You must add data for MA, NY, etc. in the load_state_boundaries function above.

        submitted = st.form_submit_button("Submit")

    #########################
    #   INITIALIZE MAP      #
    #########################
    # Default to a US-centered map
    # We'll adjust if the user chooses "State" or "Auto Region"
    lat_default, lon_default = 37.0902, -95.7129
    zoom_default = 4

    # If user chooses "State" and we have a known center:
    state_centers = {
        "CT": (41.6032, -73.0877, 8),  # lat, lon, zoom
        "MA": (42.4072, -71.3824, 8),
        "NY": (43.0000, -75.0000, 7),
    }

    if submitted:
        zip_codes = [z.strip() for z in zip_input.split(",") if z.strip()]

        # Geocode each ZIP
        coords_list = []
        for z in zip_codes:
            c = geocode_zip(z)
            time.sleep(1)  # Throttle calls to Nominatim
            if c:
                coords_list.append((c[0], c[1], z))
            else:
                st.error(f"Could not geocode ZIP: {z}")

        #########################
        #  DETERMINE MAP VIEW   #
        #########################
        if zoom_choice == "State" and chosen_state in state_centers:
            # Use a fixed center for the chosen state
            lat_default, lon_default, zoom_default = state_centers[chosen_state]
            m = folium.Map(location=[lat_default, lon_default], zoom_start=zoom_default)
        elif zoom_choice == "Auto Region" and coords_list:
            # Center the map around the bounding box of all geocoded points
            min_lat = min(c[0] for c in coords_list)
            max_lat = max(c[0] for c in coords_list)
            min_lon = min(c[1] for c in coords_list)
            max_lon = max(c[1] for c in coords_list)

            # Center is the midpoint of min/max
            center_lat = (min_lat + max_lat) / 2.0
            center_lon = (min_lon + max_lon) / 2.0

            # Rough zoom: narrower bounding box => closer zoom
            # We'll just pick a default, or you could do something more precise
            m = folium.Map(location=[center_lat, center_lon], zoom_start=6)
        else:
            # Default national map
            m = folium.Map(location=[lat_default, lon_default], zoom_start=zoom_default)

        #########################
        #  HIGHLIGHT BOUNDARIES #
        #########################
        # If the user selected "State" and we have boundary data, highlight relevant towns
        if zoom_choice == "State" and chosen_state:
            state_gdf = load_state_boundaries(chosen_state)
            if state_gdf is not None:
                # Convert user geocodes into shapely Points
                for lat, lon, z in coords_list:
                    point = Point(lon, lat)
                    # Find polygons that contain this point
                    matches = state_gdf[state_gdf.geometry.contains(point)]
                    if not matches.empty:
                        # Highlight each matching polygon
                        folium.GeoJson(
                            matches.geometry.__geo_interface__,
                            style_function=lambda x: {
                                "fillColor": "#ff0000",
                                "color": "#ff0000",
                                "fillOpacity": 0.4,
                            },
                            highlight_function=lambda x: {
                                "fillColor": "#ffff00",
                                "color": "#ffff00",
                            },
                            name=f"{chosen_state} boundary for {z}",
                        ).add_to(m)

                    # Add a pin for the ZIP code
                    folium.Marker(
                        [lat, lon],
                        popup=f"ZIP: {z}"
                    ).add_to(m)
            else:
                st.warning(f"No boundary data available for {chosen_state}, or it failed to load. Showing pins only.")
                for lat, lon, z in coords_list:
                    folium.Marker(
                        [lat, lon],
                        popup=f"ZIP: {z}"
                    ).add_to(m)
        else:
            # Just place pins for each ZIP
            for lat, lon, z in coords_list:
                folium.Marker(
                    [lat, lon],
                    popup=f"ZIP: {z}"
                ).add_to(m)

        # Render the map
        st_folium(m, width=700)

    else:
        # Before submission, show a default national map
        m = folium.Map(location=[lat_default, lon_default], zoom_start=zoom_default)
        st_folium(m, width=700)

if __name__ == "__main__":
    main()
