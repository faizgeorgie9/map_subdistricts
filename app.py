import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import numpy as np

# Konfigurasi Halaman
st.set_page_config(layout="wide", page_title="Mapping Ekonomi Kecamatan")

# --- FUNGSI LOGIKA WARNA & STATUS ---
def get_status_info(pengeluaran):
    """
    Mengembalikan warna dan label status berdasarkan nominal pengeluaran.
    """
    if pengeluaran < 2500000:
        return 'red', 'Rendah'
    elif 2500000 <= pengeluaran <= 4500000:
        return 'orange', 'Menengah'
    else:
        return 'green', 'Tinggi'

# --- FUNGSI LOAD DATA ---
@st.cache_data
def load_local_data():
    df_prov = pd.read_csv('data/provinces.csv')
    df_kota = pd.read_csv('data/cities.csv')
    df_kec = pd.read_csv('data/kecamatan.csv')
    
    for df in [df_prov, df_kota, df_kec]:
        if 'Code' in df.columns:
            df['Code'] = df['Code'].astype(str)
        if 'Parent' in df.columns:
            df['Parent'] = df['Parent'].astype(str)
            
    return df_prov, df_kota, df_kec

try:
    df_prov, df_kota, df_kec = load_local_data()

    # --- SIDEBAR FILTER ---
    st.sidebar.header("📍 Filter Wilayah")

    sel_prov_name = st.sidebar.selectbox("Pilih Provinsi", sorted(df_prov['Name'].unique()))
    prov_id = df_prov[df_prov['Name'] == sel_prov_name]['Code'].values[0]

    df_kota_filtered = df_kota[df_kota['Parent'] == prov_id]
    sel_kota_name = st.sidebar.selectbox("Pilih Kota/Kabupaten", sorted(df_kota_filtered['Name'].unique()))
    kota_id = df_kota_filtered[df_kota_filtered['Name'] == sel_kota_name]['Code'].values[0]

    df_kec_filtered = df_kec[df_kec['Parent'] == kota_id]
    sel_kec_names = st.sidebar.multiselect("Pilih Kecamatan", sorted(df_kec_filtered['Name'].unique()), 
                                           default=sorted(df_kec_filtered['Name'].unique()))

    df_final = df_kec_filtered[df_kec_filtered['Name'].isin(sel_kec_names)].copy()

    # --- SIMULASI DATA EKONOMI & KATEGORISASI ---
    if not df_final.empty:
        np.random.seed(42)
        df_final['pengeluaran'] = np.random.randint(1500000, 6000000, size=len(df_final))
        
        # Tambah kolom Status untuk Tabel
        # Menggunakan .apply untuk memetakan fungsi get_status_info ke kolom baru
        df_final['Status'] = df_final['pengeluaran'].apply(lambda x: get_status_info(x)[1])

    # --- TAMPILAN UTAMA ---
    st.title("📊 Indonesia Economic Mapping")
    
    st.markdown("""
    **Keterangan Kategori:** <span style='color:red'>●</span> **Rendah** (< 2.5jt) | 
    <span style='color:orange'>●</span> **Menengah** (2.5jt - 4.5jt) | 
    <span style='color:green'>●</span> **Tinggi** (> 4.5jt)
    """, unsafe_allow_html=True)

    if not df_final.empty:
        # Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Kecamatan", len(df_final))
        col2.metric("Rata-rata", f"Rp {df_final['pengeluaran'].mean():,.0f}")
        col3.metric("Tertinggi", f"Rp {df_final['pengeluaran'].max():,.0f}")

        # Map
        m = folium.Map(location=[df_final['Latitude'].mean(), df_final['Longitude'].mean()], 
                       zoom_start=11)

        for _, row in df_final.iterrows():
            warna, status_label = get_status_info(row['pengeluaran'])
            
            tooltip_html = f"<b>{row['Name']}</b>"
            popup_html = f"""
                <div style='width:200px'>
                <b>Kecamatan:</b> {row['Name']}<br>
                <b>Pengeluaran:</b> Rp {row['pengeluaran']:,.0f}<br>
                <hr>
                <b>Status:</b> {status_label}
                </div>
            """

            folium.Marker(
                location=[row['Latitude'], row['Longitude']],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=tooltip_html,
                icon=folium.Icon(color=warna, icon="info-sign")
            ).add_to(m)

        st_folium(m, width=1200, height=500)

        # --- TABEL DENGAN KOLOM STATUS ---
        st.write("### 📋 Detail Data Kecamatan")
        # Menampilkan kolom Name, Pengeluaran, dan Status
        df_display = df_final[['Name', 'pengeluaran', 'Status']].sort_values(by='pengeluaran', ascending=False)
        
        # Penamaan kolom agar lebih rapi di Streamlit
        df_display.columns = ['Nama Kecamatan', 'Pengeluaran (Rp)', 'Kategori']
        
        st.dataframe(df_display, use_container_width=True)
        
    else:
        st.warning("Silakan pilih kecamatan di sidebar.")

except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")