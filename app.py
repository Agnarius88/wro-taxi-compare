import streamlit as st
import openrouteservice
from geopy.geocoders import Nominatim
import math
from datetime import datetime

# Konfiguracja strony
st.set_page_config(page_title="Taxi Compare Poland", page_icon="🚕", layout="centered")

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

st.title("🚕 Taxi Compare POLSKA v7.5")

# --- LOGIKA CZASOWA ---
now = datetime.now()
h = (now.hour + 1) % 24 
time_val = h + now.minute/60
day = now.weekday() 

is_weekend = (day >= 5)
is_night = (time_val >= 22 or time_val < 6)
is_peak = not is_weekend and ((7.5 <= time_val <= 9.5) or (15.5 <= time_val <= 18.5))

ORS_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijc2N2YwMmI0Y2M2OTRkMjE5MDk5MDU4ZTg3NzMxYjYzIiwiaCI6Im11cm11cjY0In0='

def get_data():
    try:
        return openrouteservice.Client(key=ORS_KEY), Nominatim(user_agent="taxi_poland_v75")
    except: return None, None

client, geolocator = get_data()

start_adr = st.text_input("📍 Skąd (ulica i miasto)?", placeholder="np. Inflancka 19 Warszawa")
cel_adr = st.text_input("🏁 Dokąd?", placeholder="np. Dworzec Centralny")

col1, col2 = st.columns(2)
with col1: u_promo = st.slider("Zniżka Uber %", 0, 90, 0, 5)
with col2: b_promo = st.slider("Zniżka Bolt %", 0, 90, 0, 5)

if st.button("PRZELICZ TRASĘ"):
    if start_adr and cel_adr:
        with st.spinner("Analiza lokalizacji i stawek rynkowych..."):
            try:
                l1 = geolocator.geocode(f"{start_adr}, Poland", addressdetails=True)
                l2 = geolocator.geocode(f"{cel_adr}, Poland")
                
                if l1 and l2:
                    # WYKRYWANIE MIASTA DO STAWEK
                    addr = l1.raw.get('address', {})
                    city = addr.get('city') or addr.get('town') or addr.get('village') or "Polska"
                    
                    # --- SILNIK STAWEK OGÓLNOPOLSKICH ---
                    # 1. PROFIL WARSZAWA
                    if any(x in city for x in ["Warszawa", "Warsaw"]):
                        u_base, u_km, u_min = 9.00, 2.35, 0.35 
                        b_base, b_km = 6.00, 2.90
                        city_label = "WARSZAWA (Stawka Premium)"
                    
                    # 2. PROFIL DUŻE MIASTA (Kraków, Gdańsk, Gdynia, Poznań)
                    elif any(x in city for x in ["Kraków", "Krakow", "Gdańsk", "Gdansk", "Poznań", "Poznan"]):
                        u_base, u_km, u_min = 8.50, 2.20, 0.20
                        b_base, b_km = 5.50, 2.80
                        city_label = f"{city.upper()} (Stawka Metropolitalna)"
                    
                    # 3. PROFIL STANDARD (Wrocław i reszta)
                    else:
                        u_base, u_km, u_min = 8.00, 2.10, 0.15
                        b_base, b_km = 5.00, 2.70
                        city_label = f"{city.upper()} (Stawka Standard)"

                    # --- MODYFIKATORY CZASOWE ---
                    surge = 1.0
                    if is_night:
                        t_status = f"🌙 NOC | {city_label}"
                        u_base, u_km = u_base - 1.0, u_km - 0.25
                    elif (13.5 <= time_val <= 14.5):
                        t_status = f"📉 OKNO PROMOCYJNE BOLT | {city_label}"
                        b_base = b_base - 2.0 # Twoje słynne -2 zł
                    elif is_peak:
                        t_status = f"🚦 SZCZYT | {city_label}"
                        surge = 1.55
                    else:
                        t_status = f"☀️ DZIEŃ | {city_label}"

                    # OBLICZENIA TRASY
                    res = client.directions(coordinates=((l1.longitude, l1.latitude), (l2.longitude, l2.latitude)), profile='driving-car', format='geojson')
                    km = res['features'][0]['properties']['summary']['distance'] / 1000
                    dur = res['features'][0]['properties']['summary']['duration'] / 60
                    
                    u_mult = (100 - u_promo) / 100
                    b_mult = (100 - b_promo) / 100

                    # KALKULACJA FINALNA
                    uber_x = ((u_base + (km * u_km) + (dur * u_min)) * surge) * u_mult
                    bolt_std = ((b_base + (km * b_km) + 3.70) * surge) * b_mult
                    freenow_lite = ((u_base + (km * u_km) + (dur * u_min)) * surge) + 2.00
                    
                    st.markdown(f"<div class='tariff-info'>{t_status}<br>{km:.2f} km | ~{int(dur)} min</div>", unsafe_allow_html=True)

                    dane = [
                        {
                            "Firma": "Uber 🚗", "Btn": "WYBIERZ", "Val": uber_x * 0.86, "Promo": u_promo,
                            "Main": f"od {uber_x * 0.86:.2f} PLN", 
                            "Link": f"https://m.uber.com/ul/?action=setPickup&pickup[latitude]={l1.latitude}&pickup[longitude]={l1.longitude}&dropoff[latitude]={l2.latitude}&dropoff[longitude]={l2.longitude}",
                            "Vars": [("📉 Wait", uber_x * 0.86), ("🚗 UberX", uber_x), ("✨ Comfort", uber_x * 1.18)]
                        },
                        {
                            "Firma": "Bolt ⚡", "Btn": "WYBIERZ", "Val": bolt_std - 2.40, "Promo": b_promo,
                            "Main": f"od {bolt_std - 2.40:.2f} PLN", 
                            "Link": "bolt://ride",
                            "Vars": [("⚡ Bolt", bolt_std), ("✨ Comfort", bolt_std + 4.00), ("📉 Wait", bolt_std - 2.40)]
                        },
                        {
                            "Firma": "FREENOW 🔴", "Btn": "ZAMÓW", "Val": freenow_lite, "Promo": 0,
                            "Main": f"~{freenow_lite:.2f} PLN", 
                            "Link": "intent://#Intent;scheme=freenow;package=taxi.android.client;end", 
                            "Vars": [("🚗 Lite", freenow_lite), ("✨ Comfort", freenow_lite * 1.30), ("🚐 XL", freenow_lite * 1.60)]
                        }
                    ]

                    # RYBA TAXI - TYLKO WROCŁAW
                    if "Wrocław" in city or "Wroclaw" in city:
                        ryba_min = 20.50 + (math.ceil(km - 4) * 2.50 if km > 4 else 0)
                        dane.append({"Firma": "Ryba Taxi 🐟", "Btn": "ZADZWOŃ", "Val": ryba_min, "Promo": 0, "Main": f"~{ryba_min:.2f} PLN", "Link": "tel:713441515", "Vars": []})

                    # RENDEROWANIE WYNIKÓW
                    for item in sorted(dane, key=lambda x: x['Val']):
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            disc = f" <span class='discount-tag'>-{item['Promo']}%</span>" if item['Promo'] > 0 else ""
                            st.markdown(f"**{item['Firma']}**{disc}", unsafe_allow_html=True)
                            st.markdown(f"### {item['Main']}")
                            for v_name, v_price in item['Vars']:
                                st.markdown(f"<div class='variant-card'><span>{v_name}</span><b>{v_price:.2f} PLN</b></div>", unsafe_allow_html=True)
                        with c2:
                            st.write(""); st.link_button(item['Btn'], item['Link'])
                        st.write("---")
            except Exception as e: st.error(f"Błąd: {e}")
