import streamlit as st
import openrouteservice
from geopy.geocoders import Nominatim
import pandas as pd
import math
import urllib.parse

# 1. Konfiguracja strony
st.set_page_config(page_title="WroTaxi", page_icon="🚕")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; background-color: #3498db; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚕 WroTaxi Compare")

# KLUCZ ORS (Jeśli nadal masz błąd, wygeneruj nowy na openrouteservice.org)
ORS_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijc2N2YwMmI0Y2M2OTRkMjE5MDk5MDU4ZTg3NzMxYjYzIiwiaCI6Im11cm11cjY0In0='

try:
    client = openrouteservice.Client(key=ORS_KEY)
    geolocator = Nominatim(user_agent="wro_taxi_final_v5")
except Exception:
    st.error("Problem z połączeniem z serwerem map. Spróbuj za chwilę.")

start_adr = st.text_input("📍 Skąd?", placeholder="np. Dworzec Główny, Wrocław")
cel_adr = st.text_input("🏁 Dokąd?", placeholder="np. Magnolia Park, Wrocław")

if st.button("SPRAWDŹ CENY"):
    if start_adr and cel_adr:
        with st.spinner("Liczenie trasy..."):
            try:
                # Geo-kodowanie
                l1 = geolocator.geocode(f"{start_adr}, Wrocław" if "Wrocław" not in start_adr else start_adr)
                l2 = geolocator.geocode(f"{cel_adr}, Wrocław" if "Wrocław" not in cel_adr else cel_adr)
                
                if l1 and l2:
                    coords = ((l1.longitude, l1.latitude), (l2.longitude, l2.latitude))
                    route = client.directions(coordinates=coords, profile='driving-car', format='geojson')
                    
                    km = route['features'][0]['properties']['summary']['distance'] / 1000
                    minuty = round(route['features'][0]['properties']['summary']['duration'] / 60)
                    
                    # Obliczenia
                    ryba_base = 20.0 + (math.ceil(km - 4) * 2.5 if km > 4 else 0)
                    q_start = urllib.parse.quote(l1.address)
                    q_cel = urllib.parse.quote(l2.address)

                    dane = [
                        {
                            "Firma": "UberX 🚗", 
                            "Cena": f"~{8.0 + km*2.5:.2f} PLN", 
                            "Link": f"https://m.uber.com/ul/?action=setPickup&pickup[latitude]={l1.latitude}&pickup[longitude]={l1.longitude}&pickup[nickname]={q_start}&dropoff[latitude]={l2.latitude}&dropoff[longitude]={l2.longitude}&dropoff[nickname]={q_cel}", 
                            "Val": 8.0 + km*2.5
                        },
                        {
                            "Firma": "Ryba Taxi 🐟", 
                            "Cena": f"{ryba_base:.2f} PLN", 
                            "Link": "https://rybataxi.itaxi.pl/pax/", 
                            "Val": ryba_base
                        },
                        {
                            "Firma": "Bolt ⚡", 
                            "Cena": f"~{6.5 + km*2.8:.2f} PLN", 
                            "Link": "bolt://ride", 
                            "Val": 6.5 + km*2.8
                        }
                    ]
                    
                    st.success(f"🛣️ {km:.2f} km | ⌛ {minuty} min")
                    
                    for item in sorted(dane, key=lambda x: x['Val']):
                        c1, c2 = st.columns([2, 1])
                        with c1: st.markdown(f"**{item['Firma']}**\n### {item['Cena']}")
                        with c2: st.link_button("ZAMÓW", item['Link'])
                        st.write("---")
                else:
                    st.error("Nie znalazłem adresów. Spróbuj podać dokładniejszą ulicę.")
            except Exception as e:
                st.error("Błąd serwera map (ORS). Prawdopodobnie przekroczono limit zapytań. Spróbuj za 5 minut.")
    else:
        st.warning("Wpisz oba adresy!")
