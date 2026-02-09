# Version 10.0
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
import json
from io import BytesIO
import zipfile
from datetime import datetime

# --- GOOGLE DRIVE LIBRARIES ---
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# --- 1. CONFIG & DRIVE SETUP ---
st.set_page_config(page_title="Troy's Map", layout="wide")
SAVED_DATA = "field_log.csv"

# ⚠️ PASTE YOUR FOLDER ID HERE ⚠️
FOLDER_ID = "1x1qYp-qT3849DUAxLi5msViHcBecT-NA" 

# Connect to Google Drive using the Secrets
try:
    if "gcp_service_account" in st.secrets:
        # 1. Get the raw string
        raw_info = st.secrets["gcp_service_account"]
        
        # 2. SURGICAL CLEAN: This removes the literal backslashes that confuse JSON
        # It turns the text "on the page" into the data "in memory"
        clean_info = raw_info.encode('utf-8').decode('unicode_escape')
        
        # 3. Load the dictionary
        info = json.loads(clean_info, strict=False)
        
        # 4. Final safety check for the private key formatting
        if "private_key" in info:
            info["private_key"] = info["private_key"].replace('\\n', '\n').replace('\n', '\n')
            
        creds = service_account.Credentials.from_service_account_info(info)
        drive_service = build('drive', 'v3', credentials=creds)
    else:
        st.error("Google Secrets not found. Please check Streamlit Cloud Settings.")
except Exception as e:
    st.error(f"Authentication Error: {e}")

def upload_to_drive(file_content, file_name, folder_id):
    try:
        file_metadata = {'name': file_name, 'parents': [folder_id]}
        media = MediaIoBaseUpload(BytesIO(file_content), mimetype='image/jpeg', resumable=True)
        
        request = drive_service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id',
            supportsAllDrives=True
        )
        response = request.execute()
        return True
    except Exception as e:
        # This will force the REAL error to show up in a red box on your phone
        st.sidebar.error(f"⚠️ DRIVE ERROR: {str(e)}")
        return False

# Initialize session memory
if 'all_photos' not in st.session_state: st.session_state.all_photos = {}
if 'uploaded_keys' not in st.session_state: st.session_state.uploaded_keys = []
if 'selected_id' not in st.session_state: st.session_state.selected_id = None

# --- 2. DATA LOADING ---
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

# --- 3. SIDEBAR: SELECTOR ---
st.sidebar.title("📍 SITE CONTROL")
ticket_options = ["--- Search/Pick Ticket ---"] + df['Ticket'].astype(str).tolist()
current_idx = 0
if str(st.session_state.selected_id) in ticket_options:
    current_idx = ticket_options.index(str(st.session_state.selected_id))

choice = st.sidebar.selectbox("Jump to Ticket", options=ticket_options, index=current_idx)
if choice != ticket_options[current_idx]:
    st.session_state.selected_id = None if choice == "--- Search/Pick Ticket ---" else choice
    st.rerun()

# --- 4. THE MAP ---
if st.session_state.selected_id:
    s_row = df[df['Ticket'].astype(str) == str(st.session_state.selected_id)].iloc[0]
    m_lat, m_lon = s_row['lat'], s_row['lon']
else:
    m_lat, m_lon = df['lat'].mean(), df['lon'].mean()

m = folium.Map(location=[m_lat, m_lon], zoom_start=15 if st.session_state.selected_id else 13)
for i, row in df.iterrows():
    t_id = str(row['Ticket'])
    is_sel = (str(st.session_state.selected_id) == t_id)
    color, icon = ("green", "ok") if row['status'] == 'Completed' else (("red", "remove") if row['status'] == 'Inaccessible' else (("orange", "star") if is_sel else ("blue", "camera")))
    folium.Marker([row['lat'], row['lon']], popup=f"ID:{t_id}", icon=folium.Icon(color=color, icon=icon)).add_to(m)

st.subheader("Field Map")
map_data = st_folium(m, height=400, width=None, key="troy_map", returned_objects=["last_object_clicked_popup"])

if map_data and map_data.get("last_object_clicked_popup"):
    clicked_id = map_data["last_object_clicked_popup"].split(":")[1]
    st.session_state.selected_id = None if str(st.session_state.selected_id) == clicked_id else clicked_id
    st.rerun()

# --- 5. SIDEBAR DETAILS & DRIVE UPLOAD ---
if st.session_state.selected_id:
    sel_id = str(st.session_state.selected_id)
    idx = df[df['Ticket'].astype(str) == sel_id].index[0]
    sel_row = df.iloc[idx]
    
    st.sidebar.markdown(f"## 🎫 Ticket: {sel_id}")
    st.sidebar.link_button("🚗 START NAVIGATION", f"google.navigation:q={sel_row['lat']},{sel_row['lon']}", use_container_width=True)
    
    # --- AUTO-UPLOAD PHOTO LOGIC ---
    up_photos = st.sidebar.file_uploader("📸 TAKE PHOTOS", accept_multiple_files=True, key=f"c_{sel_id}")
    if up_photos:
        for photo in up_photos:
            unique_key = f"{sel_id}_{photo.name}"
            # Only upload if not already done in this session
            if unique_key not in st.session_state.uploaded_keys:
                with st.sidebar.status(f"Saving {photo.name} to Drive...", expanded=False) as status:
                    # Rename file for Drive
                    drive_name = f"Ticket_{sel_id}_{photo.name}"
                    success = upload_to_drive(photo.getvalue(), drive_name, FOLDER_ID)
                    if success:
                        st.session_state.uploaded_keys.append(unique_key)
                        status.update(label=f"✅ {photo.name} Secure on Drive!", state="complete")
        st.session_state.all_photos[sel_id] = up_photos

    if st.sidebar.button("✅ MARK AS COMPLETE", use_container_width=True):
        st.session_state.df.at[idx, 'status'] = 'Completed'
        st.session_state.df.to_csv(SAVED_DATA, index=False)
        st.session_state.selected_id = None
        st.rerun()

    if st.sidebar.button("🚫 MARK AS INACCESSIBLE", use_container_width=True):
        st.session_state.df.at[idx, 'status'] = 'Inaccessible'
        st.session_state.df.to_csv(SAVED_DATA, index=False)
        st.session_state.selected_id = None
        st.rerun()

    with st.sidebar.expander("📋 VIEW FIELD NOTES", expanded=True):
        st.write(sel_row['Notes'])

# --- 6. EXPORT (BACKUP) ---
st.sidebar.markdown("---")
if st.session_state.all_photos:
    now = datetime.now().strftime("%b-%d_%H-%M")
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for tid, file_list in st.session_state.all_photos.items():
            for i, f in enumerate(file_list):
                z.writestr(f"Ticket_{tid}_Photo_{i}.jpg", f.getvalue())
    st.sidebar.download_button(f"📂 Download Backup ZIP ({now})", data=buf.getvalue(), file_name=f"field_photos_{now}.zip", mime="application/zip", use_container_width=True)

if st.sidebar.button("🗑️ RESET ALL DATA"):
    if os.path.exists(SAVED_DATA): os.remove(SAVED_DATA)
    st.session_state.clear()
    st.rerun()















