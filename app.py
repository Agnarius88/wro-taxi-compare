import streamlit as st
import openrouteservice
from geopy.geocoders import Nominatim
import math
import urllib.parse
from datetime import datetime

# Konfiguracja strony
st.set_page_config(page_title="WroTaxi Compare", page_icon="🚕", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; font-weight: bold; }
    .stTextInput>div>div>input { border-radius: 10px; }
    .tariff-info { 
        background-color: #fdf2e9; 
        padding: 15px; 
        border-radius: 10px; 
        text-align: center; 
        margin-bottom: 20px;
        border: 1px solid #e67e22;
        color: #d35400;
        font-weight: bold;
    }
    .info-box {
        font-size: 0.8em;
        color: #666;
        background-color: #f1f2f6;
        padding: 8px;
        border-radius: 5px;
        margin-top: 5px;
        border-left: 3px solid #ffa502;
    }
    .uber-variant {
        font-size: 0.85em;
        color: #111;
        background-color: #ffffff;
        padding: 6px 12px;
        border-radius: 8px;
        margin-top: 5px;
        border: 1px solid #ddd;
        display: flex;
        justify-content: space-between;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.05);
    }
    .disclaimer {
        font-size: 0.75em;
        color: #95a5a6;
        text-align: center;
        margin-top: 30px;
        padding: 15px;
        border-top: 1px solid #eee;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🚕 WroTaxi Compare")

# --- LOGIKA TARYF ---
now = datetime.now()
hour = (now.hour + 1) % 24 
is_night = (hour >= 22 or hour < 6)
is_weekend = (now.weekday() == 6)

if is_night or is_weekend:
    t_label = "🌙 TARYFA 2 (Noc/Weekend)"
    mnoznik = 1.45
    uber_surge = 1.3
else:
    t_label = "☀️ TARYFA 1 (Dzień)"
    mnoznik = 1.0
    uber_surge = 1.0

st.markdown(f"<div class='tariff-info'>{t_label}<br>Aktualna godzina: {hour:02d}:{now.minute:02d}</div>", unsafe_allow_html=True)

# --- KLUCZ API ---
ORS_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijc2N2YwMmI0Y2M2OTRkMjE5MDk5MDU4ZTg3NzMxYjYzIiwiaCI6Im11cm11cjY0In0='

def init_services():
    try:
        client = openrouteservice.Client(key=ORS_KEY)
        geolocator = Nominatim(user_agent="wro_taxi_precision_v38")
        return client, geolocator
    except: return None, None

client, geolocator = init_services()

start_adr = st.text_input("📍 Skąd we Wrocławiu?", placeholder="np. Wojaczka 10")
cel_adr = st.text_input("🏁 Dokąd?", placeholder="np. Celtycka 1")

if st.button("PORÓWNAJ CENY"):
    if start_adr and cel_adr:
        with st.spinner("Synchronizacja cen..."):
            try:
                s_full = f"{start_adr}, Wrocław"; c_full = f"{cel_adr}, Wrocław"
                l1 = geolocator.geocode(s_full); l2 = geolocator.geocode(c_full)
                
                if l1 and l2:
                    coords = ((l1.longitude, l1.latitude), (l2.longitude, l2.latitude))
                    route = client.directions(coordinates=coords, profile='driving-car', format='geojson')
                    km = route['features'][0]['properties']['summary']['distance'] / 1000
                    
                    # --- KALIBRACJA CEN PRECYZYJNA (v38) ---
                    # Wyliczone na podstawie Twoich testów (Wojaczka - Celtycka)
                    u_x_base = (8.3 + km * 2.33) * uber_surge
                    
                    itaxi_v = 9.0 + (km * 4.30 * mnoznik)
                    ryba_min = 20.50 + (math.ceil(km - 4) * (2.50 * mnoznik) if km > 4 else 0)
                    
                    dane = [
                        {
                            "Firma": "Uber 🚗", 
                            "Cena": f"od {u_x_base * 0.86:.2f} PLN", 
                            "Val": u_x_base * 0.86, "Type": "link",
                            "Link": f"https://m.uber.com/ul/?action=setPickup&pickup[latitude]={l1.latitude}&pickup[longitude]={l1.longitude}&dropoff[latitude]={l2.latitude}&dropoff[longitude]={l2.longitude}",
                            "Variants": [
                                {"name": "📉 Saver", "price": u_x_base * 0.86},
                                {"name": "🚗 UberX", "price": u_x_base},
                                {"name": "🔋 Hybrid", "price": u_x_base * 1.03},
                                {"name": "✨ Comfort", "price": u_x_base * 1.22}
                            ]
                        },
                        {
                            "Firma": "iTaxi 🚕", "Cena": f"~{itaxi_v:.2f} PLN", 
                            "Val": itaxi_v, "Type": "call", "Link": "tel:737737737"
                        },
                        {
                            "Firma": "Ryba Taxi 🐟", "Cena": f"~{ryba_min:.2f} PLN", 
                            "Val": ryba_min, "Type": "call", "Link": "tel:713441515"
                        },
                        {
                            "Firma": "Bolt ⚡", "Cena": f"~{(6.5 + km*2.8) * uber_surge:.2f} PLN", 
                            "Val": (6.5 + km*2.8) * uber_surge, "Type": "link", "Link": "bolt://ride"
                        }
                    ]
                    
                    st.success(f"🛣️ Dystans: {km:.2f} km")
                    
                    posortowane = sorted(dane, key=lambda x: x['Val'])
                    for item in posortowane:
                        with st.container():
                            c1, c2 = st.columns([2, 1])
                            with c1:
                                st.markdown(f"**{item['Firma']}**")
                                st.markdown(f"### {item['Cena']}")
                                if "Variants" in item:
                                    for v in item['Variants']:
                                        st.markdown(f"<div class='uber-variant'><span>{v['name']}</span><b>{v['price']:.2f} PLN</b></div>", unsafe_allow_html=True)
                            with c2:
                                st.write("")
                                if item['Type'] == "link": st.link_button("ZAMÓW", item['Link'])
                                else: st.link_button("ZADZWOŃ", item['Link'], type="secondary")
                            st.write("---")

            except Exception as e: st.error(f"Błąd: {e}")
