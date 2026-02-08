import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os

# --- 1. PAGE SETUP ---
st.set_page_config(page_title="Troy's Map", layout="centered")

# CSS to make the Notes box stand out on a small screen
st.markdown("""
    <style>
    .stAlert { border: 2px solid #ffa500; background-color: #fff4e6; }
    </style>
    """, unsafe_allow_html=True)

SAVED_DATA = "permanent_work_log.csv"

# --- 2. DATA LOADING ---
if 'df' not in st.session_state:
    st.title("🛰️ Troy's Fielding Tool")
    
    if os.path.exists(SAVED_DATA):
        st.session_state.df = pd.read_csv(SAVED_DATA)
        st.rerun()

    uploaded_file = st.file_uploader("Upload CSV (Ticket, Lat, Lon, Notes)", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        # Force column names for safety: Ticket=0, Lat=1, Lon=2, Notes=3
        df.columns.values[0] = 'Ticket'
        df.columns.values[1] = 'lat'
        df.columns.values[2] = 'lon'
        if len(df.columns) >= 4:
            df.columns.values[3] = 'Notes'
        else:
            df['Notes'] = "No notes provided."
            
        df['status'] = 'Pending'
        st.session_state.df = df
        df.to_csv(SAVED_DATA, index=False)
        st.rerun()
    st.stop()

df = st.session_state.df

# --- 3. THE MAP ---
# Start map at the average location of your pins
m = folium.Map(location=[df.lat.mean(), df.lon.mean()], zoom_start=13, tiles="OpenStreetMap")

for i, row in df.iterrows():
    t_id = str(row['Ticket'])
    is_sel = (st.session_state.get('selected_id') == t_id)
    color = "orange" if is_sel else ("green" if row['status'] == 'Completed' else "blue")
    
    folium.Marker(
        [row['lat'], row['lon']],
        popup=f"ID:{t_id}", # The app uses this to identify which pin was tapped
        icon=folium.Icon(color=color, icon="camera")
    ).add_to(m)

st.subheader("Field Map")
# Smaller height (300) is key for mobile stability
map_data = st_folium(m, height=300, width=None, key="troy_map")

# --- 4. DETAILS & NOTES (The Request) ---
if map_data and map_data.get("last_object_clicked_popup"):
    # Extract ID from the popup text "ID:12345"
    t_id = map_data["last_object_clicked_popup"].split(":")[1]
    st.session_state.selected_id = t_id
    
    # Get the specific row data
    sel = df[df['Ticket'].astype(str) == t_id].iloc[0]
    
    st.markdown(f"### 📍 Site: {t_id}")
    
    # DISPLAY NOTES HERE (Between Site and Nav Button)
    st.info(f"📝 **Field Notes:**\n\n{sel['Notes']}")

    nav_url = f"google.navigation:q={sel['lat']},{sel['lon']}"
    st.link_button("🚗 Start Google Maps Nav", nav_url, use_container_width=True)
    
    if st.button("✅ Confirm Completion", use_container_width=True):
        st.session_state.df.loc[st.session_state.df['Ticket'].astype(str) == t_id, 'status'] = 'Completed'
        st.session_state.df.to_csv(SAVED_DATA, index=False)
        st.rerun()

# --- 5. TOOLS ---
if st.sidebar.button("🗑️ Reset Day"):
    if os.path.exists(SAVED_DATA): os.remove(SAVED_DATA)
    st.session_state.clear()
    st.rerun()
