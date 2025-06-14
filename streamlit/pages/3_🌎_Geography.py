import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from folium import plugins
import plotly.express as px
import plotly.graph_objects as go
import yaml
import os
from gcsfs import GCSFileSystem
from style import apply_theme
from utils import add_navigation_footer, show_loading_message
import time

# Performance optimization settings
st.set_page_config(
    page_title="S&P 500 Geography", 
    layout="wide",
    initial_sidebar_state="collapsed",  # Collapse sidebar for more screen space
)

# Apply shared theme
apply_theme()

# Set Google Cloud credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "c:/stock-data-pipeline-project/gcs-key.json"

# Load config
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
config_path = os.path.join(project_root, "config.yaml")
with open(config_path) as f:
    config = yaml.safe_load(f)

# Access bucket
bucket = config["gcs"]["bucket_name"]
fs = GCSFileSystem()

# Restore original company_info loading logic (no batching, no cache, no optimization)
# Remove load_company_data and use simple concat of all CSVs

# Load all symbols
symbols_df = pd.read_csv(f"gs://{bucket}/symbols.csv")

# Create paths for all files we need to read
paths = [f"gs://{bucket}/data/{symbol}_info.csv" for symbol in symbols_df.symbol]

# Read all files that exist
existing_paths = [p for p in paths if fs.exists(p)]

# Use pandas concat for all data
company_info = pd.concat([
    pd.read_csv(path) for path in existing_paths if not pd.read_csv(path).empty
], ignore_index=True)

# Convert strings to categorical data types to reduce memory usage
for col in ['city', 'state', 'country', 'sector', 'industry']:
    if col in company_info.columns:
        company_info[col] = company_info[col].astype('category')

# Precomputed coordinates dictionary to avoid repeated calculations
coordinates_cache = {}

# Add coordinates based on city and state for US companies
def get_approx_coordinates(row):
    if pd.isna(row.get('city')) or pd.isna(row.get('state')):
        return pd.Series({'latitude': None, 'longitude': None})
    
    # Create a cache key to avoid recomputing the same coordinates
    city = row['city'].upper() if not pd.isna(row.get('city')) else ''
    state = row['state'].upper() if not pd.isna(row.get('state')) else ''
    cache_key = f"{city}_{state}"
    
    # Check if we already computed these coordinates
    if cache_key in coordinates_cache:
        return pd.Series(coordinates_cache[cache_key])
    
    # Approximate coordinates for major cities
    coordinates = {
        'NEW YORK': {'NY': (40.7128, -74.0060)},
        'LOS ANGELES': {'CA': (34.0522, -118.2437)},
        'CHICAGO': {'IL': (41.8781, -87.6298)},
        'HOUSTON': {'TX': (29.7604, -95.3698)},
        'SAN FRANCISCO': {'CA': (37.7749, -122.4194)},
        'BOSTON': {'MA': (42.3601, -71.0589)},
        'SEATTLE': {'WA': (47.6062, -122.3321)},
        'ATLANTA': {'GA': (33.7490, -84.3880)},
        'DALLAS': {'TX': (32.7767, -96.7970)},
        'MIAMI': {'FL': (25.7617, -80.1918)},
        'CHARLOTTE': {'NC': (35.2271, -80.8431)},
        'DENVER': {'CO': (39.7392, -104.9903)},
        'AUSTIN': {'TX': (30.2672, -97.7431)},
        'PHOENIX': {'AZ': (33.4484, -112.0740)}
    }
    
    city = row['city'].upper()
    state = row['state'].upper()
    
    if city in coordinates and state in coordinates[city]:
        return pd.Series({
            'latitude': coordinates[city][state][0],
            'longitude': coordinates[city][state][1]
        })
    else:
        # Use state center coordinates as fallback
        state_centers = {
            'AL': (32.7794, -86.8287), 'AK': (64.0685, -152.2782),
            'AZ': (34.2744, -111.6602), 'AR': (34.8938, -92.4426),
            'CA': (37.1841, -119.4696), 'CO': (38.9972, -105.5478),
            'CT': (41.6219, -72.7273), 'DE': (38.9896, -75.5050),
            'FL': (28.6305, -82.4497), 'GA': (32.6415, -83.4426),
            'HI': (20.2927, -156.3737), 'ID': (44.3509, -114.6130),
            'IL': (40.0417, -89.1965), 'IN': (39.8942, -86.2816),
            'IA': (42.0751, -93.4960), 'KS': (38.4937, -98.3804),
            'KY': (37.5347, -85.3021), 'LA': (31.0689, -91.9968),
            'ME': (45.3695, -69.2428), 'MD': (39.0550, -76.7909),
            'MA': (42.2596, -71.8083), 'MI': (44.3467, -85.4102),
            'MN': (46.2807, -94.3053), 'MS': (32.7364, -89.6678),
            'MO': (38.3566, -92.4580), 'MT': (47.0527, -109.6333),
            'NE': (41.5378, -99.7951), 'NV': (39.3289, -116.6312),
            'NH': (43.6805, -71.5811), 'NJ': (40.1907, -74.6728),
            'NM': (34.4071, -106.1126), 'NY': (42.9538, -75.5268),
            'NC': (35.5557, -79.3877), 'ND': (47.4501, -100.4659),
            'OH': (40.2862, -82.7937), 'OK': (35.5889, -97.4943),
            'OR': (43.9336, -120.5583), 'PA': (40.8781, -77.7996),
            'RI': (41.6762, -71.5562), 'SC': (33.9169, -80.8964),
            'SD': (44.4443, -100.2263), 'TN': (35.8580, -86.3505),
            'TX': (31.4757, -99.3312), 'UT': (39.3055, -111.6703),
            'VT': (44.0687, -72.6658), 'VA': (37.5215, -78.8537),
            'WA': (47.3826, -120.4472), 'WV': (38.6409, -80.6227),
            'WI': (44.6243, -89.9941), 'WY': (42.9957, -107.5512)
        }
        
        if state in state_centers:
            return pd.Series({
                'latitude': state_centers[state][0],
                'longitude': state_centers[state][1]
            })
        return pd.Series({'latitude': None, 'longitude': None})

# Add coordinates for US companies
us_mask = (company_info['country'] == 'United States') | (company_info['country'] == 'USA') | (company_info['country'] == 'US')
company_info.loc[us_mask, ['latitude', 'longitude']] = company_info[us_mask].apply(get_approx_coordinates, axis=1)

# Optimize memory usage
if 'state' in company_info.columns:
    company_info['state'] = company_info['state'].astype('category')
if 'region' in company_info.columns:
    company_info['region'] = company_info['region'].astype('category')
if 'industry' in company_info.columns:
    company_info['industry'] = company_info['industry'].astype('category')

# Page title
st.title("S&P 500 Geography")
st.markdown("Geographic distribution of S&P 500 companies")
st.markdown("---")

# Add loading indicator
with st.spinner("Loading company data..."):
    pass  # company_info is already loaded above

# Show quick stats before heavy operations
if not company_info.empty:
    # Filter US companies - use faster .isin() method
    us_companies = company_info[company_info['country'].isin(['United States', 'USA', 'US'])]
    
    # Use nullable numeric type for calculations to prevent errors
    if 'marketCap' in us_companies.columns:
        # Convert to numeric without errors
        us_companies['marketCap'] = pd.to_numeric(us_companies['marketCap'], errors='coerce')
        total_market_cap = us_companies['marketCap'].sum()
    else:
        total_market_cap = 0
        
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("US Companies", f"{len(us_companies)}")
    with col2:
        # Handle potential NaN or invalid values
        market_cap_display = f"${total_market_cap/1e12:.2f}T" if pd.notnull(total_market_cap) and total_market_cap > 0 else "Unknown"
        st.metric("Total Market Cap", market_cap_display)
    with col3:
        if 'state' in us_companies.columns:
            st.metric("States Represented", f"{us_companies['state'].nunique()}")
        else:
            st.metric("States Represented", "N/A")

    # Let user choose view type to speed up loading
    view_type = st.radio("Select view type:", ["Interactive Map (Slower)", "Static Charts (Faster)"], horizontal=True)
    
    if view_type == "Static Charts (Faster)":
        # Show fast-loading charts instead of heavy maps
        st.subheader("Companies by State")
        if 'state' in us_companies.columns:
            state_counts = us_companies['state'].value_counts().reset_index()
            state_counts.columns = ['State', 'Companies']
            fig = px.bar(state_counts.head(20), x='State', y='Companies', 
                      title=f"Top 20 States by Number of S&P 500 Companies")
            st.plotly_chart(fig, use_container_width=True)
    else:
        # Create map centered on USA with optimized rendering
        m = folium.Map(
            location=[39.8283, -98.5795],  # Center of USA
            zoom_start=4,
            tiles='cartodbpositron',  # Clean, modern style
            prefer_canvas=True  # Use canvas for better performance
        )
        
        # Add lighter state boundaries
        folium.GeoJson(
            'https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/us-states.json',
            style_function=lambda x: {
                'fillColor': '#f0f0f0',
                'color': '#333333',
                'fillOpacity': 0.3,
                'weight': 1
            }
        ).add_to(m)

        # Add optimized MarkerCluster layer
        marker_cluster = folium.plugins.MarkerCluster(
            options={
                'maxClusterRadius': 40,  # Larger radius for more aggressive clustering (faster rendering)
                'spiderfyOnMaxZoom': True,
                'showCoverageOnHover': False,  # Hide coverage for better performance
                'zoomToBoundsOnClick': True,
                'disableClusteringAtZoom': 8,  # Disable clustering at high zoom levels
            }
        ).add_to(m)

        # Show progress indicator for map rendering - helps with user experience
        with st.spinner("Rendering company locations on map..."):
            # Filter for US companies and add markers - limit to top 300 by market cap for performance
            us_companies = us_companies.sort_values(by='marketCap', ascending=False).head(300)
            
            # Use batch processing to improve performance
            batch_size = 50
            total_companies = len(us_companies)
            
            # Process in batches
            for start_idx in range(0, total_companies, batch_size):
                batch = us_companies.iloc[start_idx:start_idx + batch_size]
                
                # Process each company in batch
                for idx, row in batch.iterrows():
                    try:
                        lat = float(row.get('latitude', 0))
                        lon = float(row.get('longitude', 0))
                        
                        if pd.notna(lat) and pd.notna(lon) and -90 <= lat <= 90 and -180 <= lon <= 180:
                            # Simplified popup content for better performance
                            popup_content = f"""
                            <div style='width: 180px'>
                                <b>{row['symbol']}</b><br>
                                {row.get('shortName', '')}
                            </div>
                            """
                            
                            # Use simpler icons for better performance
                            folium.CircleMarker(
                                location=[lat, lon],
                                radius=4,
                                popup=folium.Popup(popup_content, max_width=200),
                                tooltip=row['symbol'],
                                color='#E63946',
                                fill=True,
                                fill_color='#E63946',
                                fill_opacity=0.8,
                                weight=1
                            ).add_to(marker_cluster)
                    except:
                        # Silent exception handling for better performance
                        pass

            # Display map with width control for better performance
            folium_static(m, width=800)

# Add faster-loading chart alternatives
st.subheader("Geographic Distribution Statistics")

# Check if user wants to see visualizations (lazy loading)
show_charts = True  # Default to showing charts

if show_charts:
    tabs = st.tabs(["🇺🇸 State Analysis", "🏢 Industry Clusters"])
    
    with tabs[0]:
        col1, col2 = st.columns(2)
        
        with col1:
            # Companies by state - use plotly for better performance and visuals
            if 'state' in company_info.columns:
                state_counts = company_info['state'].value_counts().head(15).reset_index()
                state_counts.columns = ['State', 'Count']
                fig = px.bar(state_counts, x='State', y='Count', 
                             title="Top 15 States by Number of Companies",
                             color='Count', color_continuous_scale='Viridis')
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        
        with col2:
            # Market cap by state - more insightful than just counts
            if 'state' in company_info.columns and 'marketCap' in company_info.columns:
                # Convert to numeric, handle errors
                company_info['marketCap'] = pd.to_numeric(company_info['marketCap'], errors='coerce')
                # Group by state
                state_marketcap = company_info.groupby('state')['marketCap'].sum().reset_index()
                state_marketcap = state_marketcap.sort_values('marketCap', ascending=False).head(15)
                state_marketcap['marketCap_T'] = state_marketcap['marketCap'] / 1e12
                fig = px.bar(state_marketcap, x='state', y='marketCap_T', 
                             title="Top 15 States by Total Market Cap ($T)",
                             color='marketCap_T', color_continuous_scale='Viridis')
                fig.update_layout(height=400, yaxis_title="Market Cap ($Trillion)")
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    with tabs[1]:
        # Industry clusters analysis - simplified for better performance
        if 'industry' in company_info.columns and 'state' in company_info.columns:
            # Only calculate for top states
            top_states = company_info['state'].value_counts().head(8).index.tolist()
            top_data = company_info[company_info['state'].isin(top_states)]
            
            # Get industry counts by state
            industry_counts = top_data.groupby(['state', 'industry']).size().reset_index()
            industry_counts.columns = ['State', 'Industry', 'Companies']
            
            # Only show top 3 industries per state
            result = []
            for state in top_states:
                state_data = industry_counts[industry_counts['State'] == state]
                top_industries = state_data.nlargest(3, 'Companies')
                result.append(top_industries)
            
            # Combine results
            industry_distribution = pd.concat(result)
            
            # Create grouped bar chart
            fig = px.bar(
                industry_distribution,
                x='State',
                y='Companies',
                color='Industry',
                title='Top 3 Industries by State',
                barmode='group'            )
            
            fig.update_layout(
                height=500,
                xaxis_title='State',
                yaxis_title='Number of Companies',
                legend_title='Industry'
            )
            st.plotly_chart(fig, use_container_width=True)

            # Create a more structured DataFrame for visualization
            top_industries_formatted = []
            
            for state in top_states:
                state_data = industry_counts[industry_counts['State'] == state]
                top_industries = state_data.nlargest(3, 'Companies')
                industries_text = ", ".join([f"{row['Industry']} ({row['Companies']})" for _, row in top_industries.iterrows()])
                top_industries_formatted.append({
                    'State': state,
                    'Total Companies': top_data[top_data['state'] == state].shape[0],
                    'Dominant Industries': industries_text
                })
              # Create a more visual DataFrame
            visual_df = pd.DataFrame(top_industries_formatted)
            # Sort by total companies
            visual_df = visual_df.sort_values('Total Companies', ascending=False)
            
            # Display as three columns
            cols = st.columns(3)
            chunk_size = len(visual_df) // 3 + (1 if len(visual_df) % 3 != 0 else 0)
            for i, col in enumerate(cols):
                start_idx = i * chunk_size
                end_idx = min((i + 1) * chunk_size, len(visual_df))
                chunk = visual_df.iloc[start_idx:end_idx]
                with col:
                    for _, row in chunk.iterrows():
                        st.markdown(
                            f"""
                            <div style='background-color: rgba(28, 131, 225, 0.1); padding: 10px; border-radius: 5px; margin: 5px 0;'>
                                <h4 style='margin: 0; color: #1C83E1;'>{row['State']} ({row['Total Companies']})</h4>
                                <small>{row['Dominant Industries']}</small>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

# Add navigation footer
add_navigation_footer()