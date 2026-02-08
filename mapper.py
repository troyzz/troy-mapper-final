# Version 10.0
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os

# --- V10.0 FORCE REFRESH ---
st.set_page_config(page_title="Troy's Final Build", layout="wide")

SAVED_DATA = "field_log.csv"

# 1. SIDEBAR PERMANENT TOOLS
st.sidebar.header("🛠️ FIELD CONTROLS")
st.sidebar.write("If you see this, code is UPDATED.")

if st.sidebar.button("🗑️ CLEAR ALL DATA & RESET"):
    if os.path.exists(SAVED_DATA): os.remove(SAVED_DATA)
    st.session_state.clear()
    st.rerun()

# 2. DATA LOADING
if 'df' not in st.session_state:
    if os.path.exists(SAVED_DATA):
        st.session_state.df = pd.read_csv(SAVED_DATA)
        st.rerun()
    
    st.title("🛰️ Troy's Fielding Tool")
    upl = st.file_uploader("Upload CSV", type="csv")
    if upl:
        df = pd.read_csv(upl)
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

# 3. SELECTION DROPDOWN (Now at the top of the sidebar)
st.sidebar.markdown("---")
t_list = ["--- Select a Ticket ---"] + df['Ticket'].astype(str).tolist()
choice = st.sidebar.selectbox("🎯 JUMP TO TICKET", options=t_list)

if choice != "--- Select a Ticket ---":
    st.session_state.selected_id = choice

# 4. THE MAP
m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=13)
for i, row in df.iterrows():
    t_id = str(row['Ticket'])
    is_sel = (str(st.session_state.get('selected_id')) == t_id)
    color = "orange" if is_sel else ("green" if row['status'] == 'Completed' else "blue")
    folium.Marker([row['lat'], row['lon']], popup=f"ID:{t_id}", icon=folium.Icon(color=color)).add_to(m)

st.subheader("Field Map")
map_data = st_folium(m, height=400, width=None, key="troy_map", returned_objects=["last_object_clicked_popup"])

if map_data and map_data.get("last_object_clicked_popup"):
    st.session_state.selected_id = map_data["last_object_clicked_popup"].split(":")[1]
    st.rerun()

# 5. SITE DETAILS (Moved to Sidebar)
if st.session_state.get('selected_id'):
    sel_id = st.session_state.selected_id
    sel_row = df[df['Ticket'].astype(str) == sel_id].iloc[0]
    
    st.sidebar.markdown(f"## 🎫 Ticket: {sel_id}")
    
    # NAVIGATION
    nav = f"google.navigation:q={sel_row['lat']},{sel_row['lon']}"
    st.sidebar.link_button("🚗 START NAVIGATION", nav, use_container_width=True)
    
    # CAMERA
    st.sidebar.file_uploader("📸 TAKE PHOTO", accept_multiple_files=True, key=f"c_{sel_id}")

    # STATUS
    if st.sidebar.button("✅ MARK AS COMPLETE"):
        st.session_state.df.loc[st.session_state.df['Ticket'].astype(str) == sel_id, 'status'] = 'Completed'
        st.session_state.df.to_csv(SAVED_DATA, index=False)
        st.rerun()

    # NOTES
    st.sidebar.subheader("📋 FIELD NOTES")
    st.sidebar.info(sel_row['Notes'])
