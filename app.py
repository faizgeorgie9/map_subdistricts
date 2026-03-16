import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import numpy as np
from fiona import listlayers

# Konfigurasi Halaman
st.set_page_config(layout="wide", page_title="Mapping Ekonomi Kecamatan (Area)")

# --- FUNGSI LOGIKA WARNA & STATUS ---
def get_status_info(pengeluaran):
    if pengeluaran < 2500000:
        return 'red', 'Rendah'
    elif 2500000 <= pengeluaran <= 4500000:
        return 'orange', 'Menengah'
    else:
        return 'green', 'Tinggi'

# --- FUNGSI LOAD DATA GPKG ---
@st.cache_data
@st.cache_data
def load_gpkg_data():
    path = "data/indonesia_simple.gpkg"
    # Sekarang layer sudah rapi namanya: 'provinsi', 'kota', 'kecamatan'
    gdf_prov = gpd.read_file(path, layer='provinsi')
    gdf_city = gpd.read_file(path, layer='kota')
    gdf_kec = gpd.read_file(path, layer='kecamatan')

    # Pastikan koordinat WGS84
    for gdf in [gdf_prov, gdf_city, gdf_kec]:
        if gdf.crs != "EPSG:4326":
            gdf.to_crs("EPSG:4326", inplace=True)
    return gdf_prov, gdf_city, gdf_kec

try:
    gdf_prov, gdf_city, gdf_kec = load_gpkg_data()

    # --- SIDEBAR FILTER ---
    st.sidebar.header("📍 Filter Wilayah (GeoPackage)")

    # 1. Pilih Provinsi
    # Catatan: Sesuaikan 'NAME_1' dengan nama kolom di file gpkg Anda
    list_prov = sorted(gdf_prov['NAME_1'].unique())
    sel_prov_name = st.sidebar.selectbox("Pilih Provinsi", list_prov)

    # 2. Filter Kota
    gdf_city_filtered = gdf_city[gdf_city['NAME_1'] == sel_prov_name]
    list_city = sorted(gdf_city_filtered['NAME_2'].unique())
    sel_city_name = st.sidebar.selectbox("Pilih Kota/Kabupaten", list_city)

    # 3. Filter Kecamatan (Multiselect)
    gdf_kec_filtered = gdf_kec[(gdf_kec['NAME_1'] == sel_prov_name) & 
                               (gdf_kec['NAME_2'] == sel_city_name)]
    
    list_kec = sorted(gdf_kec_filtered['NAME_3'].unique())
    sel_kec_names = st.sidebar.multiselect("Pilih Kecamatan", list_kec, default=list_kec)

    # Data Akhir untuk Mapping
    gdf_final = gdf_kec_filtered[gdf_kec_filtered['NAME_3'].isin(sel_kec_names)].copy()

    # --- SIMULASI DATA EKONOMI & KATEGORISASI ---
    if not gdf_final.empty:
        np.random.seed(42)
        gdf_final['pengeluaran'] = np.random.randint(1500000, 6000000, size=len(gdf_final))
        
        # Tambahkan kolom status
        gdf_final['Status'] = gdf_final['pengeluaran'].apply(lambda x: get_status_info(x)[1])

    # --- TAMPILAN UTAMA ---
    st.title("📊 Indonesia Economic Area Mapping")
    
    st.markdown("""
    **Keterangan Warna Area:** <span style='color:red'>■</span> **Rendah** | 
    <span style='color:orange'>■</span> **Menengah** | 
    <span style='color:green'>■</span> **Tinggi**
    """, unsafe_allow_html=True)

    if not gdf_final.empty:
        # Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Kecamatan", len(gdf_final))
        col2.metric("Rata-rata", f"Rp {gdf_final['pengeluaran'].mean():,.0f}")
        col3.metric("Tertinggi", f"Rp {gdf_final['pengeluaran'].max():,.0f}")

        # Map Area (Bukan Titik)
        # Menentukan center peta dari centroid poligon yang dipilih
        m = folium.Map(location=[gdf_final.geometry.centroid.y.mean(), 
                                 gdf_final.geometry.centroid.x.mean()], 
                       zoom_start=11)

        # Implementasi Mapping Warna ke Poligon
        def style_function(feature):
            pengeluaran = feature['properties'].get('pengeluaran', 0)
            warna, _ = get_status_info(pengeluaran)
            return {
                'fillColor': warna,
                'color': 'white', # warna garis batas
                'weight': 1,
                'fillOpacity': 0.7,
            }

        folium.GeoJson(
            gdf_final,
            style_function=style_function,
            tooltip=folium.GeoJsonTooltip(
                fields=['NAME_3', 'pengeluaran', 'Status'],
                aliases=['Kecamatan:', 'Pengeluaran (Rp):', 'Kategori:'],
                localize=True
            )
        ).add_to(m)

        st_folium(m, width=1200, height=550)

        # --- TABEL DENGAN KOLOM STATUS ---
        st.write("### 📋 Detail Data Kecamatan")
        # NAME_3 biasanya adalah nama kecamatan di file GPKG
        df_display = pd.DataFrame(gdf_final[['NAME_3', 'pengeluaran', 'Status']].sort_values(by='pengeluaran', ascending=False))
        df_display.columns = ['Nama Kecamatan', 'Pengeluaran (Rp)', 'Kategori']
        
        st.dataframe(df_display, use_container_width=True)
        
    else:
        st.warning("Silakan pilih kecamatan di sidebar.")

except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")
    st.info("Pastikan nama kolom di GPKG (NAME_1, NAME_2, NAME_3) sudah sesuai.")
