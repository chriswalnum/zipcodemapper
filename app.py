import streamlit as st
import folium
from geopy.geocoders import Nominatim
from streamlit_folium import st_folium
import pandas as pd
import time

st.title("Zip Code Mapper")

st.write(
    "Provide a comma-separated list of zip codes or upload a spreadsheet file "
    "(CSV or Excel) with a column of zip codes."
)

# Let the user choose the input method
input_method = st.radio("Choose input method:", ("Comma-separated list", "Spreadsheet Upload"))

zip_codes = []

if input_method == "Comma-separated list":
    zip_input = st.text_area("Enter comma-separated zip codes", "10001, 94105")
    if zip_input:
        zip_codes = [z.strip() for z in zip_input.split(",") if z.strip()]
else:
    uploaded_file = st.file_uploader("Upload a spreadsheet file (CSV or Excel)", type=["csv", "xlsx"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.write("Preview of uploaded data:")
            st.dataframe(df.head())
            
            # Allow user to select the column that contains zip codes
            zip_column = st.selectbox("Select the column with zip codes", df.columns)
            zip_codes = df[zip_column].dropna().astype(str).tolist()
        except Exception as e:
            st.error(f"Error processing file: {e}")

# Initialize geocoder and map
geolocator = Nominatim(user_agent="zip_mapper")
map_center = [37.0902, -95.7129]  # Center on the US
m = folium.Map(location=map_center, zoom_start=4)

# Cache to store previously geocoded results
geocode_cache = {}

if zip_codes:
    st.write("Mapping zip codes...")
    for z in zip_codes:
        z_str = z.strip()
        if not z_str:
            continue
        
        # If we already have coordinates cached, use them
        if z_str in geocode_cache:
            coords = geocode_cache[z_str]
        else:
            # Throttle requests to avoid hitting rate limits
            time.sleep(1)
            try:
                # Restrict search to US for better results
                location = geolocator.geocode({"postalcode": z_str, "country": "USA"})
                if location:
                    coords = (location.latitude, location.longitude)
                    geocode_cache[z_str] = coords
                else:
                    st.warning(f"Could not geocode zip code: {z_str}")
                    continue
            except Exception as e:
                st.error(f"Error geocoding {z_str}: {e}")
                continue
        
        # Add marker to map if we have valid coordinates
        if coords:
            folium.Marker(
                [coords[0], coords[1]],
                popup=f"Zip: {z_str}"
            ).add_to(m)

# Display the map
st_folium(m, width=700)
