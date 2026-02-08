# Version 10.0
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
from io import BytesIO
import zipfile

# --- 1. CONFIG ---
st.set_page_config(page_title="Troy's Map", layout="wide")

SAVED_DATA = "field_log.csv"

# Initialize session memory for photos and selection
if 'all_photos' not in st.session_state:
    st.session_state.all_photos = {}
if 'selected_id' not in st.session_state:
    st.session_state.selected_id = None

# --- 2. DATA LOADING ---
if 'df' not in st.session_state:
    if os.path.exists(SAVED_DATA):
        st.session_state.df = pd.read_csv(SAVED_DATA)
    else:
        st.title("🛰️ Troy's Fielding Tool")
        upl = st.file_uploader("Upload CSV", type="csv")
        if upl:
            df = pd.read_csv(upl)
            # Standardize column positions
            df.columns.values[0], df.columns.values[1], df.columns.values[2] = 'Ticket', 'lat', 'lon'
            df['Notes'] = df.iloc[:, 3].fillna("No notes.") if len(df.columns) >= 4 else "No notes."
            df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
            df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
            df = df.dropna(subset=['lat', 'lon'])
            df['status'] = 'Pending'
            st.session_state.df = df
            df.to_csv(SAVED_DATA, index=False)
            st.rerun()
        st.stop()

df = st.session_state.df

# --- 3. SIDEBAR: SELECTOR ---
st.sidebar.title("📍 SITE CONTROL")

# Dropdown for specific ticket selection
ticket_options = ["--- Search/Pick Ticket ---"] + df['Ticket'].astype(str).tolist()
choice = st.sidebar.selectbox("Jump to Ticket", options=ticket_options)

if choice != "--- Search/Pick Ticket ---" and choice != str(st.session_state.selected_id):
    st.session_state.selected_id = choice
    st.rerun()

# --- 4. THE MAP ---
m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=13)

for i, row in df.iterrows():
    t_id = str(row['Ticket'])
    is_sel = (str(st.session_state.selected_id) == t_id)
    
    # Color logic: Green=Done, Orange=Selected, Blue=Pending
    if row['status'] == 'Completed':
        color = "green"
    elif is_sel:
        color = "orange"
    else:
        color = "blue"
    
    folium.Marker(
        [row['lat'], row['lon']], 
        popup=f"ID:{t_id}", 
        icon=folium.Icon(color=color, icon="camera" if color != "green" else "ok")
    ).add_to(m)

st.subheader("Field Map")
map_data = st_folium(m, height=400, width=None, key="troy_map", returned_objects=["last_object_clicked_popup"])

# Map click trigger
if map_data and map_data.get("last_object_clicked_popup"):
    clicked_id = map_data["last_object_clicked_popup"].split(":")[1]
    # Toggle logic
    st.session_state.selected_id = None if str(st.session_state.selected_id) == clicked_id else clicked_id
    st.rerun()

# --- 5. SIDEBAR DETAILS ---
if st.session_state.selected_id:
    sel_id = str(st.session_state.selected_id)
    # Get the current row data
    idx_list = df[df['Ticket'].astype(str) == sel_id].index
    if not idx_list.empty:
        idx = idx_list[0]
        sel_row = df.iloc[idx]
        
        st.sidebar.markdown(f"## 🎫 Ticket: {sel_id}")
        
        # Action Buttons
        st.sidebar.link_button("🚗 START NAVIGATION", f"google.navigation:q={sel_row['lat']},{sel_row['lon']}", use_container_width=True)
        
        # Photos
        up_photos = st.sidebar.file_uploader("📸 TAKE PHOTOS", accept_multiple_files=True, key=f"c_{sel_id}")
        if up_photos:
            st.session_state.all_photos[sel_id] = up_photos

        if st.sidebar.button("✅ MARK AS COMPLETE", use_container_width=True):
            st.session_state.df.at[idx, 'status'] = 'Completed'
            st.session_state.df.to_csv(SAVED_DATA, index=False)
            st.session_state.selected_id = None
            st.rerun()

        with st.sidebar.expander("📋 VIEW FIELD NOTES", expanded=False):
            st.write(sel_row['Notes'])

# --- 6. EXPORT ZIP ---
st.sidebar.markdown("---")
st.sidebar.subheader("📦 End of Day Export")

if st.session_state.all_photos:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for tid, file_list in st.session_state.all_photos.items():
            for i, f in enumerate(file_list):
                z.writestr(f"Ticket_{tid}_Photo_{i}.jpg", f.getvalue())
    
    st.sidebar.download_button(
        label="📂 Download All Photos (ZIP)",
        data=buf.getvalue(),
        file_name="field_photos.zip",
        mime="application/zip",
        use_container_width=True
    )

if st.sidebar.button("🗑️ RESET ALL DATA"):
    if os.path.exists(SAVED_DATA): os.remove(SAVED_DATA)
    st.session_state.clear()
    st.rerun()



