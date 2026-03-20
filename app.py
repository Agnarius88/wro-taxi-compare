import streamlit as st
import openrouteservice
from geopy.geocoders import Nominatim
import pandas as pd
import math
import urllib.parse

# Ustawienia strony mobilnej
st.set_page_config(page_title="WroTaxi Compare", page_icon="🚕")

# Stylizacja przycisków
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #3498db; color: white; }
    .stDownloadButton>button { width: 100%; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚕 WroTaxi Compare")
st.subheader("Wrocław: Ryba vs Apps")

# --- KONFIGURACJA ---
ORS_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijc2N2YwMmI0Y2M2OTRkMjE5MDk5MDU4ZTg3NzMxYjYzIiwiaCI6Im11cm11cjY0In0='
client = openrouteservice.Client(key=ORS_KEY)
geolocator = Nominatim(user_agent="wro_taxi_final_mobile")

# --- INPUTY ---
start_adr = st.text_input("📍 Skąd odbieramy?", placeholder="np. Pasaż Grunwaldzki")
cel_adr = st.text_input("🏁 Dokąd jedziemy?", placeholder="np. Rynek, Wrocław")

if st.button("POKAŻ NAJTAŃSZĄ OPCJĘ"):
    if start_adr and cel_adr:
        with st.spinner("Przeliczam trasę..."):
            try:
                l1, l2 = geolocator.geocode(start_adr), geolocator.geocode(cel_adr)
                if not l1 or not l2:
                    st.error("Nie znalazłem adresu. Dodaj 'Wrocław' na końcu.")
                else:
                    # Logika trasy
                    coords = ((l1.longitude, l1.latitude), (l2.longitude, l2.latitude))
                    route = client.directions(coordinates=coords, profile='driving-car', format='geojson')
                    km = route['features'][0]['properties']['summary']['distance'] / 1000
                    minuty = round(route['features'][0]['properties']['summary']['duration'] / 60)
                    
                    # Ryba Taxi Wrocław (Twoje dane)
                    ryba_base = 20.0 + (math.ceil(km - 4) * 2.5 if km > 4 else 0)
                    if any(x in (start_adr+cel_adr).lower() for x in ["lotnisko", "airport"]): ryba_base += 5.0
                    
                   # Przygotowanie bezpiecznych linków
                    q_adr = urllib.parse.quote(cel_adr)
                    
                    dane = [
                        {
                            "Firma": "Ryba Taxi 🐟", 
                            "Cena": f"{ryba_base:.2f} - {ryba_base*1.2:.2f} PLN", 
                            "Link": "https://ryba-taxi.pl/zamow-online/", 
                            "Val": ryba_base
                        },
                        {
                            "Firma": "UberX 🚗", 
                            "Cena": f"~{8.0 + km*2.5:.2f} PLN", 
                            # Ten link na 100% otwiera apkę Ubera z celem:
                            "Link": f"https://m.uber.com/ul/?action=setPickup&pickup=my_location&dropoff[formatted_address]={q_adr}", 
                            "Val": 8.0 + km*2.5
                        },
                        {
                            "Firma": "Bolt ⚡", 
                            "Cena": f"~{6.5 + km*2.8:.2f} PLN", 
                            # Bolt często ignoruje adres, ale ten link chociaż otworzy apkę:
                            "Link": "bolt://ride", 
                            "Val": 6.5 + km*2.8
                        },
                        {
                            "Firma": "FreeNow 🚕", 
                            "Cena": f"~{9.0 + km*2.3:.2f} PLN", 
                            "Link": "freenow://", 
                            "Val": 9.0 + km*2.3
                        }
                    ]
                    
                    st.success(f"Dystans: {km:.2f} km | Czas: ~{minuty} min")
                    
                    # Wyświetlanie wyników w kartach
                    for item in sorted(dane, key=lambda x: x['Val']):
                        with st.container():
                            c1, c2 = st.columns([2, 1])
                            c1.markdown(f"**{item['Firma']}**\n### {item['Cena']}")
                            c2.link_button("ZAMÓW", item['Link'])
                            st.write("---")
            except Exception as e:
                st.error(f"Błąd mapy: {e}")
    else:
        st.warning("Wpisz oba adresy!")
