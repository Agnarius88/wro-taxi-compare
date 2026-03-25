import streamlit as st
import openrouteservice
from geopy.geocoders import Nominatim
import math
from datetime import datetime

# --- KONFIGURACJA v8.5 ---
st.set_page_config(page_title="WroTaxi v8.5 Precision", page_icon="🚕", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; font-weight: bold; background-color: #2e3136; color: white; border: none; }
    .tariff-info { 
        background-color: #f0f2f6; padding: 15px; border-radius: 10px; 
        text-align: center; margin-bottom: 20px; border-left: 5px solid #3498db;
        font-weight: bold; color: #1f2937;
    }
    .variant-card {
        font-size: 0.85em; color: #111; background-color: #ffffff;
        padding: 8px 12px; border-radius: 8px; margin-top: 5px;
        border: 1px solid #eee; display: flex; justify-content: space-between;
    }
    .price-main { font-size: 1.4em; font-weight: 800; color: #2c3e50; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚕 WroTaxi Compare v8.5")

# --- LOGIKA CZASOWA WROCŁAW ---
now = datetime.now()
h = now.hour 
time_val = h + now.minute/60
day = now.weekday() 

is_weekend = (day >= 5)
is_night = (time_val >= 22 or time_val < 6)
is_peak = not is_weekend and ((7.2 <= time_val <= 9.3) or (15.2 <= time_val <= 18.8))

# Ustawienia bazowe
u_base, u_km, u_min = 8.00, 2.15, 0.20
b_base, b_km = 5.50, 2.80

if is_night:
    t_status = "🌙 NOC"
    u_surge, b_surge = 1.0, 1.0
elif is_peak:
    t_status = "🚦 SZCZYT POPOŁUDNIOWY"
    u_surge = 1.53  # Kalibracja pod Twoje 48.95 PLN
    b_surge = 1.28  # Bolt ma lżejszy szczyt we Wrocławiu
else:
    t_status = "☀️ STANDARDOWY DZIEŃ"
    u_surge, b_surge = 1.0, 1.0

st.markdown(f"<div class='tariff-info'>{t_status}<br>Godzina pomiaru: {h:02d}:{now.minute:02d}</div>", unsafe_allow_html=True)

# --- API ---
ORS_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijc2N2YwMmI0Y2M2OTRkMjE5MDk5MDU4ZTg3NzMxYjYzIiwiaCI6Im11cm11cjY0In0='
client = openrouteservice.Client(key=ORS_KEY)
geolocator = Nominatim(user_agent="wrotaxi_85")

start_adr = st.text_input("📍 Skąd?", "Wojaczka 10, Wrocław")
cel_adr = st.text_input("🏁 Dokąd?", "Celtycka 1, Wrocław")

col1, col2 = st.columns(2)
with col1: u_promo = st.slider("Zniżka Uber %", 0, 90, 0, 5)
with col2: b_promo = st.slider("Zniżka Bolt %", 0, 90, 30, 5) # Ustawione na Twoje 30%

if st.button("SPRAWDŹ CENY DLA TRASY"):
    if start_adr and cel_adr:
        with st.spinner("Pobieranie danych z map..."):
            l1 = geolocator.geocode(start_adr)
            l2 = geolocator.geocode(cel_adr)
            
            if l1 and l2:
                res = client.directions(coordinates=((l1.longitude, l1.latitude), (l2.longitude, l2.latitude)), profile='driving-car', format='geojson')
                km = res['features'][0]['properties']['summary']['distance'] / 1000
                dur = res['features'][0]['properties']['summary']['duration'] / 60
                
                # 1. OBLICZENIA UBER
                ux_val = ((u_base + (km * u_km) + (dur * u_min)) * u_surge) * ((100-u_promo)/100)
                
                # 2. OBLICZENIA BOLT
                bolt_std = ((b_base + (km * b_km) + 3.70) * b_surge) * ((100-b_promo)/100)

                dane = [
                    {
                        "Firma": "Uber 🚗",
                        "Val": ux_val * 0.78, # Skorygowany mnożnik "Czekaj" na 0.78
                        "Main": f"od {ux_val * 0.78:.2f} PLN",
                        "Link": f"https://m.uber.com/ul/?action=setPickup&pickup[latitude]={l1.latitude}&pickup[longitude]={l1.longitude}&dropoff[latitude]={l2.latitude}&dropoff[longitude]={l2.longitude}",
                        "Vars": [
                            ("📉 Czekaj i oszczędzaj", ux_val * 0.779), # Cel: ~38.15
                            ("🚗 UberX / 🔋 Hybrid", ux_val),           # Cel: ~48.95
                            ("✨ Comfort", ux_val * 1.185)              # Cel: ~57.97
                        ]
                    },
                    {
                        "Firma": "Bolt ⚡",
                        "Val": bolt_std - 8.00, # W szczycie Bolt obniża Wait o ok. 8 zł na tej trasie
                        "Main": f"od {bolt_std - 8.00:.2f} PLN",
                        "Link": "bolt://ride",
                        "Vars": [
                            ("⚡ Bolt", bolt_std),                      # Cel: ~32.90
                            ("✨ Comfort", bolt_std + 5.00),            # Cel: ~37.90
                            ("📉 Wait and Save", bolt_std - 8.00)       # Cel: ~24.90
                        ]
                    }
                ]

                st.success(f"🛣️ Dystans: {km:.2f} km | ⏱️ Czas: {int(dur)} min")
                
                for item in sorted(dane, key=lambda x: x['Val']):
                    st.markdown(f"**{item['Firma']}**")
                    st.markdown(f"<div class='price-main'>{item['Main']}</div>", unsafe_allow_html=True)
                    for v_name, v_price in item['Vars']:
                        st.markdown(f"<div class='variant-card'><span>{v_name}</span><b>{v_price:.2f} PLN</b></div>", unsafe_allow_html=True)
                    st.link_button("WYBIERZ", item['Link'])
                    st.write("---")
