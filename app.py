import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import time

# Cache geocoding so we don't hit Nominatim repeatedly for the same ZIP
@st.cache_data
def geocode_zip(zip_code: str):
    geolocator = Nominatim(user_agent="zip_mapper")
    try:
        # Restrict search to US
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
        "and click **Submit**. Each ZIP code will be highlighted with a circle on the map."
    )

    # Form so the map only updates on submit
    with st.form("zip_form"):
        zip_input = st.text_area("Enter comma-separated ZIP codes", "06106, 06604, 06840, 06804")
        zoom_choice = st.selectbox("Map Zoom Level", ["National", "Auto Region"])
        radius = st.number_input("Circle radius (in meters)", value=1000, step=100)
        submitted = st.form_submit_button("Submit")

    # Default to US map
    lat_default, lon_default = 37.0902, -95.7129
    zoom_default = 4

    if submitted:
        # Parse ZIP codes
        zip_codes = [z.strip() for z in zip_input.split(",") if z.strip()]

        coords_list = []
        for z in zip_codes:
            coords = geocode_zip(z)
            time.sleep(1)  # Throttle to avoid Nominatim rate limits
            if coords:
                coords_list.append((coords[0], coords[1], z))
            else:
                st.error(f"Could not geocode ZIP: {z}")

        # Determine map center
        if zoom_choice == "Auto Region" and coords_list:
            min_lat = min(c[0] for c in coords_list)
            max_lat = max(c[0] for c in coords_list)
            min_lon = min(c[1] for c in coords_list)
            max_lon = max(c[1] for c in coords_list)
            center_lat = (min_lat + max_lat) / 2
            center_lon = (min_lon + max_lon) / 2
            m = folium.Map(location=[center_lat, center_lon], zoom_start=5)
        else:
            # National default
            m = folium.Map(location=[lat_default, lon_default], zoom_start=zoom_default)

        # Highlight each ZIP with a circle
        for lat, lon, z in coords_list:
            folium.Circle(
                location=[lat, lon],
                radius=radius,
                color="red",
                fill=True,
                fill_color="red",
                popup=f"ZIP: {z}"
            ).add_to(m)

        # Display the map
        st_folium(m, width=700)
    else:
        # Show default map before submission
        m = folium.Map(location=[lat_default, lon_default], zoom_start=zoom_default)
        st_folium(m, width=700)

if __name__ == "__main__":
    main()
