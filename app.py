import streamlit as st
import openrouteservice
from geopy.geocoders import Nominatim
import math
import urllib.parse

st.set_page_config(page_title="WroTaxi Compare", page_icon="🚕", layout="centered")

# Stylizacja przycisków i pól
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; font-weight: bold; }
    .stTextInput>div>div>input { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚕 WroTaxi Compare")
st.caption("Wrocław: Pełne porównanie Uber, iTaxi, Bolt, FreeNow i Ryba Taxi")

# --- KLUCZ API (Pamiętaj o wklejeniu swojego nowego klucza!) ---
ORS_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijc2N2YwMmI0Y2M2OTRkMjE5MDk5MDU4ZTg3NzMxYjYzIiwiaCI6Im11cm11cjY0In0='

def init_services():
    try:
        client = openrouteservice.Client(key=ORS_KEY)
        geolocator = Nominatim(user_agent="wro_taxi_all_in_one_v1")
        return client, geolocator
    except:
        return None, None

client, geolocator = init_services()

start_adr = st.text_input("📍 Skąd?", placeholder="np. Rynek")
cel_adr = st.text_input("🏁 Dokąd?", placeholder="np. Magnolia Park")

if st.button("SPRAWDŹ CENY"):
    if start_adr and cel_adr:
        with st.spinner("Przeliczam taryfy..."):
            try:
                # 1. Geo-kodowanie
                s_full = f"{start_adr}, Wrocław" if "Wrocław" not in start_adr else start_adr
                c_full = f"{cel_adr}, Wrocław" if "Wrocław" not in cel_adr else cel_adr
                
                l1 = geolocator.geocode(s_full)
                l2 = geolocator.geocode(c_full)
                
                if l1 and l2:
                    # 2. Pobranie trasy
                    coords = ((l1.longitude, l1.latitude), (l2.longitude, l2.latitude))
                    route = client.directions(coordinates=coords, profile='driving-car', format='geojson')
                    
                    km = route['features'][0]['properties']['summary']['distance'] / 1000
                    minuty = round(route['features'][0]['properties']['summary']['duration'] / 60)
                    
                    q_start = urllib.parse.quote(l1.address)
                    q_cel = urllib.parse.quote(l2.address)

                    # --- OBLICZENIA STAWEK ---
                    # Ryba Taxi: baza 20zł (do 4km) + 0.50 PLN korekty, potem 2.5zł/km
                    ryba_raw = 20.0 + (math.ceil(km - 4) * 2.5 if km > 4 else 0)
                    ryba_min = ryba_raw + 0.50  # DODANO 50 GROSZY DO MINIMUM
                    ryba_max = (ryba_raw * 1.2) + 0.50 # DODANO 50 GROSZY DO MAKSIMUM
                    
                    # Dane wszystkich firm
                    dane = [
                        {
                            "Firma": "UberX 🚗", 
                            "Cena": f"~{8.0 + km*2.5:.2f} PLN", 
                            "Link": f"https://m.uber.com/ul/?action=setPickup&pickup[latitude]={l1.latitude}&pickup[longitude]={l1.longitude}&pickup[nickname]={q_start}&dropoff[latitude]={l2.latitude}&dropoff[longitude]={l2.longitude}&dropoff[nickname]={q_cel}", 
                            "Val": 8.0 + km*2.5, "Active": True
                        },
                        {
                            "Firma": "iTaxi 🚕", 
                            "Cena": f"~{7.0 + km*3.0:.2f} PLN", 
                            # Deep Link bezpośrednio do aplikacji iTaxi
                            "Link": f"itaxi://order?address_from_name={q_start}&address_to_name={q_cel}", 
                            "Val": 7.0 + km*3.0, "Active": True
                        },
                        {
                            "Firma": "Ryba Taxi 🐟", 
                            "Cena": f"{ryba_min:.2f} - {ryba_min*1.2:.2f} PLN", 
                            "Link": "", 
                            "Val": ryba_min, "Active": False
                        },
                        {
                            "Firma": "Bolt ⚡", 
                            "Cena": f"~{6.5 + km*2.8:.2f} PLN", 
                            "Link": "bolt://ride", 
                            "Val": 6.5 + km*2.8, "Active": True
                        },
                        {
                            "Firma": "FreeNow 🚕", 
                            "Cena": f"~{9.0 + km*2.3:.2f} PLN", 
                            "Link": "freenow://", 
                            "Val": 9.0 + km*2.3, "Active": True
                        }
                    ]
                    
                    st.success(f"🛣️ {km:.2f} km | ⌛ ok. {minuty} min")
                    st.write("---")
                    
                    # 3. Sortowanie i wyróżnienie najtańszej opcji
                    posortowane = sorted(dane, key=lambda x: x['Val'])
                    najnizsza_cena = posortowane[0]['Val']

                    for item in posortowane:
                        czy_najtaniej = (item['Val'] == najnizsza_cena)
                        with st.container():
                            if czy_najtaniej:
                                st.markdown("✅ **NAJLEPSZA CENA**")
                            
                            col1, col2 = st.columns([2, 1])
                            with col1:
                                kolor = "#27ae60" if czy_najtaniej else "#31333F"
                                st.markdown(f"**{item['Firma']}**")
                                st.markdown(f"<h3 style='color: {kolor}; margin-top: 0;'>{item['Cena']}</h3>", unsafe_allow_html=True)
                            
                            with col2:
                                st.write("") # Odstęp
                                if item['Active']:
                                    st.link_button("ZAMÓW", item['Link'], type="primary" if czy_najtaniej else "secondary")
                                else:
                                    st.button("INFO", disabled=True, key=item['Firma'], help="Ta opcja jest tylko informacyjna")
                            st.write("---")
                else:
                    st.error("Nie znalazłem adresu. Wpisz np. 'Rynek 1' lub 'Legnicka 58'.")
            except Exception as e:
                st.error(f"Błąd klucza lub serwera: {e}")
    else:
        st.warning("Uzupełnij oba pola!")

st.caption("Ceny iTaxi/Ryba są oparte na taryfach miejskich. Uber/Bolt/FreeNow zależą od popytu.")
