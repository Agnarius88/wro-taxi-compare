import streamlit as st
import openrouteservice
from geopy.geocoders import Nominatim
import math
import urllib.parse

st.set_page_config(page_title="WroTaxi Compare", page_icon="🚕", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; font-weight: bold; }
    .stTextInput>div>div>input { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚕 WroTaxi Compare")
st.caption("Wrocław: Ryba (Standard) | iTaxi (Korekta korkowa) | Reszta (Dynamiczne)")

ORS_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijc2N2YwMmI0Y2M2OTRkMjE5MDk5MDU4ZTg3NzMxYjYzIiwiaCI6Im11cm11cjY0In0='

def init_services():
    try:
        client = openrouteservice.Client(key=ORS_KEY)
        geolocator = Nominatim(user_agent="wro_taxi_final_v20")
        return client, geolocator
    except: return None, None

client, geolocator = init_services()

start_adr = st.text_input("📍 Skąd?", placeholder="np. Wojaczka 10")
cel_adr = st.text_input("🏁 Dokąd?", placeholder="np. Celtycka 1")

if st.button("SPRAWDŹ CENY"):
    if start_adr and cel_adr:
        with st.spinner("Synchronizacja taryf..."):
            try:
                s_full = f"{start_adr}, Wrocław"; c_full = f"{cel_adr}, Wrocław"
                l1 = geolocator.geocode(s_full); l2 = geolocator.geocode(c_full)
                
                if l1 and l2:
                    coords = ((l1.longitude, l1.latitude), (l2.longitude, l2.latitude))
                    route = client.directions(coordinates=coords, profile='driving-car', format='geojson')
                    km = route['features'][0]['properties']['summary']['distance'] / 1000
                    
                    q_start = urllib.parse.quote(l1.address.split(',')[0])
                    q_cel = urllib.parse.quote(l2.address.split(',')[0])

                   # --- PRECYZYJNY TUNING TARYF ---
                    # Dystans z mapy (zostawiamy, bo dla Ryby jest IDEALNY)
                    km = raw_km 

                    # 1. iTaxi: 9zł start + (km * 4.30) 
                    # Taki przelicznik przy 10km daje ~52.00 PLN. 
                    # To uwzględnia realny koszt przejazdu iTaxi we Wrocławiu z korkami.
                    itaxi_val = 9.0 + (km * 4.30)
                    
                    # 2. Ryba Taxi: (ZOSTAJE BEZ ZMIAN - Twój ideał)
                    ryba_val = 20.50 + (math.ceil(km - 4) * 2.50 if km > 4 else 0)

                    dane = [
                        {"Firma": "UberX 🚗", "Cena": f"~{8.0 + km*2.5:.2f} PLN", "Link": f"https://m.uber.com/ul/?action=setPickup&pickup[latitude]={l1.latitude}&pickup[longitude]={l1.longitude}&pickup[nickname]={q_start}&dropoff[latitude]={l2.latitude}&dropoff[longitude]={l2.longitude}&dropoff[nickname]={q_cel}", "Val": 8.0 + km*2.5, "Active": True},
                        {"Firma": "iTaxi 🚕", "Cena": f"~{itaxi_val:.2f} PLN", "Link": "", "Val": itaxi_val, "Active": False},
                        {"Firma": "Ryba Taxi 🐟", "Cena": f"{ryba_val:.2f} - {ryba_val*1.15:.2f} PLN", "Link": "", "Val": ryba_val, "Active": False},
                        {"Firma": "Bolt ⚡", "Cena": f"~{6.5 + km*2.8:.2f} PLN", "Link": "bolt://ride", "Val": 6.5 + km*2.8, "Active": True},
                        {"Firma": "FreeNow 🚕", "Cena": f"~{9.0 + km*2.3:.2f} PLN", "Link": "freenow://", "Val": 9.0 + km*2.3, "Active": True}
                    ]
                    
                    st.success(f"🛣️ Dystans trasy: {km:.2f} km")
                    st.write("---")
                    
                    posortowane = sorted(dane, key=lambda x: x['Val'])
                    min_val = posortowane[0]['Val']

                    for item in posortowane:
                        najtaniej = (item['Val'] == min_val)
                        with st.container():
                            if najtaniej: st.markdown("✅ **NAJLEPSZA CENA**")
                            c1, c2 = st.columns([2, 1])
                            with c1:
                                kolor = "#27ae60" if najtaniej else "#31333F"
                                st.markdown(f"**{item['Firma']}**")
                                st.markdown(f"<h3 style='color: {kolor}; margin-top: 0;'>{item['Cena']}</h3>", unsafe_allow_html=True)
                            with c2:
                                st.write("")
                                if item['Active']:
                                    st.link_button("ZAMÓW", item['Link'], type="primary" if najtaniej else "secondary")
                                else:
                                    st.button("INFO", disabled=True, key=item['Firma'])
                            st.write("---")
                else: st.error("Nie znaleziono adresu.")
            except Exception as e: st.error(f"Błąd: {e}")

st.caption("iTaxi uwzględnia przewidywany czas postoju w korkach. Ryba Taxi oparta na czystym dystansie.")
