import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os

# --- 1. MOBILE OPTIMIZATION HEADERS ---
st.set_page_config(page_title="Troy's Tool", layout="centered")

# This CSS forces the map to fit perfectly on a phone screen without crashing
st.markdown("""
    <style>
    .main { overflow: hidden; }
    iframe { width: 100% !important; border-radius: 10px; }
    .stButton>button { width: 100%; border-radius: 20px; height: 3em; background-color: #f0f2f6; }
    </style>
    """, unsafe_allow_html=True)

SAVED_DATA = "current_work_log.csv"

# --- 2. DATA LOADING ---
if 'df' not in st.session_state:
    st.title("🛰️ Troy's Fielding Tool")
    
    # Auto-load saved data if it exists
    if os.path.exists(SAVED_DATA):
        try:
            st.session_state.df = pd.read_csv(SAVED_DATA)
            st.rerun()
        except:
            os.remove(SAVED_DATA)

    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file:
        try:
            raw = pd.read_csv(uploaded_file).dropna(how='all')
            df = pd.DataFrame()
            df['Ticket'] = raw.iloc[:, 0].astype(str)
            df['lat'] = pd.to_numeric(raw.iloc[:, 1], errors='coerce')
            df['lon'] = pd.to_numeric(raw.iloc[:, 2], errors='coerce')
            df['Notes'] = raw.iloc[:, 3].fillna("No notes.") if len(raw.columns) >= 4 else "No notes."
            
            df = df.dropna(subset=['lat', 'lon'])
            df['status'] = 'Pending'
            st.session_state.df = df
            df.to_csv(SAVED_DATA, index=False)
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
    st.stop()

# --- 3. SIDEBAR & SEARCH ---
st.sidebar.title("🔍 Search")
search_query = st.sidebar.text_input("Ticket #")

if st.sidebar.button("🗑️ Clear & Reset"):
    if os.path.exists(SAVED_DATA): os.remove(SAVED_DATA)
    st.session_state.clear()
    st.rerun()

# --- 4. THE MAP (Optimized for Mobile RAM) ---
# We use a standard map tileset first. If this works, we can add satellite back later.
m = folium.Map(tiles="OpenStreetMap", control_scale=True)

df = st.session_state.df

if search_query:
    match = df[df['Ticket'].astype(str).str.contains(search_query, na=False)]
    if not match.empty:
        st.session_state.selected_id = str(match.iloc[0]['Ticket'])
        m.location = [match.iloc[0]['lat'], match.iloc[0]['lon']]
        m.zoom_start = 17
else:
    # Zoom to fit all pins
    sw, ne = df[['lat', 'lon']].min().values.tolist(), df[['lat', 'lon']].max().values.tolist()
    m.fit_bounds([sw, ne])

for _, row in df.iterrows():
    t_id = str(row['Ticket'])
    is_sel = (t_id == st.session_state.get('selected_id'))
    color = "orange" if is_sel else ("green" if row['status'] == 'Completed' else "blue")
    folium.Marker(
        [row['lat'], row['lon']], 
        popup=f"Ticket: {t_id}",
        icon=folium.Icon(color=color, icon="camera")
    ).add_to(m)

# --- 5. RENDER ---
st.subheader("Field Map")
# Using a smaller height (300) prevents the mobile browser from "killing" the process
map_data = st_folium(m, height=300, width=None, key="mobile_map")

# Mobile Click Logic
if map_data and map_data.get("last_object_clicked_popup"):
    clicked_id = map_data["last_object_clicked_popup"].split(": ")[1]
    if st.session_state.get('selected_id') != clicked_id:
        st.session_state.selected_id = clicked_id
        st.rerun()

# --- 6. SITE DETAILS ---
if st.session_state.get('selected_id'):
    t_id = st.session_state.selected_id
    sel = df[df['Ticket'].astype(str) == t_id].iloc[0]
    
    st.markdown(f"### 📍 Ticket: {t_id}")
    st.info(f"**Field Notes:** {sel['Notes']}")
    
    # Standard Android navigation link
    nav_url = f"google.navigation:q={sel['lat']},{sel['lon']}"
    st.link_button("🚗 Open in Google Maps", nav_url)
    
    if st.button("✅ Mark as Complete"):
        st.session_state.df.loc[st.session_state.df['Ticket'].astype(str) == t_id, 'status'] = 'Completed'
        st.session_state.selected_id = None
        st.session_state.df.to_csv(SAVED_DATA, index=False)
        st.rerun()
