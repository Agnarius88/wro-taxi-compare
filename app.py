import streamlit as st
import openrouteservice
from geopy.geocoders import Nominatim
import math
import urllib.parse

# 1. Konfiguracja
st.set_page_config(page_title="WroTaxi", page_icon="🚕")

# KLUCZ ORS - WYMIEŃ GO NA SWÓJ NOWY!
ORS_KEY = '5b3ce3597851100001cf6248383f98c603b544d6935272a912a2335f'

st.title("🚕 WroTaxi Compare")

# Inicjalizacja narzędzi
geolocator = Nominatim(user_agent="wro_taxi_final_v10")
client = openrouteservice.Client(key=ORS_KEY)

start_adr = st.text_input("📍 Skąd?", placeholder="np. Rynek")
cel_adr = st.text_input("🏁 Dokąd?", placeholder="np. Magnolia")

if st.button("LICZ CENY"):
    if start_adr and cel_adr:
        try:
            # Dodajemy "Wrocław" automatycznie dla pewności
            s_full = f"{start_adr}, Wrocław" if "Wrocław" not in start_adr else start_adr
            c_full = f"{cel_adr}, Wrocław" if "Wrocław" not in cel_adr else cel_adr
            
            l1 = geolocator.geocode(s_full)
            l2 = geolocator.geocode(c_full)
            
            if l1 and l2:
                # Trasa i dystans
                coords = ((l1.longitude, l1.latitude), (l2.longitude, l2.latitude))
                route = client.directions(coordinates=coords, profile='driving-car', format='geojson')
                
                km = route['features'][0]['properties']['summary']['distance'] / 1000
                q_start = urllib.parse.quote(l1.address)
                q_cel = urllib.parse.quote(l2.address)

                # Firmy (iTaxi zamiast Ryby)
                dane = [
                    {
                        "Firma": "UberX 🚗", 
                        "Cena": f"~{8.0 + km*2.5:.2f} PLN", 
                        "Link": f"https://m.uber.com/ul/?action=setPickup&pickup[latitude]={l1.latitude}&pickup[longitude]={l1.longitude}&pickup[nickname]={q_start}&dropoff[latitude]={l2.latitude}&dropoff[longitude]={l2.longitude}&dropoff[nickname]={q_cel}", 
                        "Val": 8.0 + km*2.5
                    },
                    {
                        "Firma": "iTaxi 🚕", 
                        "Cena": f"~{7.0 + km*3.0:.2f} PLN", 
                        "Link": f"https://itaxi.pl/zamow-przejazd/?address_from={q_start}&address_to={q_cel}", 
                        "Val": 7.0 + km*3.0
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
                
                st.info(f"Dystans: {km:.2f} km")
                
                for item in sorted(dane, key=lambda x: x['Val']):
                    col1, col2 = st.columns([2, 1])
                    with col1: st.write(f"**{item['Firma']}**: {item['Cena']}")
                    with col2: st.link_button("ZAMÓW", item['Link'])
            else:
                st.error("Nie znalazłem adresu. Wpisz np. 'Legnicka 58'")
        
        except Exception as e:
            if "403" in str(e) or "429" in str(e):
                st.error("Limit klucza API wyczerpany! Musisz wkleić nowy klucz ORS w kodzie.")
            else:
                st.error(f"Błąd: {e}")
