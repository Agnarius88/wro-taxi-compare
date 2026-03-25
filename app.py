import streamlit as st
import openrouteservice
from geopy.geocoders import Nominatim
import math
from datetime import datetime

# --- KONFIGURACJA v8.7 FULL PRECISION ---
st.set_page_config(page_title="WroTaxi v8.7 Full", page_icon="🚕", layout="centered")

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
        padding: 6px 12px; border-radius: 8px; margin-top: 4px;
        border: 1px solid #eee; display: flex; justify-content: space-between;
    }
    .price-main { font-size: 1.4em; font-weight: 800; color: #2c3e50; margin-bottom: 5px; }
    .discount-tag { color: #27ae60; font-weight: bold; font-size: 0.9em; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚕 WroTaxi Compare v8.7")

# --- LOGIKA CZASOWA ---
now = datetime.now()
h = now.hour 
time_val = h + now.minute/60
day = now.weekday() 

is_weekend = (day >= 5)
is_night = (time_val >= 22 or time_val < 6)

# Ustawienia bazowe stawek
u_base, u_km, u_min = 8.00, 2.15, 0.20
b_base, b_km = 5.50, 2.80
u_surge, b_surge = 1.0, 1.0

if is_night:
    t_status = "🌙 NOC"
    u_surge, b_surge = 1.0, 1.0
elif (7.2 <= time_val <= 9.5) or (15.2 <= time_val <= 18.8):
    t_status = "🚦 SZCZYT KOMUNIKACYJNY"
    u_surge = 1.53  # Kalibracja pod Twoje 48.95 PLN (Uber)
    b_surge = 1.28  # Kalibracja pod Twoje 32.90 PLN (Bolt)
elif (11.0 <= time_val < 13.5): 
    t_status = "🍴 STANDARDOWY LUNCH"
    u_surge, b_surge = 1.05, 1.05
else:
    t_status = "☀️ STANDARDOWY DZIEŃ"
    u_surge, b_surge = 1.0, 1.0

# POPRAWIONA LINIA HTML:
st.markdown(f"<div class='tariff-info'>{t_status}<br>Godzina pomiaru: {h:02d}:{now.minute:02d}</div>", unsafe_allow_html=True)

# --- API ---
ORS_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijc2N2YwMmI0Y2M2OTRkMjE5MDk5MDU4ZTg3NzMxYjYzIiwiaCI6Im11cm11cjY0In0='
client = openrouteservice.Client(key=ORS_KEY)
geolocator = Nominatim(user_agent="wrotaxi_87_full")

start_adr = st.text_input("📍 Skąd?", "Wojaczka 10, Wrocław")
cel_adr = st.text_input("🏁 Dokąd?", "Celtycka 1, Wrocław")

col1, col2 = st.columns(2)
with col1: u_promo = st.slider("Zniżka Uber %", 0, 90, 0, 5)
with col2: b_promo = st.slider("Zniżka Bolt %", 0, 90, 30, 5)

if st.button("SPRAWDŹ WSZYSTKIE CENY"):
    if start_adr and cel_adr:
        with st.spinner("Przeliczanie trasy Wojaczka -> Celtycka..."):
            try:
                l1 = geolocator.geocode(f"{start_adr}, Wrocław")
                l2 = geolocator.geocode(f"{cel_adr}, Wrocław")
                
                if l1 and l2:
                    res = client.directions(coordinates=((l1.longitude, l1.latitude), (l2.longitude, l2.latitude)), profile='driving-car', format='geojson')
                    km = res['features'][0]['properties']['summary']['distance'] / 1000
                    dur = res['features'][0]['properties']['summary']['duration'] / 60
                    
                    # --- KALKULACJE ---
                    u_mult = (100 - u_promo) / 100
                    b_mult = (100 - b_promo) / 100
                    
                    # UberX (Cel: ~48.95)
                    uber_x = ((u_base + (km * u_km) + (dur * u_min)) * u_surge) * u_mult
                    
                    # Bolt Standard (Cel: ~32.90)
                    bolt_std = ((b_base + (km * b_km) + 3.70) * b_surge) * b_mult
                    
                    # Freenow (Szacunek na bazie Ubera)
                    freenow_lite = ((u_base + (km * u_km) + (dur * 0.15)) * u_surge) + 2.00
                    
                    # Ryba Taxi
                    ryba_min = 20.50 + (math.ceil(km - 4) * 2.50 if km > 4 else 0)
                    ryba_max = (ryba_min * 1.15) + 2.00

                    dane = [
                        {
                            "Firma": "Uber 🚗", "Val": uber_x * 0.779, "Promo": u_promo,
                            "Main": f"od {uber_x * 0.779:.2f} PLN", "Btn": "WYBIERZ",
                            "Link": f"https://m.uber.com/ul/?action=setPickup&pickup[latitude]={l1.latitude}&pickup[longitude]={l1.longitude}&dropoff[latitude]={l2.latitude}&dropoff[longitude]={l2.longitude}",
                            "Vars": [("📉 Czekaj i oszczędzaj", uber_x * 0.779), ("🚗 UberX / Hybrid", uber_x), ("✨ Comfort", uber_x * 1.185)]
                        },
                        {
                            "Firma": "Bolt ⚡", "Val": bolt_std - 8.00, "Promo": b_promo,
                            "Main": f"od {bolt_std - 8.00:.2f} PLN", "Btn": "WYBIERZ",
                            "Link": "bolt://ride",
                            "Vars": [("⚡ Bolt", bolt_std), ("✨ Comfort", bolt_std + 5.00), ("📉 Wait and Save", bolt_std - 8.00)]
                        },
                        {
                            "Firma": "FREENOW 🔴", "Val": freenow_lite, "Promo": 0,
                            "Main": f"~{freenow_lite:.2f} PLN", "Btn": "W APCE",
                            "Link": "intent://#Intent;scheme=freenow;package=taxi.android.client;end",
                            "Vars": [("🚗 Lite / Green", freenow_lite), ("🚕 Taxi", freenow_lite * 1.20), ("✨ Comfort", freenow_lite * 1.30)]
                        },
                        {
                            "Firma": "Ryba Taxi 🐟", "Val": ryba_min, "Promo": 0,
                            "Main": f"{ryba_min:.2f} - {ryba_max:.2f} PLN", "Btn": "ZADZWOŃ",
                            "Link": "tel:713441515", "Vars": [("🚕 Licznik (szacunek)", ryba_min)]
                        }
                    ]

                    st.success(f"🛣️ {km:.2f} km | ⏱️ {int(dur)} min")
                    
                    for item in sorted(dane, key=lambda x: x['Val']):
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            disc = f" <span class='discount-tag'>-{item['Promo']}%</span>" if item['Promo'] > 0 else ""
                            st.markdown(f"**{item['Firma']}**{disc}", unsafe_allow_html=True)
                            st.markdown(f"<div class='price-main'>{item['Main']}</div>", unsafe_allow_html=True)
                            for v_name, v_price in item['Vars']:
                                st.markdown(f"<div class='variant-card'><span>{v_name}</span><b>{v_price:.2f} PLN</b></div>", unsafe_allow_html=True)
                        with c2:
                            st.write(""); st.write("")
                            st.link_button(item['Btn'], item['Link'])
                        st.write("---")
            except Exception as e:
                st.error(f"Wystąpił błąd: {e}")
