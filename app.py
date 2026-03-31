import streamlit as st
import openrouteservice
from geopy.geocoders import Nominatim
import math
from datetime import datetime
import random
import pytz
import json
from google.cloud import firestore
from google.oauth2 import service_account
import os

# Łączymy się z bazą używając "Secrets"
if "db" not in st.session_state:
    try:
        key_dict = json.loads(json.dumps(st.secrets["textkey"]))
        creds = service_account.Credentials.from_service_account_info(key_dict)
        st.session_state.db = firestore.Client(credentials=creds, project="taxi-compare-pro")
    except Exception as e:
        st.error(f"Błąd połączenia z bazą: {e}")

def load_data():
    try:
        doc_ref = st.session_state.db.collection("taxi_data").document("memory")
        doc = doc_ref.get()
        return doc.to_dict() if doc.exists else {}
    except:
        return {}

def save_data(data):
    try:
        doc_ref = st.session_state.db.collection("taxi_data").document("memory")
        doc_ref.set(data)
        return True
    except Exception as e:
        st.error(f"Błąd zapisu do chmury: {e}")
        return False

# --- LOAD AI MEMORY FROM FILE ---
if 'ai_data' not in st.session_state:
    st.session_state.ai_data = load_data() # Korzysta z nowej funkcji

# --- AI LEARNING MEMORY ---
if "correction_uber" not in st.session_state:
    st.session_state.correction_uber = 1.0

if "correction_bolt" not in st.session_state:
    st.session_state.correction_bolt = 1.0

if "correction_freenow" not in st.session_state:
    st.session_state.correction_freenow = 1.0

def simulate_smart_market(is_peak, is_night):
    if is_peak:
        surge = 1.35
        status = "🔴 BARDZO WYSOKI POPYT (Szczyt)"
    elif is_night:
        surge = 1.10
        status = "🌙 NOCNY SPOKÓJ"
    else:
        surge = 1.00 # Stały mnożnik 1.0 dla weekendu i zwykłego dnia
        status = "🟢 DUŻA DOSTĘPNOŚĆ"
    
    # Zwracamy stałe wartości zamiast random
    return surge, 20, 10, status

# --- KONFIGURACJA STREAMLIT ---
st.set_page_config(page_title="WroTaxi Compare Pro", page_icon="🚕", layout="centered")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; font-weight: bold; background-color: #2e3136; color: white; }
    .tariff-info { 
        background-color: #f0f2f6; padding: 15px; border-radius: 10px; 
        text-align: center; margin-bottom: 20px; border-left: 5px solid #e67e22;
        font-weight: bold; color: #1f2937;
    }
    .variant-card {
        font-size: 0.85em; color: #111; background-color: #f9f9f9;
        padding: 6px 12px; border-radius: 8px; margin-top: 4px;
        border: 1px solid #eee; display: flex; justify-content: space-between;
    }
    .discount-tag { color: #27ae60; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚕 WroTaxi Compare v5.5")

# --- LOGIKA CZASOWA (Automatyczna dla Polski) ---
tz_PL = pytz.timezone('Europe/Warsaw') 
now = datetime.now(tz_PL) # Pobiera aktualny czas w Polsce, uwzględniając zmianę czasu
h = now.hour
time_val = h + now.minute/60
day = now.weekday() 
is_weekend = (day >= 5)
is_night = (time_val >= 22 or time_val < 6)
is_peak = not is_weekend and ((7.5 <= time_val <= 9.5) or (15.5 <= time_val <= 18.5))

context_key = f"{int(time_val)}_{'weekend' if is_weekend else 'weekday'}"
if context_key not in st.session_state.ai_data:
    st.session_state.ai_data[context_key] = {
        "uber": 1.0,
        "bolt": 1.0,
        "freenow": 1.0
    }

# Wywołujemy nową funkcję, aby zainicjować zmienne dla interfejsu
surge, drivers, requests, market_status = simulate_smart_market(is_peak, is_night)

# --- CENY W ZALEŻNOŚCI OD PORY DNIA ---
if is_night:
    t_status = "🌙 NOC"
    u_base, u_km = 7.00, 1.85 
    b_base, b_km = 4.50, 2.30
    fn_fix = 2.00
    time_rate = 0.15
elif is_weekend:  # <--- NOWY BLOK TYLKO DLA WEEKENDU (w ciągu dnia)
    t_status = "🎉 WEEKEND (Dzień)"
    u_base, u_km = 6.60, 2.20  
    b_base, b_km = 3.00, 2.70
    fn_fix = 8.00
    time_rate = 0.20
elif (10.25 <= time_val < 10.67):
    t_status = "📉 SPOKÓJ PRZEDPOŁUDNIOWY"
    u_base, u_km = 5.00, 1.70  
    b_base, b_km = 3.50, 1.90
    fn_fix = 2.00
    time_rate = 0.15
elif (11.0 <= time_val < 11.5):
    t_status = "📉 PRZEDPOŁUDNIOWY DOŁEK"
    u_base, u_km = 7.50, 1.90    # To Twoje "standardowe" ceny, które były o 10:00
    b_base, b_km = 4.80, 2.30
    fn_fix = 2.00
    time_rate = 0.15    
elif (11.5 <= time_val < 12.25):
    t_status = "⚖️ STABILIZACJA PRZEDPOŁUDNIOWA (11:30-12:15)"
    u_base, u_km = 7.00, 2.00  
    b_base, b_km = 6.50, 2.35
    fn_fix = 2.00
    time_rate = 0.25            # Normalna stawka czasowa
elif (13.5 <= time_val <= 14.5):
    t_status = "📉 PRZEDSZCZYTOWA PROMOCJA BOLT"
    u_base, u_km = 9.00, 2.35
    b_base, b_km = 2.80, 2.70 
    fn_fix = 2.00
    time_rate = 0.15
elif (15.67 <= time_val < 16.0):
    u_base, u_km = 4.5, 2.25 
    b_base, b_km = 5.00, 2.70
    fn_fix = -10  
    time_rate = 0.45  
#elif (13.0 <= time_val < 14.0): <--- To jest szablon do korekty cen w zależności od godziny
   #t_status = "🕒 POŁUDNIOWY SKOK CEN"
    #u_base = 9.00  # było 8.00, więc dodajemy 1 zł
    #b_base = 6.00  # było 5.00, więc dodajemy 1 zł
    #u_km = 2.10    # stawka za km zostaje standardowa
    #b_km = 2.70  
elif is_peak: #  peak jest ustawiony 7:30 - 9:30 i 15:30 - 18:30
    # Szczyt (Twoje 15:22 - korki + wysoki popyt)
    u_base, u_km = 10.5, 2.25 
    b_base, b_km = 5.00, 2.70
    fn_fix = 3.50  
    time_rate = 0.45         # Minuta droższa, bo stoisz na światłach
else:
    t_status = "☀️ STANDARDOWY DZIEŃ (np. 10:00)"
    u_base, u_km = 8.00, 2.10
    b_base, b_km = 3.00, 2.70
    fn_fix = 2.50
    time_rate = 0.20

st.markdown(f"<div class='tariff-info'>Aktualna godzina: {h:02d}:{now.minute:02d}</div>", unsafe_allow_html=True)

# --- USŁUGI ---
ORS_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijc2N2YwMmI0Y2M2OTRkMjE5MDk5MDU4ZTg3NzMxYjYzIiwiaCI6Im11cm11cjY0In0='

def get_data():
    try:
        return openrouteservice.Client(key=ORS_KEY), Nominatim(user_agent="wrotaxi_v55_precision")
    except:
        return None, None

client, geolocator = get_data()

start_adr = st.text_input("📍 Skąd?", placeholder="np. Wojaczka 10")
cel_adr = st.text_input("🏁 Dokąd?", placeholder="np. Rynek")

col1, col2, col3 = st.columns(3)
with col1:
    u_promo = st.slider("Zniżka Uber %", 0, 90, 0, 5)
with col2:
    b_promo = st.slider("Zniżka Bolt %", 0, 90, 0, 5)
with col3:
    f_promo = st.slider("Zniżka FreeNow %", 0, 90, 0, 5)    

if st.button("SPRAWDŹ CENY"):
    st.session_state.show_results = True  # Aktywujemy pamięć kliknięcia

if st.session_state.show_results:  # <--- To sprawi, że formularz nie zniknie!
    if not start_adr or not cel_adr:
        st.warning("⚠️ Podaj adres początkowy i końcowy")
        st.session_state.show_results = False # Resetujemy, jak user zapomniał wpisać adresów
    else:
        surge, drivers, requests, market_status = simulate_smart_market(is_peak, is_night)
        
        if start_adr and cel_adr:
            with st.spinner("Przeliczanie..."):
                try:
                    l1 = geolocator.geocode(f"{start_adr}, Poland")
                    l2 = geolocator.geocode(f"{cel_adr}, Poland")
                        
                    if l1 and l2:
                        #if is_center(l1.latitude, l1.longitude) or is_center(l2.latitude, l2.longitude):
                            #surge *= 1.15
                    
                        # --- GŁÓWNA FUNKCJA MAPOWA Z TRY-EXCEPT ---
                        try:
                            res = client.directions(
                                coordinates=((l1.longitude, l1.latitude), (l2.longitude, l2.latitude)),
                                profile='driving-car',
                                format='geojson',
                                radiuses=[3000, 3000]
                            )
                            
                            if 'features' in res and len(res['features']) > 0:
                                km = res['features'][0]['properties']['summary']['distance'] / 1000
                                dur = res['features'][0]['properties']['summary']['duration'] / 60
                        
                                u_mult = (100 - u_promo) / 100
                                b_mult = (100 - b_promo) / 100
                                f_mult = (100 - f_promo) / 100
                                        
                                # Obliczamy "gołą" bazę
                                uber_raw = u_base + (km * u_km) + (dur * time_rate)
                                bolt_raw = b_base + (km * b_km) + 3.70
                                freenow_raw = uber_raw + fn_fix
                                
                                # Nakładamy surge z symulacji rynku
                                ctx = st.session_state.ai_data[context_key]

                                uber_x = uber_raw * surge * ctx["uber"]
                                bolt_std = bolt_raw * surge * ctx["bolt"]
                                freenow_lite = freenow_raw * surge * ctx["freenow"]
                                
                                # --- CHAOS ALGORYTMU ---
                                noise = 1
                                uber_x *= noise
                                bolt_std *= noise
                                freenow_lite *= noise
                                
                                # --- NAKŁADAMY ZNIŻKI UŻYTKOWNIKA ---
                                uber_x *= u_mult
                                bolt_std *= b_mult
                                freenow_lite *= f_mult
                                
                                # --- MINIMALNE CENY ---
                                uber_x = max(uber_x, 12)
                                bolt_std = max(bolt_std, 11)
                                freenow_lite = max(freenow_lite, 12)

                                # Zapisujemy aktualne ceny do session_state
                                st.session_state.uber_x = uber_x
                                st.session_state.bolt_std = bolt_std
                                st.session_state.freenow_lite = freenow_lite
                                
                                # --- LOKALNA TAXI ---
                                ryba_min = 20.50 + (math.ceil(km - 4) * 2.50 if km > 4 else 0)
                                ryba_max = (ryba_min * 1.15) + 2.00
        
                                dane = [
                                    {"Firma": "Uber 🚗", "Btn": "WYBIERZ", "Val": uber_x*0.86, "Promo": u_promo,
                                     "Main": f"~ {uber_x*0.86:.2f} PLN",
                                     "Link": f"https://m.uber.com/ul/?action=setPickup&pickup[latitude]={l1.latitude}&pickup[longitude]={l1.longitude}&dropoff[latitude]={l2.latitude}&dropoff[longitude]={l2.longitude}",
                                     "Vars": [("📉 Czekaj i oszczędzaj", uber_x*0.85), 
                                              ("🚗 UberX", uber_x),
                                              ("🔋 Hybrid", uber_x),                                              
                                              ("🐾 Uber Pets", uber_x+4)]},
                                    {"Firma": "Bolt ⚡", "Btn": "WYBIERZ", "Val": bolt_std * 0.956, "Promo": b_promo,
                                     "Main": f"~ {bolt_std * 0.956:.2f} PLN", "Link": "bolt://ride",
                                     "Vars": [("⚡ Bolt", bolt_std), 
                                              ("🔋 Hybrid", bolt_std),
                                              ("🐾 Pet", bolt_std+4), # Dodałem wariant Pet, względem zwykłego Bolta, Pet był droższy ok 4 zł
                                              ("📉 Wait and Save", bolt_std * 0.77 if (is_peak or 15.67 <= time_val < 16.0) else bolt_std * 0.956)]},
                                    {"Firma": "FREENOW 🔴", "Btn": "ZAMÓW W APCE", "Val": freenow_lite, "Promo": f_promo,
                                     "Main": f"~ {freenow_lite:.2f} PLN",
                                     "Link": "intent://#Intent;scheme=freenow;package=taxi.android.client;end",
                                     "Vars": [("🚗 Lite / Green", freenow_lite), 
                                              ("🐾 Pets", freenow_lite*1.3), 
                                              ("🚐 Taxi XL", freenow_lite*1.6)]},
                                    {"Firma": "Ryba Taxi 🐟", "Btn": "ZADZWOŃ", "Val": ryba_min, "Promo": 0,
                                     "Main": f"{ryba_min:.2f} - {ryba_max:.2f} PLN", "Link": "tel:713441515", "Vars": []}
                                ]

                                st.success(f"🛣️ {km:.2f} km | ⏱️ {int(dur)} min")

                                # --- AUTOMATYCZNE PORÓWNANIE ---
                                # Szukamy firmy z najniższą wartością 'Val'
                                najtansza = min(dane, key=lambda x: x['Val'])
                                
                                # Wyświetlamy baner z informacją
                                st.info(f"🏆 **NAJLEPSZY WYBÓR:** Obecnie najtaniej pojedziesz z **{najtansza['Firma']}**!")
                                
                                # Opcjonalnie: Obliczamy ile oszczędzasz względem najdroższej opcji
                                najdrozsza = max(dane, key=lambda x: x['Val'])
                                oszczednosc = najdrozsza['Val'] - najtansza['Val']
                                
                                if oszczednosc > 2: # Pokazuj tylko, jeśli różnica jest większa niż 2 zł
                                    st.markdown(f"💡 Wybierając tę opcję, oszczędzasz ok. **{oszczednosc:.2f} PLN** względem najdroższego przewoźnika.")
                                
                                st.write("---") # Oddzielenie kreską od szczegółowej listy

                                for item in sorted(dane, key=lambda x: x['Val']):
                                    c1, c2 = st.columns([3, 1])
                                    with c1:
                                        disc = f" <span class='discount-tag'>-{item['Promo']}%</span>" if item['Promo'] > 0 else ""
                                        st.markdown(f"**{item['Firma']}**{disc}", unsafe_allow_html=True)
                                        st.markdown(f"### {item['Main']}")
                                        if item['Vars']:
                                            for v_name, v_price in item['Vars']:
                                                st.markdown(f"<div class='variant-card'><span>{v_name}</span><b>~ {v_price:.2f} PLN</b></div>", unsafe_allow_html=True)
                                    with c2:
                                        st.write("")
                                        st.link_button(item['Btn'], item['Link'])
                                    st.write("---")

                                st.caption("ℹ️ Ceny dojazdu są szacunkowe i mogą różnić się w oficjalnych aplikacjach.")

                                # --- formularz korekty AI ---
                                # --- formularz korekty AI (POPRAWIONY) ---
                                st.markdown("### 🧠 Pomóż ulepszyć AI (opcjonalne)")
                                
                                with st.form("correction_form"):
                                    col_c1, col_c2, col_c3 = st.columns(3)
                                    with col_c1:
                                        real_uber = st.number_input("Cena UberX w aplikacji", min_value=0.0, step=0.5)
                                    with col_c2:
                                        real_bolt = st.number_input("Cena Bolt w aplikacji", min_value=0.0, step=0.5)
                                    with col_c3:
                                        real_fn = st.number_input("Cena FreeNow w aplikacji", min_value=0.0, step=0.5)
                                    
                                    submitted = st.form_submit_button("Zapisz korektę AI")
                                    
                                    if submitted:
                                        # Pobieramy aktualne dane kontekstowe
                                        ctx = st.session_state.ai_data.get(context_key, {"uber": 1.0, "bolt": 1.0, "freenow": 1.0})
                                        
                                        # Logika nauki: porównujemy cenę wyliczoną z rzeczywistą
                                        if real_uber > 0 and st.session_state.get('uber_x', 0) > 0:
                                            factor = real_uber / st.session_state.uber_x
                                            ctx["uber"] = ctx.get("uber", 1.0) * (0.8 + 0.2 * factor)
                                
                                        if real_bolt > 0 and st.session_state.get('bolt_std', 0) > 0:
                                            factor = real_bolt / st.session_state.bolt_std
                                            ctx["bolt"] = ctx.get("bolt", 1.0) * (0.8 + 0.2 * factor)
                                
                                        if real_fn > 0 and st.session_state.get('freenow_lite', 0) > 0:
                                            factor = real_fn / st.session_state.freenow_lite
                                            ctx["freenow"] = ctx.get("freenow", 1.0) * (0.8 + 0.2 * factor)
                                        
                                        # Nadpisujemy w pamięci sesji
                                        st.session_state.ai_data[context_key] = ctx
                                        
                                        # Zapisujemy do bazy danych
                                        if save_data(st.session_state.ai_data):
                                            st.toast("Mózg AI zaktualizowany!", icon="🧠")
                                            st.success("✅ Dane zapisane w chmurze. Przy następnym sprawdzeniu ceny będą dokładniejsze!")
                                            st.rerun() # Odświeżamy, by zastosować nowe mnożniki
                                            
                                        # --- KONIEC GŁÓWNEJ LOGIKI ---
                                        except Exception as e:
                                            st.error(f"⚠️ Błąd podczas pobierania trasy: {e}")
                                    else:
                                        st.warning("⚠️ Nie znaleziono jednego z adresów we Wrocławiu.")
