import streamlit as st
import openrouteservice
from geopy.geocoders import Nominatim
import math
from datetime import datetime

# Konfiguracja strony
st.set_page_config(page_title="WroTaxi Compare Pro", page_icon="🚕", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; font-weight: bold; background-color: #2e3136; color: white; }
    .tariff-info { 
        background-color: #f0f2f6; padding: 15px; border-radius: 10px; 
        text-align: center; margin-bottom: 20px; border-left: 5px solid #e67e22;
        font-weight: bold; color: #1f2937;
    }
    .variant-card {
        font-size: 0.85em; color: #111; background-color: #f9f9f9;
        padding: 6px 12px; border-radius: 8px; margin-top: 4px;
        border: 1px solid #eee; display: flex; justify-content: space-between;
    }
    .discount-tag { color: #27ae60; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚕 WroTaxi Compare v5.5")

# --- LOGIKA CZASOWA ---
now = datetime.now()
h = (now.hour + 1) % 24 
time_val = h + now.minute/60
day = now.weekday() 

is_weekend = (day >= 5)
is_night = (time_val >= 22 or time_val < 6)
is_peak = not is_weekend and ((7.5 <= time_val <= 9.5) or (15.5 <= time_val <= 18.5))

surge = 1.0

if is_night:
    t_status = "🌙 NOC (Parametry nocne)"
    u_base, u_km = 7.00, 1.85 
    b_base, b_km = 4.50, 2.30 
elif is_peak:
    t_status = "🚦 SZCZYT KOMUNIKACYJNY (Dynamiczny Uber/Bolt/FREENOW)"
    surge = 1.55
    u_base, u_km = 8.00, 2.10
    b_base, b_km = 5.00, 2.70 
else:
    t_status = "☀️ STANDARDOWY DZIEŃ"
    u_base, u_km = 8.00, 2.10
    b_base, b_km = 5.00, 2.70 

st.markdown(f"<div class='tariff-info'>{t_status}<br>Aktualna godzina: {h:02d}:{now.minute:02d}</div>", unsafe_allow_html=True)

# --- USŁUGI ---
ORS_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijc2N2YwMmI0Y2M2OTRkMjE5MDk5MDU4ZTg3NzMxYjYzIiwiaCI6Im11cm11cjY0In0='

def get_data():
    try:
        return openrouteservice.Client(key=ORS_KEY), Nominatim(user_agent="wrotaxi_v55_precision")
    except: return None, None

client, geolocator = get_data()

start_adr = st.text_input("📍 Skąd?", placeholder="np. Wojaczka 10")
cel_adr = st.text_input("🏁 Dokąd?", placeholder="np. Rynek")

col1, col2 = st.columns(2)
with col1: u_promo = st.slider("Zniżka Uber %", 0, 90, 0, 5)
with col2: b_promo = st.slider("Zniżka Bolt %", 0, 90, 0, 5)

if st.button("SPRAWDŹ CENY"):
    if start_adr and cel_adr:
        with st.spinner("Przeliczanie..."):
            try:
                l1 = geolocator.geocode(f"{start_adr}, Poland")
                l2 = geolocator.geocode(f"{cel_adr}, Poland")
                
                if l1 and l2:
                    res = client.directions(coordinates=((l1.longitude, l1.latitude), (l2.longitude, l2.latitude)), profile='driving-car', format='geojson')
                    km = res['features'][0]['properties']['summary']['distance'] / 1000
                    dur = res['features'][0]['properties']['summary']['duration'] / 60
                    
                    u_mult = (100 - u_promo) / 100
                    b_mult = (100 - b_promo) / 100

                    # 1. OBLICZENIA UBER I BOLT
                    uber_x = ((u_base + (km * u_km) + (dur * 0.15)) * surge) * u_mult
                    # Bolt: Dodano +2.00 (opłata operacyjna) oraz + (dur * 0.25) (opłata za czas)
                    bolt_std = ((b_base + (km * b_km) + (dur * 0.25) + 2.00) * surge) * b_mult
                    
                    # 2. OBLICZENIA FREENOW (z opłatą serwisową 2.00 PLN)
                    freenow_lite = ((u_base + (km * u_km) + (dur * 0.15)) * surge) + 2.00
                    
                    # 3. OBLICZENIA RYBA
                    ryba_min = 20.50 + (math.ceil(km - 4) * 2.50 if km > 4 else 0)
                    ryba_max = (ryba_min * 1.15) + 2.00 

                    dane = [
                        {
                            "Firma": "Uber 🚗",
                            "Btn": "WYBIERZ",
                            "Val": uber_x * 0.86, 
                            "Promo": u_promo,
                            "Main": f"od {uber_x * 0.86:.2f} PLN", 
                            "Link": f"https://m.uber.com/ul/?action=setPickup&pickup[latitude]={l1.latitude}&pickup[longitude]={l1.longitude}&dropoff[latitude]={l2.latitude}&dropoff[longitude]={l2.longitude}",
                            "Vars": [
                                ("📉 Czekaj i oszczędzaj", uber_x * 0.86), ("🚗 UberX", uber_x), ("🔋 Hybrid", uber_x * 1.01), ("✨ Comfort", uber_x * 1.18)
                            ]
                        },
                        {
                            "Firma": "Bolt ⚡",
                            "Btn": "WYBIERZ",
                            "Val": bolt_std * 0.90, # Wait & Save jest zazwyczaj 10% tańszy
                            "Promo": b_promo,
                            "Main": f"od {bolt_std * 0.90:.2f} PLN", 
                            "Link": "bolt://ride",
                            "Vars": [
                                ("⚡ Bolt", bolt_std), 
                                ("✨ Comfort", bolt_std * 1.15), 
                                ("📉 Wait and Save", bolt_std * 0.90)                    
                            ]
                        },
                        {
                            "Firma": "FREENOW 🔴",
                            "Btn": "WYBIERZ",
                            "Val": freenow_lite, 
                            "Promo": 0, 
                            "Main": f"~{freenow_lite:.2f} PLN", 
                            "Link": "freenow://", 
                            "Vars": [
                                ("🚗 Lite", freenow_lite), ("🚕 Taxi", freenow_lite * 1.25), ("✨ Comfort", freenow_lite * 1.40)
                            ]
                        },
                        {
                            "Firma": "Ryba Taxi 🐟",
                            "Btn": "ZADZWOŃ",
                            "Val": ryba_min, 
                            "Promo": 0, 
                            "Main": f"{ryba_min:.2f} - {ryba_max:.2f} PLN", 
                            "Link": "tel:713441515", 
                            "Vars": []
                        }
                    ]

                    st.success(f"🛣️ {km:.2f} km | ⏱️ {int(dur)} min")
                    
                    for item in sorted(dane, key=lambda x: x['Val']):
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            disc = f" <span class='discount-tag'>-{item['Promo']}%</span>" if item['Promo'] > 0 else ""
                            st.markdown(f"**{item['Firma']}**{disc}", unsafe_allow_html=True)
                            st.markdown(f"### {item['Main']}")
                            
                            if item['Vars']:
                                for v_name, v_price in item['Vars']:
                                    st.markdown(f"<div class='variant-card'><span>{v_name}</span><b>{v_price:.2f} PLN</b></div>", unsafe_allow_html=True)
                        with c2:
                            st.write("")
                            st.link_button(item['Btn'], item['Link'])
                        st.write("---")
            except Exception as e: st.error(f"Błąd mapy: {e}")
