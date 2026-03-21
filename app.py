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
    .tariff-info { background-color: #f0f2f6; padding: 10px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚕 WroTaxi Compare")

# --- LOGIKA CZASU (TARYFA NOCKA/WEEKEND) ---
# Streamlit serwery są w UTC, dodajemy +1h dla Polski (lub +2h w lato)
now = datetime.now()
hour = (now.hour + 1) % 24 
is_night = (hour >= 22 or hour < 6)
is_weekend = (now.weekday() == 6) # Niedziela

if is_night or is_weekend:
    t_label = "🌙 TARYFA NOCNA/WEEKENDOWA"
    mnoznik = 1.5
else:
    t_label = "☀️ TARYFA DZIENNA"
    mnoznik = 1.0

st.markdown(f"<div class='tariff-info'>Aktualnie: <b>{t_label}</b> (Godzina: {hour:02d}:00)</div>", unsafe_allow_html=True)

# --- KLUCZ API ---
ORS_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijc2N2YwMmI0Y2M2OTRkMjE5MDk5MDU4ZTg3NzMxYjYzIiwiaCI6Im11cm11cjY0In0='

def init_services():
    try:
        client = openrouteservice.Client(key=ORS_KEY)
        geolocator = Nominatim(user_agent="wro_taxi_night_v25")
        return client, geolocator
    except: return None, None

client, geolocator = init_services()

start_adr = st.text_input("📍 Skąd?", placeholder="np. Wojaczka 10")
cel_adr = st.text_input("🏁 Dokąd?", placeholder="np. Celtycka 1")

if st.button("SPRAWDŹ CENY"):
    if start_adr and cel_adr:
        with st.spinner("Przeliczam taryfę..."):
            try:
                s_full = f"{start_adr}, Wrocław"; c_full = f"{cel_adr}, Wrocław"
                l1 = geolocator.geocode(s_full); l2 = geolocator.geocode(c_full)
                
                if l1 and l2:
                    coords = ((l1.longitude, l1.latitude), (l2.longitude, l2.latitude))
                    route = client.directions(coordinates=coords, profile='driving-car', format='geojson')
                    km = route['features'][0]['properties']['summary']['distance'] / 1000
                    
                    q_start = urllib.parse.quote(l1.address.split(',')[0])
                    q_cel = urllib.parse.quote(l2.address.split(',')[0])

                    # --- DYNAMIZACJA TARYF ---
                    
                    # iTaxi: Twoja kalibracja (4.30 za dnia, ok 6.30 w nocy)
                    itaxi_base_km = 4.30 * mnoznik
                    itaxi_val = 9.0 + (km * itaxi_base_km)
                    
                    # Ryba Taxi: (Dzień: 2.50/km, Noc: ok 3.75/km)
                    ryba_km_rate = 2.50 * mnoznik
                    ryba_min = 20.50 + (math.ceil(km - 4) * ryba_km_rate if km > 4 else 0)
                    ryba_max = (ryba_min * 1.15) + 2.00

                    dane = [
                        {"Firma": "UberX 🚗", "Cena": f"~{8.0 + km*2.5*mnoznik:.2f} PLN", "Link": f"https://m.uber.com/ul/?action=setPickup&pickup[latitude]={l1.latitude}&pickup[longitude]={l1.longitude}&dropoff[latitude]={l2.latitude}&dropoff[longitude]={l2.longitude}", "Val": 8.0 + km*2.5*mnoznik, "Active": True},
                        {"Firma": "iTaxi 🚕", "Cena": f"~{itaxi_val:.2f} PLN", "Link": "", "Val": itaxi_val, "Active": False},
                        {"Firma": "Ryba Taxi 🐟", "Cena": f"{ryba_min:.2f} - {ryba_max:.2f} PLN", "Link": "", "Val": ryba_min, "Active": False},
                        {"Firma": "Bolt ⚡", "Cena": f"~{6.5 + km*2.8*mnoznik:.2f} PLN", "Link": "bolt://ride", "Val": 6.5 + km*2.8*mnoznik, "Active": True},
                        {"Firma": "FreeNow 🚕", "Cena": f"~{5.0 + km*3.0*mnoznik:.2f} PLN", "Link": f"https://www.free-now.com/pl/zamow-taksowke/?pickupLat={l1.latitude}&pickupLng={l1.longitude}&dropOffLat={l2.latitude}&dropOffLng={l2.longitude}", "Val": 5.0 + km*3.0*mnoznik, "Active": True}
                    ]
                    
                    st.success(f"🛣️ Dystans: {km:.2f} km")
                    st.write("---")
                    
                    posortowane = sorted(dane, key=lambda x: x['Val'])
                    for item in posortowane:
                        with st.container():
                            c1, c2 = st.columns([2, 1])
                            with c1:
                                st.markdown(f"**{item['Firma']}**")
                                st.markdown(f"### {item['Cena']}")
                            with c2:
                                if item['Active']:
                                    st.link_button("ZAMÓW", item['Link'])
                                else:
                                    st.button("INFO", disabled=True, key=item['Firma'])
                            st.write("---")
                else: st.error("Nie znaleziono adresu.")
            except Exception as e: st.error(f"Błąd: {e}")
