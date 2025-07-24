import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- Configuration ---
# Page config must be the first Streamlit command
st.set_page_config(layout="wide", page_title="Malaysian Weather Dashboard", page_icon="🇲🇾")

# --- City Data ---
CITIES = {
    "Kangar": {"lat": 6.44, "lon": 100.19}, "Alor Setar": {"lat": 6.12, "lon": 100.37},
    "George Town": {"lat": 5.41, "lon": 100.33}, "Butterworth": {"lat": 5.40, "lon": 100.37},
    "Bukit Mertajam": {"lat": 5.36, "lon": 100.46}, "Seberang Jaya": {"lat": 5.39, "lon": 100.40},
    "Sungai Petani": {"lat": 5.65, "lon": 100.49}, "Taiping": {"lat": 4.85, "lon": 100.73},
    "Ipoh": {"lat": 4.60, "lon": 101.08}, "Batu Gajah": {"lat": 4.47, "lon": 101.04},
    "Teluk Intan": {"lat": 4.02, "lon": 101.02}, "Klang": {"lat": 3.03, "lon": 101.45},
    "Shah Alam": {"lat": 3.07, "lon": 101.52}, "Petaling Jaya": {"lat": 3.11, "lon": 101.60},
    "Kuala Lumpur": {"lat": 3.14, "lon": 101.69}, "Kajang": {"lat": 2.99, "lon": 101.79},
    "Putrajaya": {"lat": 2.93, "lon": 101.69}, "Seremban": {"lat": 2.73, "lon": 101.94},
    "Port Dickson": {"lat": 2.52, "lon": 101.80}, "Melaka": {"lat": 2.19, "lon": 102.25},
    "Muar": {"lat": 2.05, "lon": 102.57}, "Batu Pahat": {"lat": 1.85, "lon": 102.93},
    "Kluang": {"lat": 2.03, "lon": 103.32}, "Kulai": {"lat": 1.66, "lon": 103.60},
    "Johor Bahru": {"lat": 1.49, "lon": 103.74}, "Pasir Gudang": {"lat": 1.46, "lon": 103.90},
    "Taman Johor Jaya": {"lat": 1.52, "lon": 103.79}, "Segamat": {"lat": 2.51, "lon": 102.82},
    "Kota Bharu": {"lat": 6.13, "lon": 102.24}, "Tumpat": {"lat": 6.20, "lon": 102.17},
    "Kuala Terengganu": {"lat": 5.33, "lon": 103.14}, "Cukai": {"lat": 4.23, "lon": 103.42},
    "Kuantan": {"lat": 3.81, "lon": 103.33},
    "Kuching": {"lat": 1.55, "lon": 110.34}, "Simanggang": {"lat": 1.25, "lon": 111.45},
    "Sibu": {"lat": 2.30, "lon": 111.82}, "Bintulu": {"lat": 3.17, "lon": 113.03},
    "Miri": {"lat": 4.41, "lon": 114.01}, "Labuan": {"lat": 5.28, "lon": 115.24},
    "Kota Kinabalu": {"lat": 5.98, "lon": 116.07}, "Tuaran": {"lat": 6.18, "lon": 116.23},
    "Keningau": {"lat": 5.34, "lon": 116.16}, "Sandakan": {"lat": 5.84, "lon": 118.12},
    "Lahad Datu": {"lat": 5.03, "lon": 118.34}, "Tawau": {"lat": 4.25, "lon": 117.89},
}
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
    """Fetches current data for all cities for the heatmap and summary table."""
    lats = [city['lat'] for city in CITIES.values()]
    lons = [city['lon'] for city in CITIES.values()]
    # Fetch additional parameters for the summary table
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
    """Fetches forecast data for a single selected city."""
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
    """Fetches recent historical data for the selected city."""
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

# Create navigation options, with "Home" as the first option
sorted_cities = sorted(CITIES.keys())
page_options = ["--- HOME ---"] + sorted_cities

selected_page = st.sidebar.selectbox(
    "Select a View",
    page_options,
    index=0  # Default to the "HOME" view
)

st.title(f"🇲🇾 Malaysian Weather Dashboard")

# --- Page Content ---
if selected_page == "--- HOME ---":
    st.header("National Weather Overview")
    all_cities_data = get_all_cities_data()

    if all_cities_data:
        # --- MAP ---
        map_data = []
        summary_data = []
        for i, city_name in enumerate(CITIES.keys()):
            city_api_data = all_cities_data[i]
            current = city_api_data['current']

            # Data for the map
            map_data.append({
                "name": city_name, "lat": city_api_data["latitude"], "lon": city_api_data["longitude"],
                "temp": current['temperature_2m'], "precip": current['precipitation']
            })

            # Data for the summary table
            weather_desc, weather_icon = WEATHER_CODES.get(current['weather_code'], ("Unknown", ""))
            summary_data.append({
                "City": city_name,
                "Condition": f"{weather_icon} {weather_desc}",
                "Temp (°C)": current['temperature_2m'],
                "Rain (mm/hr)": current['precipitation'],
                "Humidity (%)": current['relative_humidity_2m'],
                "Wind (km/h)": current['wind_speed_10m']
            })

        # --- Display Map ---
        map_df = pd.DataFrame(map_data)
        map_df['size'] = map_df['precip'].apply(lambda x: x if x > 0 else 0.1)
        fig_map = px.scatter_mapbox(map_df, lat="lat", lon="lon", color="temp", size="size", hover_name="name",
                                    custom_data=['temp', 'precip'], color_continuous_scale=px.colors.sequential.Plasma,
                                    size_max=20, zoom=4.5, mapbox_style="carto-positron",
                                    center={"lat": 4.21, "lon": 108.2})
        fig_map.update_traces(
            hovertemplate='<b>%{hovertext}</b><br><br>Temperature: %{customdata[0]:.1f}°C<br>Precipitation: %{customdata[1]:.1f} mm<extra></extra>')
        fig_map.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, legend_title_text='Temp (°C)')
        st.plotly_chart(fig_map, use_container_width=True)

        # --- Display Summary Table ---
        st.subheader("Current Conditions Across Malaysia")
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

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
