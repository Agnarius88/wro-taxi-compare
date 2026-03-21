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
    .sub-link { font-size: 0.8em; text-align: center; display: block; margin-top: -10px; color: #7f8c8d; text-decoration: none; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚕 WroTaxi Compare")
st.caption("Wrocław: Kalibracja iTaxi (~52zł) | Ryba (Idealna) | Fix Link FreeNow")

# --- KLUCZ API ---
ORS_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijc2N2YwMmI0Y2M2OTRkMjE5MDk5MDU4ZTg3NzMxYjYzIiwiaCI6Im11cm11cjY0In0='

def init_services():
    try:
        client = openrouteservice.Client(key=ORS_KEY)
        geolocator = Nominatim(user_agent="wro_taxi_final_v23")
        return client, geolocator
    except: return None, None

client, geolocator = init_services()

start_adr = st.text_input("📍 Skąd?", placeholder="np. Wojaczka 10")
cel_adr = st.text_input("🏁 Dokąd?", placeholder="np. Celtycka 1")

if st.button("SPRAWDŹ CENY"):
    if start_adr and cel_adr:
        with st.spinner("Łączenie z korporacjami..."):
            try:
                s_full = f"{start_adr}, Wrocław"; c_full = f"{cel_adr}, Wrocław"
                l1 = geolocator.geocode(s_full); l2 = geolocator.geocode(c_full)
                
                if l1 and l2:
                    coords = ((l1.longitude, l1.latitude), (l2.longitude, l2.latitude))
                    route = client.directions(coordinates=coords, profile='driving-car', format='geojson')
                    km = route['features'][0]['properties']['summary']['distance'] / 1000
                    
                    q_start = urllib.parse.quote(l1.address.split(',')[0])
                    q_cel = urllib.parse.quote(l2.address.split(',')[0])

                    # --- TWOJE IDEALNE TARYFY ---
                    itaxi_val = 9.0 + (km * 4.30)
                    ryba_min = 20.50 + (math.ceil(km - 4) * 2.50 if km > 4 else 0)
                    ryba_max = (ryba_min * 1.15) + 2.00

                    dane = [
                        {
                            "Firma": "UberX 🚗", 
                            "Cena": f"~{8.0 + km*2.5:.2f} PLN", 
                            "Link": f"https://m.uber.com/ul/?action=setPickup&pickup[latitude]={l1.latitude}&pickup[longitude]={l1.longitude}&pickup[nickname]={q_start}&dropoff[latitude]={l2.latitude}&dropoff[longitude]={l2.longitude}&dropoff[nickname]={q_cel}", 
                            "Val": 8.0 + km*2.5, "Active": True
                        },
                        {
                            "Firma": "iTaxi 🚕", 
                            "Cena": f"~{itaxi_val:.2f} PLN", 
                            "Link": "", "Val": itaxi_val, "Active": False
                        },
                        {
                            "Firma": "Ryba Taxi 🐟", 
                            "Cena": f"{ryba_min:.2f} - {ryba_max:.2f} PLN", 
                            "Link": "", "Val": ryba_min, "Active": False
                        },
                        {
                            "Firma": "Bolt ⚡", 
                            "Cena": f"~{6.5 + km*2.8:.2f} PLN", 
                            "Link": "bolt://ride", 
                            "Val": 6.5 + km*2.8, "Active": True
                        },
                        {
                            "Firma": "FreeNow 🚕", 
                            "Cena": f"~{5.0 + km*2.8:.2f} PLN", 
                            # Próba bezpośredniego wywołania aplikacji (Deep Link)
                            "Link": f"freenow://short-order?pickupLat={l1.latitude}&pickupLng={l1.longitude}&destinationLat={l2.latitude}&destinationLng={l2.longitude}", 
                            "Val": 5.0 + km*2.8, 
                            "Active": True,
                            "Fallback": f"https://www.free-now.com/pl/zamow-taksowke/?pickupLat={l1.latitude}&pickupLng={l1.longitude}&dropOffLat={l2.latitude}&dropOffLng={l2.longitude}"
                        }
                    ]
                    
                    st.success(f"🛣️ Dystans: {km:.2f} km")
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
                                    if "Fallback" in item:
                                        st.markdown(f'<a href="{item["Fallback"]}" target="_blank" class="sub-link">Nie działa? Kliknij tutaj</a>', unsafe_allow_html=True)
                                else:
                                    st.button("INFO", disabled=True, key=item['Firma'])
                            st.write("---")
                else: st.error("Nie znaleziono lokalizacji.")
            except Exception as e: st.error(f"Błąd: {e}")
