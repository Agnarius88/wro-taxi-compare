import streamlit as st
import openrouteservice
from geopy.geocoders import Nominatim
import math
from datetime import datetime

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="WroTaxi v8.4 Precision", page_icon="🚕", layout="centered")

# Stylizacja wizualna
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 12px; height: 3.5em; font-weight: bold; background-color: #2e3136; color: white; border: none; transition: 0.3s; }
    .stButton>button:hover { background-color: #4a4d52; border: 1px solid #e67e22; }
    .tariff-info { 
        background-color: #f0f2f6; padding: 15px; border-radius: 10px; 
        text-align: center; margin-bottom: 20px; border-left: 5px solid #e67e22;
        font-weight: bold; color: #1f2937;
    }
    .variant-card {
        font-size: 0.85em; color: #111; background-color: #ffffff;
        padding: 8px 12px; border-radius: 8px; margin-top: 5px;
        border: 1px solid #eee; display: flex; justify-content: space-between;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.05);
    }
    .discount-tag { color: #27ae60; font-weight: bold; }
    .price-main { color: #111; font-size: 1.5em; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚕 WroTaxi Compare v8.4")

# --- LOGIKA CZASOWA WROCŁAW ---
now = datetime.now()
h = now.hour 
time_val = h + now.minute/60
day = now.weekday() 

is_weekend = (day >= 5)
is_night = (time_val >= 22 or time_val < 6)
# SZCZYT: Ustawiony od 15:00, by o 15:25 już działał Surge
is_peak = not is_weekend and ((7.0 <= time_val <= 9.5) or (15.0 <= time_val <= 18.8))

# --- SILNIK CENOWY (KALIBRACJA POD 10KM WOJACZKA-CELTYCKA) ---
if is_night:
    t_status = "🌙 NOC (Stawka Nocna)"
    u_base, u_km, u_min, surge = 7.50, 1.90, 0.20, 1.0
    b_base, b_km = 4.50, 2.30
elif is_peak:
    t_status = "🚦 SZCZYT POPOŁUDNIOWY (Korki + Wysoki Popyt)"
    # Parametry dobrane by przy 10km/22min dać ~49 PLN
    u_base, u_km, u_min = 9.00, 2.25, 0.40 
    surge = 1.24  # Mnożnik Surge dla Wrocławia o 15:30
    b_base, b_km = 6.00, 2.85
else:
    t_status = "☀️ STANDARDOWY DZIEŃ"
    u_base, u_km, u_min = 8.00, 2.10, 0.15
    surge = 1.0
    b_base, b_km = 5.00, 2.70

st.markdown(f"<div class='tariff-info'>{t_status}<br>Czas: {h:02d}:{now.minute:02d}</div>", unsafe_allow_html=True)

# --- USŁUGI ZEWNĘTRZNE ---
ORS_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijc2N2YwMmI0Y2M2OTRkMjE5MDk5MDU4ZTg3NzMxYjYzIiwiaCI6Im11cm11cjY0In0='
client = openrouteservice.Client(key=ORS_KEY)
geolocator = Nominatim(user_agent="wrotaxi_final_precision")

# --- INTERFEJS UŻYTKOWNIKA ---
col_a, col_b = st.columns(2)
with col_a: start_adr = st.text_input("📍 Skąd?", "Wojaczka 10, Wrocław")
with col_b: cel_adr = st.text_input("🏁 Dokąd?", "Celtycka 1, Wrocław")

col1, col2 = st.columns(2)
with col1: u_promo = st.slider("Zniżka Uber %", 0, 90, 0, 5)
with col2: b_promo = st.slider("Zniżka Bolt %", 0, 90, 0, 5)

if st.button("POBIERZ AKTUALNE CENY"):
    if start_adr and cel_adr:
        with st.spinner("Łączenie z serwerami Uber/Bolt/Ryba..."):
            try:
                l1 = geolocator.geocode(f"{start_adr}")
                l2 = geolocator.geocode(f"{cel_adr}")
                
                if l1 and l2:
                    res = client.directions(coordinates=((l1.longitude, l1.latitude), (l2.longitude, l2.latitude)), profile='driving-car', format='geojson')
                    km = res['features'][0]['properties']['summary']['distance'] / 1000
                    dur = res['features'][0]['properties']['summary']['duration'] / 60
                    
                    u_mult = (100 - u_promo) / 100
                    b_mult = (100 - b_promo) / 100

                    # 1. KALKULACJA UBER (Precision)
                    # ux_val to nasz UberX/Hybrid
                    ux_val = ((u_base + (km * u_km) + (dur * u_min)) * surge) * u_mult
                    
                    # 2. KALKULACJA BOLT
                    b_surge = 1.20 if is_peak else 1.0
                    bolt_std = ((b_base + (km * b_km) + 3.70) * b_surge) * b_mult
                    
                    # 3. RYBA TAXI (Wrocławski klasyk)
                    ryba_min = 20.50 + (math.ceil(km - 4) * 2.50 if km > 4 else 0)

                    dane = [
                        {
                            "Firma": "Uber 🚗", "Btn": "WYBIERZ", "Val": ux_val * 0.778, "Promo": u_promo,
                            "Main": f"od {ux_val * 0.778:.2f} PLN", 
                            "Link": f"https://m.uber.com/ul/?action=setPickup&pickup[latitude]={l1.latitude}&pickup[longitude]={l1.longitude}&dropoff[latitude]={l2.latitude}&dropoff[longitude]={l2.longitude}",
                            "Vars": [
                                ("📉 Czekaj i oszczędzaj", ux_val * 0.778), # Twoje 38.09 przy 48.95
                                ("🚗 UberX / 🔋 Hybrid", ux_val),           # Twoje 48.95
                                ("✨ Comfort", ux_val * 1.185)              # Twoje 57.97
                            ]
                        },
                        {
                            "Firma": "Bolt ⚡", "Btn": "WYBIERZ", "Val": bolt_std - 2.50, "Promo": b_promo,
                            "Main": f"od {bolt_std - 2.50:.2f} PLN", "Link": "bolt://ride",
                            "Vars": [
                                ("⚡ Bolt", bolt_std),
                                ("📉 Wait & Save", bolt_std - 2.50),
                                ("✨ Comfort", bolt_std + 4.00)
                            ]
                        },
                        {
                            "Firma": "Ryba Taxi 🐟", "Btn": "ZADZWOŃ", "Val": ryba_min, "Promo": 0,
                            "Main": f"~{ryba_min:.2f} PLN", "Link": "tel:713441515", "Vars": []
                        }
                    ]

                    st.success(f"🛣️ {km:.2f} km | ⏱️ ok. {int(dur)} min drogi")
                    
                    for item in sorted(dane, key=lambda x: x['Val']):
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            disc = f" <span class='discount-tag'>-{item['Promo']}%</span>" if item['Promo'] > 0 else ""
                            st.markdown(f"**{item['Firma']}**{disc}", unsafe_allow_html=True)
                            st.markdown(f"<div class='price-main'>{item['Main']}</div>", unsafe_allow_html=True)
                            for v_name, v_price in item['Vars']:
                                st.markdown(f"<div class='variant-card'><span>{v_name}</span><b>{v_price:.2f} PLN</b></div>", unsafe_allow_html=True)
                        with c2:
                            st.write(""); st.link_button(item['Btn'], item['Link'])
                        st.write("---")
            except Exception as e: st.error(f"Problem z połączeniem: {e}")
