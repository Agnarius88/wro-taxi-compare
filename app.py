import streamlit as st
import openrouteservice
from geopy.geocoders import Nominatim
import pandas as pd
import math
import urllib.parse

# 1. Konfiguracja strony pod telefon
st.set_page_config(page_title="WroTaxi Compare", page_icon="🚕")

# Stylizacja przycisków (żeby były duże i wygodne na smartfonie)
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; background-color: #3498db; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚕 WroTaxi Compare")
st.caption("Wrocław: Porównywarka Uber, Bolt, FreeNow i Ryba Taxi")

# --- KONFIGURACJA KLUCZY ---
# Twój klucz ORS (zostawiamy ten, który działa)
ORS_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijc2N2YwMmI0Y2M2OTRkMjE5MDk5MDU4ZTg3NzMxYjYzIiwiaCI6Im11cm11cjY0In0='
client = openrouteservice.Client(key=ORS_KEY)
geolocator = Nominatim(user_agent="wro_taxi_final_v3")

# --- POLA WPISYWANIA ---
start_adr = st.text_input("📍 Skąd (Lokalizacja)?", placeholder="np. Dworzec Główny, Wrocław")
cel_adr = st.text_input("🏁 Dokąd jedziemy?", placeholder="np. Magnolia Park, Wrocław")

if st.button("SPRAWDŹ CENY I ZAMÓW"):
    if start_adr and cel_adr:
        with st.spinner("Szukam najlepszej trasy we Wrocławiu..."):
            try:
                # Geolokalizacja (zamiana tekstu na współrzędne)
                l1 = geolocator.geocode(start_adr if "Wrocław" in start_adr else f"{start_adr}, Wrocław")
                l2 = geolocator.geocode(cel_adr if "Wrocław" in cel_adr else f"{cel_adr}, Wrocław")
                
                if not l1 or not l2:
                    st.error("Nie znalazłem jednego z adresów. Spróbuj dopisać nazwę ulicy.")
                else:
                    # Pobranie trasy z OpenRouteService
                    coords = ((l1.longitude, l1.latitude), (l2.longitude, l2.latitude))
                    route = client.directions(coordinates=coords, profile='driving-car', format='geojson')
                    
                    km = route['features'][0]['properties']['summary']['distance'] / 1000
                    minuty = round(route['features'][0]['properties']['summary']['duration'] / 60)
                    
                    # --- OBLICZENIA CEN ---
                    
                    # 1. Ryba Taxi (Cennik wrocławski)
                    ryba_base = 20.0 + (math.ceil(km - 4) * 2.5 if km > 4 else 0)
                    
                    # 2. Przygotowanie danych do Ubera (dokładna pinezka GPS)
                    lat_cel = l2.latitude
                    lon_cel = l2.longitude
                    q_nick = urllib.parse.quote(cel_adr)

                    # --- LISTA WYNIKÓW ---
                    dane = [
                        {
                            "Firma": "Ryba Taxi 🐟", 
                            "Cena": f"{ryba_base:.2f} - {ryba_base*1.2:.2f} PLN", 
                            "Link": "https://pasażer.ryba-taxi.pl/", 
                            "Val": ryba_base
                        },
                        {
                            "Firma": "UberX 🚗", 
                            "Cena": f"~{8.0 + km*2.5:.2f} PLN", 
                            "Link": f"https://m.uber.com/ul/?action=setPickup&pickup=my_location&dropoff[latitude]={lat_cel}&dropoff[longitude]={lon_cel}&dropoff[nickname]={q_nick}", 
                            "Val": 8.0 + km*2.5
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
                    
                    st.success(f"🛣️ Dystans: {km:.2f} km | ⌛ Czas: ok. {minuty} min")
                    st.write("---")
                    
                    # Sortowanie po cenie (od najtańszej)
                    for item in sorted(dane, key=lambda x: x['Val']):
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.markdown(f"**{item['Firma']}**")
                            st.markdown(f"### {item['Cena']}")
                        with col2:
                            st.link_button("ZAMÓW", item['Link'])
                        st.write("---")
                        
            except Exception as e:
                st.error(f"Wystąpił błąd: {e}")
    else:
        st.warning("Uzupełnij oba pola tekstowe!")

st.caption("Uwaga: Ceny aplikacji (Uber/Bolt/FreeNow) są szacunkowe i zależą od popytu.")
