import streamlit as st
import openrouteservice
from geopy.geocoders import Nominatim
import pandas as pd
import math
import urllib.parse

# 1. Ustawienia wyglądu pod telefon
st.set_page_config(page_title="WroTaxi Compare", page_icon="🚕", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; background-color: #3498db; color: white; font-weight: bold; }
    .price-box { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #3498db; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚕 WroTaxi Compare")
st.caption("Najszybsze porównanie cen we Wrocławiu")

# --- KLUCZ I KONFIGURACJA ---
ORS_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijc2N2YwMmI0Y2M2OTRkMjE5MDk5MDU4ZTg3NzMxYjYzIiwiaCI6Im11cm11cjY0In0='

def get_data():
    try:
        client = openrouteservice.Client(key=ORS_KEY)
        geolocator = Nominatim(user_agent="wro_taxi_ultimate_v7")
        return client, geolocator
    except:
        return None, None

client, geolocator = get_data()

# --- POLA WPISYWANIA ---
start_adr = st.text_input("📍 Skąd (Lokalizacja)?", placeholder="np. Rynek, Wrocław")
cel_adr = st.text_input("🏁 Dokąd jedziemy?", placeholder="np. Magnolia Park, Wrocław")

if st.button("SPRAWDŹ CENY I TRASĘ"):
    if start_adr and cel_adr:
        with st.spinner("Szukam taksówek we Wrocławiu..."):
            try:
                # 1. Geolokalizacja
                s_query = f"{start_adr}, Wrocław" if "Wrocław" not in start_adr else start_adr
                c_query = f"{cel_adr}, Wrocław" if "Wrocław" not in cel_adr else cel_adr
                
                l1 = geolocator.geocode(s_query)
                l2 = geolocator.geocode(c_query)
                
                if l1 and l2:
                    # 2. Pobranie trasy
                    coords = ((l1.longitude, l1.latitude), (l2.longitude, l2.latitude))
                    route = client.directions(coordinates=coords, profile='driving-car', format='geojson')
                    
                    km = route['features'][0]['properties']['summary']['distance'] / 1000
                    minuty = round(route['features'][0]['properties']['summary']['duration'] / 60)
                    
                    # 3. Obliczenia stawek
                    ryba_min = 20.0 + (math.ceil(km - 4) * 2.5 if km > 4 else 0)
                    ryba_max = ryba_min * 1.2
                    
                    q_start = urllib.parse.quote(l1.address)
                    q_cel = urllib.parse.quote(l2.address)

                    # 4. Przygotowanie listy firm
                    dane = [
                        {
                            "Firma": "UberX 🚗", 
                            "Cena": f"~{8.0 + km*2.5:.2f} PLN", 
                            "Link": f"https://m.uber.com/ul/?action=setPickup&pickup[latitude]={l1.latitude}&pickup[longitude]={l1.longitude}&pickup[nickname]={q_start_name}&dropoff[latitude]={l2.latitude}&dropoff[longitude]={l2.longitude}&dropoff[nickname]={q_cel_name}", 
                            "Val": 8.0 + km*2.5
                        },
                        {
                            "Firma": "iTaxi 🚕", 
                            "Cena": f"~{7.0 + km*3.0:.2f} PLN", # iTaxi ma zazwyczaj taryfę ok. 3zł/km
                            "Link": f"https://itaxi.pl/zamow-przejazd/?address_from={q_start_name}&address_to={q_cel_name}", 
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
                    
                    st.success(f"🛣️ Dystans: {km:.2f} km | ⌛ Czas: ok. {minuty} min")
                    st.write("---")
                    
                    # 5. Wyświetlanie wyników (Sortowanie od najtańszej)
                    for item in sorted(dane, key=lambda x: x['Val']):
                        with st.container():
                            col1, col2 = st.columns([2, 1])
                            with col1:
                                st.markdown(f"**{item['Firma']}**")
                                st.markdown(f"### {item['Cena']}")
                                if "Note" in item:
                                    st.caption(item["Note"])
                            with col2:
                                st.link_button("ZAMÓW", item['Link'])
                            st.write("---")
                else:
                    st.error("Nie znalazłem adresu. Spróbuj wpisać nazwę ulicy i numer.")
            except Exception as e:
                st.error("Przekroczono limit zapytań mapy lub błąd serwera. Spróbuj za chwilę.")
    else:
        st.warning("Uzupełnij oba pola!")

st.caption("Ceny są szacunkowe i mogą się różnić w zależności od korków i popytu.")
