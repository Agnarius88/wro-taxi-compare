import streamlit as st
import openrouteservice
from geopy.geocoders import Nominatim
import math
from datetime import datetime
import random
import pytz
import json
import os

# --- 1. INTELIGENTNE USTALANIE ŚCIEŻKI (POPRAWIONE) ---
import platform

def h(time_str): # --- Zmiana formatu czasu
    """Zamienia '15:10' na 15.17"""
    try:
        hours, minutes = map(int, time_str.split(':'))
        return round(hours + (minutes / 60), 2)
    except:
        return 0.0 # Zabezpieczenie przed błędami

# Pobieramy ścieżkę do folderu domowego użytkownika (np. C:\Users\Piotr)
home = os.path.expanduser("~")

# Sprawdzamy czy jesteśmy na Windowsie
if platform.system() == "Windows":
    # Budujemy ścieżkę do Pulpitu
    desktop = os.path.join(home, 'Desktop')
    folder_path = os.path.join(desktop, "Apka", "raport")
else:
    # Jesteś w chmurze lub na Linuxie
    folder_path = "data" 

# Tworzymy folder, jeśli nie istnieje
os.makedirs(folder_path, exist_ok=True)
PATH = os.path.join(folder_path, "ai_memory.json")


# --- 2. ŁADOWANIE PAMIĘCI ---
if "ai_data" not in st.session_state:
    if os.path.exists(PATH):
        try:
            with open(PATH, "r", encoding='utf-8') as f:
                st.session_state.ai_data = json.load(f)
        except:
            st.session_state.ai_data = {}
    else:
        st.session_state.ai_data = {}
        
if "show_results" not in st.session_state:
    st.session_state.show_results = False  

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
now = datetime.now(tz_PL) 
current_hour = now.hour  # <--- ZMIENIONA NAZWA ZMIENNEJ
time_val = current_hour + now.minute/60
day = now.weekday() 
is_weekend = (day >= 5)
is_night = (time_val >= 22 or time_val < 6)
is_peak = not is_weekend and (
    (h("07:30") <= time_val < h("09:30")) or 
    (h("15:30") <= time_val < h("18:30"))
)
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
elif (h("10:15") <= time_val < h("10:40")):
    t_status = "📉 SPOKÓJ PRZEDPOŁUDNIOWY"
    u_base, u_km = 5.00, 1.70  
    b_base, b_km = 3.50, 1.90
    fn_fix = 2.00
    time_rate = 0.15
elif (h('11:00') <= time_val < h('11:30')):
    t_status = "📉 PRZEDPOŁUDNIOWY DOŁEK"
    u_base, u_km = 7.50, 1.90    # To Twoje "standardowe" ceny, które były o 10:00
    b_base, b_km = 4.80, 2.30
    fn_fix = 2.00
    time_rate = 0.15    
elif (h('11:30') <= time_val < h('12:15')):
    t_status = "⚖️ STABILIZACJA PRZEDPOŁUDNIOWA (11:30-12:15)"
    u_base, u_km = 7.00, 2.00  
    b_base, b_km = 6.50, 2.35
    fn_fix = 2.00
    time_rate = 0.25            # Normalna stawka czasowa
elif (h('13:30') <= time_val <= h('14:30')):
    t_status = "📉 PRZEDSZCZYTOWA PROMOCJA BOLT"
    u_base, u_km = 9.00, 2.35
    b_base, b_km = 2.80, 2.70 
    fn_fix = 2.00
    time_rate = 0.15
elif (h('15:10') <= time_val < h('15:30')):
    u_base, u_km = 4.5, 2.25 
    b_base, b_km = 5.00, 2.70
    fn_fix = -10  
    time_rate = 0.45
elif (h("17:00") <= time_val < h("18:00")):
    t_status = "📉 POPOŁUDNIOWE ROZLUŹNIENIE (17:00-18:00)"
    u_base, u_km = 6.50, 1.60   # Znacznie niższa stawka za km (było 1.90)
    b_base, b_km = 4.50, 2.45   # 
    fn_fix = 1.00
    time_rate = 0.20            # Mniejsza dopłata za korki
#elif (13.0 <= time_val < 14.0): <--- To jest szablon do korekty cen w zależności od godziny
   #t_status = "🕒 POŁUDNIOWY SKOK CEN"
    #u_base = 9.00  # było 8.00, więc dodajemy 1 zł
    #b_base = 6.00  # było 5.00, więc dodajemy 1 zł
    #u_km = 2.10    # stawka za km zostaje standardowa
    #b_km = 2.70  
elif (h("18:00") <= time_val < h("19:00")):
    t_status = "🌆 WIECZORNY POWRÓT (18:00-19:00)"
    u_base, u_km = 6.20, 1.70   
    b_base, b_km = 3.50, 1.95
    time_rate = 0.20            # Mniejszy ruch, mniej płacimy za minuty
    fn_fix = 0.50               # FreeNow ma być blisko Ubera  
elif is_peak: #  peak jest ustawiony 7:30 - 9:30 i 15:30 - 18:30
    # Szczyt (Twoje 15:22 - korki + wysoki popyt)
    u_base, u_km = 8.0, 1.90 
    b_base, b_km = 4.00, 2.20
    fn_fix = 3.50  
    time_rate = 0.40         # Minuta droższa, bo stoisz na światłach
else:
    t_status = "☀️ STANDARDOWY DZIEŃ (np. 10:00)"
    u_base, u_km = 8.00, 2.10
    b_base, b_km = 3.00, 2.70
    fn_fix = 2.50
    time_rate = 0.20

st.markdown(f"<div class='tariff-info'>Aktualna godzina: {current_hour:02d}:{now.minute:02d}</div>", unsafe_allow_html=True)

# --- USŁUGI ---
ORS_KEY = 'eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6Ijc2N2YwMmI0Y2M2OTRkMjE5MDk5MDU4ZTg3NzMxYjYzIiwiaCI6Im11cm11cjY0In0='

def get_data():
    try:
        return openrouteservice.Client(key=ORS_KEY)
    except Exception as e:
        st.error(f"Błąd klucza API: {e}")
        return None

client = get_data()

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
           with st.spinner("Szukanie adresów i trasy..."):
                try:
                    # --- TŁUMACZ ADRESÓW (SZYBKI FIX) ---
                    def fix_address(adr):
                        adr_low = adr.lower().strip()
                        # Jeśli wpiszesz tylko "lotnisko" lub "na lotnisko"
                        if "lotnisko" in adr_low:
                            return "Port Lotniczy Wrocław, Graniczna"
                        # Możesz tu dodać inne skróty, np. dworzec
                        if adr_low == "pkp" or adr_low == "dworzec":
                            return "Dworzec Główny PKP Wrocław"
                        return adr

                    # Naprawiamy adresy przed wysłaniem do map
                    search_start = fix_address(start_adr)
                    search_cel = fix_address(cel_adr)

                    # --- SZUKANIE WSPÓŁRZĘDNYCH (używamy naprawionych adresów) ---
                    res_a = client.pelias_search(text=search_start, focus_point=[17.03, 51.10], size=1)
                    res_b = client.pelias_search(text=search_cel, focus_point=[17.03, 51.10], size=1)
        
                    if res_a['features'] and res_b['features']:
                        # Pobieramy współrzędne [lon, lat]
                        coords_a = res_a['features'][0]['geometry']['coordinates']
                        coords_b = res_b['features'][0]['geometry']['coordinates']
        
                        # --- LICZENIE TRASY ---
                        res = client.directions(
                            coordinates=(coords_a, coords_b),
                            profile='driving-car',
                            format='geojson'
                        )
                        
                        if 'features' in res and len(res['features']) > 0:
                            # 1. Wyciągnięcie współrzędnych z ORS w formacie (lon, lat)
                            lon_a, lat_a = coords_a[0], coords_a[1]
                            lon_b, lat_b = coords_b[0], coords_b[1]
                            
                            # 2. Pobranie dystansu (km) i czasu (min)
                            km = res['features'][0]['properties']['summary']['distance'] / 1000
                            dur = res['features'][0]['properties']['summary']['duration'] / 60
                            
                            # POPRAWIONE WCIĘCIA DLA PONIŻSZEGO BLOKU:
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

                            # --- DEFINICJA NAJTAŃSZYCH OPJI DLA PORÓWNANIA ---
                            uber_cheap = uber_x * 0.85  # Czekaj i oszczędzaj
                            # --- LOGIKA DYNAMICZNEJ ZNIŻKI BOLT ---
                            if (h('15:10') <= time_val < h('16:00')) or (is_peak and time_val < h('18:00')):
                                bolt_discount = 9  # Mocna zniżka w głębokim szczycie
                            elif (h('18:00') <= time_val < h('19:00')):
                                bolt_discount = 5  # Twoja nowa zniżka wieczorna
                            else:
                                bolt_discount = 3  # Standardowa zniżka poza szczytem
                            
                            bolt_cheap = bolt_std - bolt_discount
                            
                            # POPRAWIONY LINK DO UBERA - używamy lat_a, lon_a, lat_b, lon_b
                            dane = [
                                {"Firma": "Uber 🚗", "Btn": "WYBIERZ", "Val": uber_cheap, "Promo": u_promo,
                                 "Main": f"~ {uber_cheap:.2f} PLN",
                                 "Link": f"https://m.uber.com/ul/?action=setPickup&pickup[latitude]={lat_a}&pickup[longitude]={lon_a}&dropoff[latitude]={lat_b}&dropoff[longitude]={lon_b}",
                                 "Vars": [("📉 Czekaj i oszczędzaj", uber_x*0.85), 
                                          ("🚗 UberX / 🔋 Hybrid", uber_x),                                                                                          
                                          ("🐾 Uber Pets", uber_x+4)]},
                                {"Firma": "Bolt ⚡", "Btn": "WYBIERZ", "Val": bolt_cheap, "Promo": b_promo,
                                 "Main": f"~ {bolt_cheap:.2f} PLN", "Link": "bolt://ride",
                                 "Vars": [("📉 Wait and Save", bolt_cheap),  # <--- Teraz używamy gotowej zmiennej!,                                           
                                          ("⚡ Bolt /🔋 Hybrid", bolt_std),
                                          ("🐾 Pet", bolt_std+4)]},                                         
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
                            st.markdown("### 🧠 Pomóż ulepszyć AI (opcjonalne)")
                            
                            # zapisujemy aktualne wartości w session_state, żeby nie znikały po odświeżeniu
                            if "real_uber" not in st.session_state:
                                st.session_state.real_uber = 0.0
                            if "real_bolt" not in st.session_state:
                                st.session_state.real_bolt = 0.0
                            if "real_fn" not in st.session_state:
                                st.session_state.real_fn = 0.0
                            
                            with st.form("correction_form"):
                                real_uber = st.number_input("Rzeczywista cena UberX", min_value=0.0, step=1.0)
                                real_bolt = st.number_input("Rzeczywista cena Bolt", min_value=0.0, step=1.0)
                                real_fn = st.number_input("Rzeczywista cena FreeNow", min_value=0.0, step=1.0)
                                
                                submitted = st.form_submit_button("Zapisz korektę AI")
                                
                                if submitted:
                                    ctx = st.session_state.ai_data[context_key]
                                    
                                    # KOREKTA UBERA
                                    if real_uber > 0:
                                        # Używamy dokładnie tego, co widzi użytkownik w tabelce 'dane'
                                        # (st.session_state.uber_x już zawiera w sobie mnożnik ctx!)
                                        app_visible_price = st.session_state.uber_x 
                                        
                                        factor = real_uber / app_visible_price
                                        st.write(f"DEBUG: Cena w apce: {app_visible_price:.2f} zł | Realna: {real_uber:.2f} zł | Factor: {factor:.4f}")
                                        
                                        # Aktualizacja mnożnika
                                        ctx["uber"] *= (0.7 + 0.3 * factor)
                                
                                    # KOREKTA BOLTA
                                    if real_bolt > 0:
                                        # 
                                        app_visible_price_bolt = st.session_state.bolt_std 
                                        factor = real_bolt / app_visible_price_bolt
                                        ctx["bolt"] *= (0.7 + 0.3 * factor)
                                        
                                    # KOREKTA FREE NOW
                                    if real_fn > 0:
                                        # FreeNow w tabelce nie ma dodatkowego mnożnika
                                        app_visible_price_fn = st.session_state.freenow_lite
                                        factor = real_fn / app_visible_price_fn
                                        ctx["freenow"] *= (0.7 + 0.3 * factor)
                            
                                    try:
                                        with open(PATH, "w") as f:
                                            json.dump(st.session_state.ai_data, f)
                                        st.toast("Mózg AI zaktualizowany na Pulpicie!", icon="🧠")
                                        st.success(f"✅ Dane zapisane w: {PATH}")
                                    except Exception as e:
                                        st.error(f"❌ Nie udało się zapisać pliku na Pulpicie. Błąd: {e}")
                                    # --- PODGLĄD PAMIĘCI AI PO ZAPISIE ---
                                    st.markdown("#### 🔍 Aktualny stan pamięci dla tej godziny:")
                                    # Wyświetlamy tylko dane dla obecnego kontekstu (godzina/dzień), żeby było czytelnie
                                    st.json(st.session_state.ai_data[context_key])
                                    
                                    # Opcjonalnie: jeśli chcesz widzieć CAŁY plik, użyj:
                                    # st.json(st.session_state.ai_data)    
                        else:
                            st.warning("⚠️ Serwer map nie znalazł trasy.")
                    
                    # To 'else' jest parą do: if res_a['features'] and res_b['features']:
                    else:
                        st.warning("⚠️ Nie znaleziono adresu.")
                
                # To 'except' jest parą do głównego: try: (zaraz pod with st.spinner)
                except Exception as e:
                    st.error(f"⚠️ Błąd obliczeń trasy lub mapy: {e}")
# --- SEKCJA EKSPORTU DANYCH (NA SAMYM DOLE PLIKU) ---
st.markdown("---")
st.markdown("### 💾 Zarządzanie pamięcią AI")

# Konwertujemy aktualne dane AI z sesji do formatu JSON (tekstowego)
ai_memory_json = json.dumps(st.session_state.ai_data, indent=4, ensure_ascii=False)

col_dl, col_info = st.columns([1, 2])

with col_dl:
    # Przycisk do pobierania pliku
    st.download_button(
        label="📥 Pobierz ai_memory.json",
        data=ai_memory_json,
        file_name="ai_memory.json",
        mime="application/json",
        help="Pobierz ten plik i wrzuć go do folderu Apka/raport na swoim komputerze, aby AI 'pamiętało' ceny."
    )

