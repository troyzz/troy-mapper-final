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

# --- 2. SESSION INITIALIZATION ---
if 'all_photos' not in st.session_state:
    st.session_state.all_photos = {}
if 'selected_id' not in st.session_state:
    st.session_state.selected_id = None

# --- 3. DATA LOADING ---
if 'df' not in st.session_state:
    if os.path.exists(SAVED_DATA):
        st.session_state.df = pd.read_csv(SAVED_DATA)
    else:
        st.title("🛰️ Troy's Fielding Tool")
        upl = st.file_uploader("Upload CSV", type="csv")
        if upl:
            df = pd.read_csv(upl)
            df.columns.values[0], df.columns.values[1], df.columns.values[2] = 'Ticket', 'lat', 'lon'
            df['Notes'] = df.iloc[:, 3].fillna("No notes.") if len(df.columns) >= 4 else "No notes."
            df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
            df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
            df = df.dropna(subset=['lat', 'lon'])
            df['status'] = 'Pending' # Statuses: Pending, Completed, Inaccessible
            st.session_state.df = df
            df.to_csv(SAVED_DATA, index=False)
            st.rerun()
        st.stop()

df = st.session_state.df

# --- 4. SIDEBAR: SELECTOR ---
st.sidebar.title("📍 SITE CONTROL")

ticket_options = ["--- Search/Pick Ticket ---"] + df['Ticket'].astype(str).tolist()
current_idx = 0
if str(st.session_state.selected_id) in ticket_options:
    current_idx = ticket_options.index(str(st.session_state.selected_id))

choice = st.sidebar.selectbox("Jump to Ticket", options=ticket_options, index=current_idx)

if choice != ticket_options[current_idx]:
    st.session_state.selected_id = None if choice == "--- Search/Pick Ticket ---" else choice
    st.rerun()

# --- 5. THE MAP ---
if st.session_state.selected_id:
    s_row = df[df['Ticket'].astype(str) == str(st.session_state.selected_id)].iloc[0]
    m_lat, m_lon = s_row['lat'], s_row['lon']
else:
    m_lat, m_lon = df['lat'].mean(), df['lon'].mean()

m = folium.Map(location=[m_lat, m_lon], zoom_start=15 if st.session_state.selected_id else 13)

for i, row in df.iterrows():
    t_id = str(row['Ticket'])
    is_sel = (str(st.session_state.selected_id) == t_id)
    
    # 🎨 COLOR LOGIC 🎨
    if row['status'] == 'Completed':
        color, icon = "green", "ok"
    elif row['status'] == 'Inaccessible':
        color, icon = "red", "remove" # Red X icon
    elif is_sel:
        color, icon = "orange", "star"
    else:
        color, icon = "blue", "camera"
    
    folium.Marker(
        [row['lat'], row['lon']], 
        popup=f"ID:{t_id}", 
        icon=folium.Icon(color=color, icon=icon)
    ).add_to(m)

st.subheader("Field Map")
map_data = st_folium(m, height=400, width=None, key="troy_map", returned_objects=["last_object_clicked_popup"])

if map_data and map_data.get("last_object_clicked_popup"):
    clicked_id = map_data["last_object_clicked_popup"].split(":")[1]
    st.session_state.selected_id = None if str(st.session_state.selected_id) == clicked_id else clicked_id
    st.rerun()

# --- 6. SIDEBAR DETAILS ---
if st.session_state.selected_id:
    sel_id = str(st.session_state.selected_id)
    idx = df[df['Ticket'].astype(str) == sel_id].index[0]
    sel_row = df.iloc[idx]
    
    st.sidebar.markdown(f"## 🎫 Ticket: {sel_id}")
    st.sidebar.write(f"Current Status: **{sel_row['status']}**")
    
    st.sidebar.link_button("🚗 START NAVIGATION", f"google.navigation:q={sel_row['lat']},{sel_row['lon']}", use_container_width=True)
    
    up_photos = st.sidebar.file_uploader("📸 TAKE PHOTOS", accept_multiple_files=True, key=f"c_{sel_id}")
    if up_photos:
        st.session_state.all_photos[sel_id] = up_photos

    # ACTION BUTTONS
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("✅ COMPLETE", use_container_width=True):
            st.session_state.df.at[idx, 'status'] = 'Completed'
            st.session_state.df.to_csv(SAVED_DATA, index=False)
            st.session_state.selected_id = None
            st.rerun()
    with col2:
        if st.button("🚫 BLOCKED", use_container_width=True):
            st.session_state.df.at[idx, 'status'] = 'Inaccessible'
            st.session_state.df.to_csv(SAVED_DATA, index=False)
            st.session_state.selected_id = None
            st.rerun()

    with st.sidebar.expander("📋 VIEW FIELD NOTES", expanded=True):
        st.write(sel_row['Notes'])

# --- 7. EXPORT ---
st.sidebar.markdown("---")
if st.session_state.all_photos:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for tid, file_list in st.session_state.all_photos.items():
            for i, f in enumerate(file_list):
                z.writestr(f"Ticket_{tid}_Photo_{i}.jpg", f.getvalue())
    
    st.sidebar.download_button("📂 Download Photos (ZIP)", data=buf.getvalue(), file_name="field_photos.zip", mime="application/zip", use_container_width=True)

if st.sidebar.button("🗑️ RESET ALL DATA"):
    if os.path.exists(SAVED_DATA): os.remove(SAVED_DATA)
    st.session_state.clear()
    st.rerun()





