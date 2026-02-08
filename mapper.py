# Version 10.0
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os

st.set_page_config(page_title="Troy's Final Build", layout="wide")

SAVED_DATA = "field_log.csv"

# 1. SESSION STATE INITIALIZATION
if 'selected_id' not in st.session_state:
    st.session_state.selected_id = None
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
            df['status'] = 'Pending'
            st.session_state.df = df
            df.to_csv(SAVED_DATA, index=False)
            st.rerun()
        st.stop()

df = st.session_state.df

# 2. THE MAP (RESTORED COLOR LOGIC)
m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=13)

for i, row in df.iterrows():
    t_id = str(row['Ticket'])
    # Logic: Orange if selected, Green if Completed, Blue otherwise
    is_sel = (str(st.session_state.selected_id) == t_id)
    
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

# 3. SELECTION LOGIC (WITH UN-TAP TOGGLE)
if map_data and map_data.get("last_object_clicked_popup"):
    clicked_id = map_data["last_object_clicked_popup"].split(":")[1]
    # If we click the SAME pin again, unselect it (turn it back blue/green)
    if st.session_state.selected_id == clicked_id:
        st.session_state.selected_id = None
    else:
        st.session_state.selected_id = clicked_id
    st.rerun()

# 4. SIDEBAR CONTROLS
st.sidebar.title("📍 SITE CONTROL")

if st.session_state.selected_id:
    sel_id = st.session_state.selected_id
    # Find the row in the session_state DF to ensure status is current
    idx = st.session_state.df[st.session_state.df['Ticket'].astype(str) == sel_id].index[0]
    sel_row = st.session_state.df.iloc[idx]
    
    st.sidebar.markdown(f"## 🎫 Ticket: {sel_id}")
    st.sidebar.write(f"Status: **{sel_row['status']}**")
    
    # NAV & CAMERA
    nav = f"google.navigation:q={sel_row['lat']},{sel_row['lon']}"
    st.sidebar.link_button("🚗 START NAVIGATION", nav, use_container_width=True)
    st.sidebar.file_uploader("📸 TAKE PHOTO", accept_multiple_files=True, key=f"c_{sel_id}")

    # GREEN PIN TRIGGER
    if st.sidebar.button("✅ MARK AS COMPLETE", use_container_width=True):
        st.session_state.df.at[idx, 'status'] = 'Completed'
        st.session_state.df.to_csv(SAVED_DATA, index=False)
        st.session_state.selected_id = None # Clear selection to show the green pin
        st.rerun()

    # NOTES POP-OUT
    with st.sidebar.expander("📋 VIEW FIELD NOTES", expanded=False):
        st.write(sel_row['Notes'])

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ RESET DAY"):
    if os.path.exists(SAVED_DATA): os.remove(SAVED_DATA)
    st.session_state.clear()
    st.rerun()

    # NOTES
    st.sidebar.subheader("📋 FIELD NOTES")
    st.sidebar.info(sel_row['Notes'])

