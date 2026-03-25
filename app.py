import streamlit as st
import openrouteservice
from geopy.geocoders import Nominatim
import math
from datetime import datetime

# Konfiguracja strony
st.set_page_config(page_title="WroTaxi Compare", page_icon="🚕", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; font-weight: bold; }
    .stTextInput>div>div>input { border-radius: 10px; }
    .tariff-info { 
        background-color: #fdf2e9; 
        padding: 15px; 
        border-radius: 10px; 
        text-align: center; 
        margin-bottom: 20px;
        border: 1px solid #e67e22;
        color: #d35400;
        font-weight: bold;
    }
    .uber-variant {
        font-size: 0.85em;
        color: #111;
        background-color: #ffffff;
        padding: 6px 12px;
        border-radius: 8px;
        margin-top: 5px;
        border: 1px solid #ddd;
        display: flex;
        justify-content: space-between;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.05);
    }
    .discount-tag { color: #27ae60; font-weight: bold; font-size: 0.85em; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚕 WroTaxi Compare")

# --- LOGIKA TARYF ---
now = datetime.now()
hour = (now.hour + 1) % 24 
is_night = (hour >= 22 or hour < 6)
is_weekend = (now.weekday() == 6)

# Taryfa 2 TYLKO dla iTaxi
if is_night or is_weekend:
    t_label = "🌙 TARYFA 2 (Noc/Weekend - tylko iTaxi)"
    itaxi_mnoznik = 1.45
else:
    t_label = "☀️ TARYFA 1 (Dzień)"
    itaxi_mnoznik = 1.0

st.markdown(f"<div class='tariff-info'>{t_label}<br>Aktualna godzina: {hour:02d}:{now.minute:02d}</div>", unsafe_allow_html=True)

# --- KLUCZ API ---
ORS_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijc2N2YwMmI0Y2M2OTRkMjE5MDk5MDU4ZTg3NzMxYjYzIiwiaCI6Im11cm11cjY0In0='

def init_services():
    try:
        client = openrouteservice.Client(key=ORS_KEY)
        geolocator = Nominatim(user_agent="wro_taxi_precision_v47")
        return client, geolocator
    except: return None, None

client, geolocator = init_services()

start_adr = st.text_input("📍 Skąd?", placeholder="np. Wojaczka 10")
cel_adr = st.text_input("🏁 Dokąd?", placeholder="np. Celtycka 1")

# --- SUWAKI ZNIŻEK ---
col_u, col_b = st.columns(2)
with col_u:
    u_promo = st.slider("Zniżka Uber (%)", 0, 90, 0, 5)
with col_b:
    b_promo = st.slider("Zniżka Bolt (%)", 0, 90, 0, 5)

if st.button("PORÓWNAJ CENY"):
    if start_adr and cel_adr:
        with st.spinner("Liczenie trasy..."):
            try:
                l1 = geolocator.geocode(f"{start_adr}, Wrocław")
                l2 = geolocator.geocode(f"{cel_adr}, Wrocław")
                
                if l1 and l2:
                    route = client.directions(coordinates=((l1.longitude, l1.latitude), (l2.longitude, l2.latitude)), profile='driving-car', format='geojson')
                    summary = route['features'][0]['properties']['summary']
                    km, minuty = summary['distance'] / 1000, summary['duration'] / 60
                    
                    u_mult = (100 - u_promo) / 100
                    b_mult = (100 - b_promo) / 100

                    # --- NOWA KALIBRACJA UBERA (ZOPTYMALIZOWANA POD TWOJE DANE) ---
                    # Baza 7.00 + km * 1.85 + minuty * 0.15
                    u_x_base = (7.00 + (km * 1.85) + (minuty * 0.15)) * u_mult
                    
                    # iTaxi (z mnożnikiem nocnym)
                    itaxi_v = 9.0 + (km * 4.30 * itaxi_mnoznik)
                    
                    # Ryba Taxi (BEZ mnożnika nocnego)
                    ryba_min = 20.50 + (math.ceil(km - 4) * 2.50 if km > 4 else 0)
                    ryba_max = (ryba_min * 1.15) + 2.00 
                    
                    # Bolt (lekka korekta bazy)
                    bolt_v = (6.0 + km * 2.5) * b_mult
                    
                    dane = [
                        {
                            "Firma": "Uber 🚗", 
                            "Promo": f"-{u_promo}%" if u_promo > 0 else "",
                            "Cena": f"od {u_x_base * 0.86:.2f} PLN", 
                            "Val": u_x_base * 0.86, "Type": "link",
                            "Link": f"https://m.uber.com/ul/?action=setPickup&pickup[latitude]={l1.latitude}&pickup[longitude]={l1.longitude}&dropoff[latitude]={l2.latitude}&dropoff[longitude]={l2.longitude}",
                            "Variants": [
                                {"name": "📉 Czekaj i oszczędzaj", "price": u_x_base * 0.86},
                                {"name": "🚗 UberX", "price": u_x_base},
                                {"name": "🔋 Hybrid", "price": u_x_base * 1.01},
                                {"name": "✨ Comfort", "price": u_x_base * 1.18}
                            ]
                        },
                        {
                            "Firma": "iTaxi 🚕", "Cena": f"~{itaxi_v:.2f} PLN", "Promo": "",
                            "Val": itaxi_v, "Type": "call", "Link": "tel:737737737"
                        },
                        {
                            "Firma": "Ryba Taxi 🐟", 
                            "Cena": f"{ryba_min:.2f} - {ryba_max:.2f} PLN", "Promo": "",
                            "Val": ryba_min, "Type": "call", "Link": "tel:713441515"
                        },
                        {
                            "Firma": "Bolt ⚡", 
                            "Promo": f"-{b_promo}%" if b_promo > 0 else "",
                            "Cena": f"~{bolt_v:.2f} PLN", 
                            "Val": bolt_v, "Type": "link", "Link": "bolt://ride"
                        }
                    ]
                    
                    st.success(f"🛣️ {km:.2f} km | ⏱️ {int(minuty)} min")
                    for item in sorted(dane, key=lambda x: x['Val']):
                        with st.container():
                            c1, c2 = st.columns([2, 1])
                            with c1:
                                p_tag = f" <span class='discount-tag'>{item['Promo']}</span>" if item['Promo'] else ""
                                st.markdown(f"**{item['Firma']}**{p_tag}", unsafe_allow_html=True)
                                st.markdown(f"### {item['Cena']}")
                                if "Variants" in item:
                                    for v in item['Variants']:
                                        st.markdown(f"<div class='uber-variant'><span>{v['name']}</span><b>{v['price']:.2f} PLN</b></div>", unsafe_allow_html=True)
                            with c2:
                                st.write("")
                                st.link_button("ZAMÓW" if item['Type']=="link" else "ZADZWOŃ", item['Link'])
                            st.write("---")
            except Exception as e: st.error(f"Błąd: {e}")
