import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json

# --- Configuration ---
# Page config must be the first Streamlit command
st.set_page_config(layout="wide", page_title="Malaysian Weather Dashboard", page_icon="🇲🇾")

# --- City Data ---
def extract_coordinates_from_csv(file_path):
    """
    Reads a CSV file, extracts coordinates, and returns a clean DataFrame
    with duplicate cities removed.

    Args:
        file_path (str): The path to the postcode CSV file.

    Returns:
        pandas.DataFrame: A DataFrame with 'city', 'longitude', and 'latitude' columns.
    """
    try:
        # Read the CSV file using the 'latin1' encoding
        df = pd.read_csv(file_path, encoding='latin1')

        # --- Extract Latitude and Longitude ---
        coord_pattern = r'POINT\(([\d.-]+) ([\d.-]+)\)'
        extracted_coords = df['point_coord'].str.extract(coord_pattern)

        # Assign the extracted numbers to new columns
        df['latitude'] = pd.to_numeric(extracted_coords[0])
        df['longitude'] = pd.to_numeric(extracted_coords[1])

        # --- Create and Clean the DataFrame ---
        final_df = df[['city', 'longitude', 'latitude']]
        final_df = final_df.dropna()
        final_df = final_df.drop_duplicates(subset=['city']).reset_index(drop=True)

        return final_df

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def dataframe_to_cities_dict(df):
    """
    Converts the DataFrame into a dictionary with the specified format.

    Args:
        df (pandas.DataFrame): The DataFrame with city, latitude, and longitude.

    Returns:
        dict: A dictionary in the format {"City": {"lat": ..., "lon": ...}}.
    """
    # Rename columns to match the desired dictionary keys
    df = df.rename(columns={'latitude': 'lat', 'longitude': 'lon'})

    # Set 'city' as the index and convert the DataFrame to a dictionary
    cities_dict = df.set_index('city').to_dict('index')

    return cities_dict


# --- How to use it ---
file_path = 'postcode-list.csv'
coordinates_df = extract_coordinates_from_csv(file_path)

if coordinates_df is not None:
    # Convert the DataFrame to the desired dictionary format
    CITIES = dataframe_to_cities_dict(coordinates_df)

TIMEZONE = "Asia/Kuala_Lumpur"
WEATHER_CODES = {
    0: ("Clear", "☀️"), 1: ("Mainly clear", "🌤️"), 2: ("Partly cloudy", "⛅️"),
    3: ("Overcast", "☁️"), 45: ("Fog", "🌫️"), 48: ("Rime fog", "🌫️"),
    51: ("Light drizzle", "💧"), 53: ("Mod. drizzle", "💧"), 55: ("Dense drizzle", "💧"),
    61: ("Slight rain", "🌧️"), 63: ("Mod. rain", "🌧️"), 65: ("Heavy rain", "🌧️"),
    80: ("Rain showers", "🌦️"), 81: ("Rain showers", "🌦️"), 82: ("Violent showers", "🌦️"),
    95: ("Thunderstorm", "⛈️"),
}


# --- Data Fetching Functions ---
@st.cache_data(ttl=600)
def get_all_cities_data():
    lats = [city['lat'] for city in CITIES.values()]
    lons = [city['lon'] for city in CITIES.values()]
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={','.join(map(str, lats))}&longitude={','.join(map(str, lons))}"
        f"&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m"
    )
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None


@st.cache_data(ttl=600)
def get_forecast_data(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m"
        f"&hourly=temperature_2m,precipitation_probability"
        f"&daily=weather_code,temperature_2m_max,temperature_2m_min"
        f"&timezone={TIMEZONE}"
    )
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None


@st.cache_data(ttl=3600)
def get_historical_data(lat, lon):
    start_date = "2025-04-22"
    end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}"
        f"&daily=temperature_2m_mean,precipitation_sum"
        f"&timezone={TIMEZONE}"
    )
    response = requests.get(url)
    if response.status_code == 200 and 'daily' in response.json():
        return pd.DataFrame(response.json()['daily'])
    return None


# --- UI Layout ---
st.sidebar.title("Dashboard Controls")
sorted_cities = sorted(CITIES.keys())
page_options = ["--- HOME ---"] + sorted_cities
selected_page = st.sidebar.selectbox("Select a View", page_options, index=0)

st.title(f"🇲🇾 Malaysian Weather Dashboard")

# --- Page Content ---
if selected_page == "--- HOME ---":
    st.header("National Weather Overview")
    all_cities_data = get_all_cities_data()

    if all_cities_data:
        summary_data = []
        for i, city_name in enumerate(CITIES.keys()):
            city_api_data = all_cities_data[i]
            current = city_api_data['current']
            summary_data.append({
                "City": city_name, "lat": city_api_data["latitude"], "lon": city_api_data["longitude"],
                "Temp (°C)": current['temperature_2m'], "Rain (mm/hr)": current['precipitation'],
                "Humidity (%)": current['relative_humidity_2m'], "Wind (km/h)": current['wind_speed_10m']
            })
        summary_df = pd.DataFrame(summary_data)

        # --- NEW: Create columns for map and analytics ---
        col1, col2 = st.columns([3, 1])  # Give the map more space

        with col1:
            # --- Display Map ---
            summary_df['size'] = summary_df['Rain (mm/hr)'].apply(lambda x: x if x > 0 else 0.1)
            fig_map = px.scatter_mapbox(summary_df, lat="lat", lon="lon", color="Temp (°C)", size="size",
                                        hover_name="City",
                                        custom_data=['Temp (°C)', 'Rain (mm/hr)'],
                                        color_continuous_scale='RdYlGn_r',  # Green-to-Red scale
                                        size_max=20, zoom=4.5, mapbox_style="carto-positron",
                                        center={"lat": 4.21, "lon": 108.2})
            fig_map.update_traces(
                hovertemplate='<b>%{hovertext}</b><br><br>Temperature: %{customdata[0]:.1f}°C<br>Precipitation: %{customdata[1]:.1f} mm<extra></extra>')
            fig_map.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, legend_title_text='Temp (°C)')
            st.plotly_chart(fig_map, use_container_width=True)

        with col2:
            # --- NEW: Display Analytics Panel ---
            st.subheader("Live National Summary")

            avg_temp = summary_df['Temp (°C)'].mean()
            hottest_city = summary_df.loc[summary_df['Temp (°C)'].idxmax()]
            coldest_city = summary_df.loc[summary_df['Temp (°C)'].idxmin()]
            rainiest_city = summary_df.loc[summary_df['Rain (mm/hr)'].idxmax()]

            st.metric("National Average Temp", f"{avg_temp:.1f} °C")
            st.metric("Hottest City", f"{hottest_city['City']}", f"{hottest_city['Temp (°C)']:.1f} °C")
            st.metric("Coldest City", f"{coldest_city['City']}", f"{coldest_city['Temp (°C)']:.1f} °C")
            if rainiest_city['Rain (mm/hr)'] > 0:
                st.metric("Most Rainfall", f"{rainiest_city['City']}", f"{rainiest_city['Rain (mm/hr)']:.1f} mm/hr")
            else:
                st.metric("Most Rainfall", "No rain reported")

        # --- Display Summary Table ---
        st.subheader("Current Conditions Across Malaysia")
        st.dataframe(summary_df[["City", "Temp (°C)", "Rain (mm/hr)", "Humidity (%)", "Wind (km/h)"]],
                     use_container_width=True, hide_index=True)

    else:
        st.warning("Could not load national overview data.")

else:  # This is the detailed view for a single city
    selected_city = selected_page
    st.header(f"Detailed View: {selected_city}")
    city_lat = CITIES[selected_city]["lat"]
    city_lon = CITIES[selected_city]["lon"]
    forecast_data = get_forecast_data(city_lat, city_lon)
    historical_data_df = get_historical_data(city_lat, city_lon)

    if forecast_data:
        # This part is the same as your working detailed view code
        current = forecast_data['current']
        weather_desc, weather_icon = WEATHER_CODES.get(current['weather_code'], ("Unknown", ""))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Temperature", f"{current['temperature_2m']}°C", f"Feels like {current['apparent_temperature']}°C")
        c2.metric("Condition", weather_desc, weather_icon)
        c3.metric("Humidity", f"{current['relative_humidity_2m']}%")
        c4.metric("Wind", f"{current['wind_speed_10m']} km/h")

        hourly_df = pd.DataFrame(forecast_data['hourly'])
        hourly_df['time'] = pd.to_datetime(hourly_df['time'])
        now = pd.Timestamp.now(tz=TIMEZONE)
        try:
            hourly_df['time'] = hourly_df['time'].dt.tz_localize(TIMEZONE, ambiguous='infer')
        except TypeError:  # Already localized
            pass

        start_index = hourly_df['time'].searchsorted(now)
        chart_df = hourly_df.iloc[start_index:start_index + 24]

        fig_hourly = go.Figure()
        fig_hourly.add_trace(
            go.Scatter(x=chart_df['time'], y=chart_df['temperature_2m'], name='Temp (°C)', line=dict(color='#ff7f0e'),
                       yaxis='y1'))
        fig_hourly.add_trace(go.Bar(x=chart_df['time'], y=chart_df['precipitation_probability'], name='Precip. (%)',
                                    marker=dict(color='#1f77b4'), opacity=0.6, yaxis='y2'))
        fig_hourly.update_layout(height=400, title_text="Next 24h: Temp & Precipitation", yaxis=dict(title="°C"),
                                 yaxis2=dict(title="%", overlaying='y', side='right', range=[0, 100]),
                                 legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_hourly, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🗓️ 7-Day Forecast")
            daily_df = pd.DataFrame(forecast_data['daily'])
            daily_df['weather'] = daily_df['weather_code'].map(
                lambda code: f"{WEATHER_CODES.get(code, ('', ''))[1]} {WEATHER_CODES.get(code, ('', ''))[0]}")
            st.dataframe(daily_df[['time', 'temperature_2m_max', 'temperature_2m_min', 'weather']].rename(
                columns={'time': 'Date', 'temperature_2m_max': 'High', 'temperature_2m_min': 'Low',
                         'weather': 'Condition'}), use_container_width=True, hide_index=True, height=300)

        with col2:
            st.subheader("📊 Recent Monthly Rainfall")
            if historical_data_df is not None and not historical_data_df.empty:
                historical_data_df['time'] = pd.to_datetime(historical_data_df['time'])
                monthly_data = historical_data_df.groupby(historical_data_df['time'].dt.to_period('M')).agg(
                    {'precipitation_sum': 'sum'}).reset_index()
                monthly_data['time'] = monthly_data['time'].dt.strftime('%Y-%m')

                fig_hist = px.bar(monthly_data, x='time', y='precipitation_sum',
                                  labels={'time': 'Month', 'precipitation_sum': 'Total Rainfall (mm)'},
                                  color_discrete_sequence=['royalblue'])
                fig_hist.update_layout(height=300, title_text="Total Rainfall (since Apr 2025)")
                st.plotly_chart(fig_hist, use_container_width=True)
            else:
                st.info("No historical rainfall data available for this city.")
    else:
        st.error(f"Failed to fetch detailed weather data for {selected_page}.")