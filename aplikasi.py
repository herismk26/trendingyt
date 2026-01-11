import streamlit as st
from googleapiclient.discovery import build
import pandas as pd
from datetime import datetime, timezone, timedelta
import isodate
import base64

# ==========================================
# 1. KONFIGURASI API (GANTI API KEY ANDA)
# ==========================================
API_KEY = st.secrets"AIzaSyB-2vyqGeSwkrNEVuFWkClq2G845ctms6c"
youtube = build('youtube', 'v3', developerKey=API_KEY)

# ==========================================
# 2. SETTING HALAMAN & UI
# ==========================================
st.set_page_config(page_title="YouTube Research Pro", layout="wide")

st.markdown("""
    <style>
    .vph-text { color: #ff4b4b; font-weight: bold; }
    .channel-text { color: #555; font-size: 0.9em; }
    </style>
    """, unsafe_allow_html=True)

KATEGORI_ID = {
    "Semua": None, "Musik": "10", "Video Game": "20", 
    "Hiburan": "24", "Sains & Teknologi": "28", "Komedi": "23",
    "Olahraga": "17", "Berita": "25", "Otomotif": "2"
}

# ==========================================
# 3. FUNGSI LOGIKA
# ==========================================
def get_channel_subs(channel_id):
    try:
        request = youtube.channels().list(part="statistics", id=channel_id)
        response = request.execute()
        return response['items'][0]['statistics'].get('subscriberCount', '0')
    except: return '0'

def download_link(df):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    return f'''
        <a href="data:file/csv;base64,{b64}" download="riset_youtube.csv">
            <button style="background-color:#ff4b4b; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer;">
                💾 Simpan Hasil Ke CSV (Excel)
            </button>
        </a>'''

def fetch_data(region, limit, category, tipe):
    # Ambil 50 data untuk difilter
    request = youtube.videos().list(
        part="snippet,statistics,contentDetails",
        chart="mostPopular",
        regionCode=region,
        maxResults=50,
        videoCategoryId=category
    )
    response = request.execute()
    
    data = []
    now = datetime.now(timezone.utc)
    
    for item in response['items']:
        # Filter Durasi (Shorts <= 60s)
        duration_raw = item['contentDetails']['duration']
        duration_sec = isodate.parse_duration(duration_raw).total_seconds()
        is_shorts = duration_sec <= 60
        
        if tipe == "Shorts" and not is_shorts: continue
        if tipe == "Video Panjang" and is_shorts: continue
        
        # Konversi Waktu WIB
        pub_at = isodate.parse_datetime(item['snippet']['publishedAt'])
        wib_time = pub_at.astimezone(timezone(timedelta(hours=7)))
        
        # Hitung VPH
        views = int(item['statistics'].get('viewCount', 0))
        age_hours = (now - pub_at).total_seconds() / 3600
        vph = round(views / age_hours, 2) if age_hours > 0 else views
        
        data.append({
            "Judul": item['snippet']['title'],
            "Channel": item['snippet']['channelTitle'],
            "ChannelID": item['snippet']['channelId'],
            "Views": views,
            "VPH": vph,
            "Waktu Upload": wib_time.strftime('%Y-%m-%d %H:%M WIB'),
            "Durasi_Detik": int(duration_sec),
            "Tags": ", ".join(item['snippet'].get('tags', []))[:150],
            "Link": f"https://www.youtube.com/watch?v={item['id']}",
            "Thumbnail": item['snippet']['thumbnails']['medium']['url']
        })
        if len(data) >= limit: break
    return data

# ==========================================
# 4. TAMPILAN UTAMA
# ==========================================
st.title("🚀 YouTube Trending Research Tool")

with st.sidebar:
    st.header("⚙️ Filter Riset")
    negara = st.selectbox("Pilih Negara", ["ID", "US", "KR", "JP", "GB"])
    topik = st.selectbox("Topik Utama", list(KATEGORI_ID.keys()))
    tipe = st.radio("Format Konten", ["Semua", "Shorts", "Video Panjang"])
    jumlah = st.slider("Banyak Video", 5, 50, 10)
    st.divider()
    st.caption("Tools ini mengambil data real-time dari YouTube API v3.")

if st.button("MULAI ANALISIS DATA"):
    with st.spinner('Menghubungkan ke server YouTube...'):
        try:
            results = fetch_data(negara, jumlah, KATEGORI_ID[topik], tipe)
            
            if results:
                # Tombol Download di bagian atas
                df = pd.DataFrame(results)
                st.markdown(download_link(df), unsafe_allow_html=True)
                st.write("") 

                # Looping hasil (Fix Visual: Tanpa Border Ganda)
                for res in results:
                    col1, col2 = st.columns([1, 2.5])
                    
                    with col1:
                        st.image(res['Thumbnail'], use_container_width=True)
                        if res['Durasi_Detik'] <= 60:
                            st.error("⚡ SHORTS")
                        else:
                            st.success("🎥 VIDEO PANJANG")
                    
                    with col2:
                        st.subheader(res['Judul'])
                        subs = get_channel_subs(res['ChannelID'])
                        st.markdown(f"📺 **{res['Channel']}** | 👥 `{int(subs):,}` Subscribers")
                        
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Total Views", f"{res['Views']:,}")
                        m2.metric("VPH (Kecepatan)", f"{res['VPH']:,}")
                        m3.write(f"📅 **Waktu Upload:**\n{res['Waktu Upload']}")
                        
                        with st.expander("Lihat Hashtags & Metadata"):
                            st.write(f"**Tags:** {res['Tags']}")
                            st.write(f"**URL:** {res['Link']}")
                        
                        st.link_button("🔗 Tonton Video", res['Link'], use_container_width=True)
                    
                    st.divider() # Pemisah antar video yang bersih
            else:
                st.warning("Tidak ditemukan video trending untuk kategori/format ini.")
                
        except Exception as e:
            st.error(f"Terjadi kesalahan API: {e}")

            st.info("Pastikan API Key Anda benar dan kuota masih tersedia.")

