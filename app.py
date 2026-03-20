import streamlit as st
import openrouteservice
from geopy.geocoders import Nominatim
import pandas as pd
import math
import urllib.parse

# 1. Konfiguracja strony
st.set_page_config(page_title="WroTaxi", page_icon="🚕")

# Stylizacja przycisków
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; background-color: #3498db; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚕 WroTaxi Compare")

# KLUCZ ORS
ORS_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijc2N2YwMmI0Y2M2OTRkMjE5MDk5MDU4ZTg3NzMxYjYzIiwiaCI6Im11cm11cjY0In0='

try:
    client = openrouteservice.Client(key=ORS_KEY)
    geolocator = Nominatim(user_agent="wro_taxi_v6_final")
except Exception:
    st.error("Problem z połączeniem. Odśwież stronę.")

start_adr = st.text_input("📍 Skąd?", placeholder="np. Dworzec Główny, Wrocław")
cel_adr = st.text_input("🏁 Dokąd?", placeholder="np. Magnolia Park, Wrocław")

if st.button("SPRAWDŹ CENY"):
    if start_adr and cel_adr:
        with st.spinner("Liczenie trasy..."):
            try:
                # Geo-kodowanie (z wymuszeniem Wrocławia)
                s_query = f"{start_adr}, Wrocław" if "Wrocław" not in start_adr else start_adr
                c_query = f"{cel_adr}, Wrocław" if "Wrocław" not in cel_adr else cel_adr
                
                l1 = geolocator.geocode(s_query)
                l2 = geolocator.geocode(c_query)
                
                if l1 and l2:
                    coords = ((l1.longitude, l1.latitude), (l2.longitude, l2.latitude))
                    route = client.directions(coordinates=coords, profile='driving-car', format='geojson')
                    
                    km = route['features'][0]['properties']['summary']['distance'] / 1000
                    minuty = round(route['features'][0]['properties']['summary']['duration'] / 60)
                    
                    # --- OBLICZENIA ---
                    # Ryba Taxi: baza 20zł (do 4km), potem 2.5zł/km
                    ryba_min = 20.0 + (math.ceil(km - 4) * 2.5 if km > 4 else 0)
                    ryba_max = ryba_min * 1.2 # zakres +20% na korki
                    
                    q_start_name = urllib.parse.quote(l1.address)
                    q_cel_name = urllib.parse.quote(l2.address)

                    dane = [
                        {
                            "Firma": "UberX 🚗", 
                            "Cena": f"~{8.0 + km*2.5:.2f} PLN", 
                            "Link": f"https://m.uber.com/ul/?action=setPickup&pickup[latitude]={l1.latitude}&pickup[longitude]={l1.longitude}&pickup[nickname]={q_start_name}&dropoff[latitude]={l2.latitude}&dropoff[longitude]={l2.longitude}&dropoff[nickname]={q_cel_name}", 
                            "Val": 8.0 + km*2.5
                        },
                        {
                            "Firma": "Ryba Taxi 🐟", 
                            "Cena": f"{ryba_min:.2f} - {ryba_max:.2f} PLN", 
                            "Link": "https://rybataxi.pl/app/", 
                            "Val": ryba_min
                        },
                        {
                            "Firma": "Bolt ⚡", 
                            "Cena": f"~{6.5 + km*2.8:.2f} PLN", 
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
                    
                    st.success(f"🛣️ {km:.2f} km | ⌛ {minuty} min")
                    
                    # Sortowanie od najtańszej opcji
                    for item in sorted(dane, key=lambda x: x['Val']):
                        c1, c2 = st.columns([2, 1])
                        with c1: 
                            st.markdown(f"**{item['Firma']}**")
                            st.markdown(f"### {item['Cena']}")
                        with c2: 
                            st.link_button("ZAMÓW", item['Link'])
                        st.write("---")
                else:
                    st.error("Nie znalazłem adresów. Podaj dokładniejszą ulicę we Wrocławiu.")
            except Exception as e:
                st.error(f"Błąd: {e}")
    else:
        st.warning("Wpisz oba adresy!")
