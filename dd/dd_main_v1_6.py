# dd_main.py - Détecteur Distant (DD) pour ESP32 + GT38 (MicroPython)
# Version : 1.6 - Optimisations communication rapide
# Changelog v1.6:
#   - Délai boucle: 500ms → 50ms (10× plus réactif)
#   - LED non-bloquante (asyncio ou toggle rapide)
#   - Timeout UART configuré
#   - Buffer systématiquement vidé avant réponse
#   - Stats détaillées (timing, erreurs)
#   - Mode debug amélioré

from machine import Pin, UART, Timer, reset
import time

# ============================ CONFIG ============================
UART_PORT = 1
UART_BAUD = 9600
UART_TX_PIN = 17         # ESP32 → GT38 RX
UART_RX_PIN = 16         # ESP32 ← GT38 TX
GT38_SET_PIN = 5         # Pin SET du GT38 (mode CONFIG/RUN)
LED_PIN = 2              # LED de statut

# Watchdog
WATCHDOG_ENABLED = False  # False pour debug avec Thonny
WATCHDOG_MS = 30000      # 30s

# Mode développement
DEV_MODE = True          # True pour logs verbeux

# Timing optimisé
LOOP_DELAY_MS = 50       # 50ms (était 500ms) - 10× plus réactif
LED_BLINK_MS = 20        # LED ultra-rapide (était 40ms)

# ====================== ID UNIQUE DU DETECTEUR ==================
def _get_id_from_config():
    try:
        import config
        did = getattr(config, "DETECTOR_ID", None)
        if isinstance(did, str) and 1 <= len(did) <= 8:
            return did
    except Exception:
        pass
    return None

def _get_id_from_nvs():
    try:
        import esp32
        n = esp32.NVS("dd")
        b = bytearray(8)
        ln = n.get_blob("id", b)
        if ln and ln > 0:
            return b[:ln].decode()
    except Exception:
        pass
    return None

def _get_id_from_straps():
    try:
        pA = Pin(18, Pin.IN, Pin.PULL_UP)
        pB = Pin(19, Pin.IN, Pin.PULL_UP)
        pC = Pin(21, Pin.IN, Pin.PULL_UP)
        bit0 = 0 if pA.value() == 0 else 1
        bit1 = 0 if pB.value() == 0 else 1
        bit2 = 0 if pC.value() == 0 else 1
        val = (bit2 << 2) | (bit1 << 1) | (bit0 << 0)
        mapping = {1: "01", 2: "02", 3: "03", 4: "04", 5: "05"}
        return mapping.get(val, None)
    except Exception:
        return None

def _persist_id_to_nvs(new_id):
    try:
        import esp32
        n = esp32.NVS("dd")
        b = new_id.encode()
        n.set_blob("id", b)
        n.commit()
        return True
    except Exception:
        return False

DETECTOR_ID = (
    _get_id_from_config()
    or _get_id_from_nvs()
    or _get_id_from_straps()
    or "01"
)

# ======================== INITIALISATION ========================
print("[DD] Démarrage v1.6 (optimisé)")
print("[DD] ID: {}".format(DETECTOR_ID))

# LED
led = Pin(LED_PIN, Pin.OUT)
led_state = False
led_timer = 0  # Timer pour LED non-bloquante

def led_pulse():
    """Impulsion LED non-bloquante"""
    global led_state, led_timer
    led_state = True
    led.value(1)
    led_timer = time.ticks_ms()

def led_update():
    """Mise à jour LED (à appeler dans boucle)"""
    global led_state, led_timer
    if led_state:
        if time.ticks_diff(time.ticks_ms(), led_timer) > LED_BLINK_MS:
            led.value(0)
            led_state = False

# Clignotement boot
led.value(1)
time.sleep_ms(100)
led.value(0)

# Pin SET du GT38 (mode RUN par défaut)
print("[DD] Init pin SET (GPIO{})".format(GT38_SET_PIN))
try:
    gt38_set = Pin(GT38_SET_PIN, Pin.OUT)
    gt38_set.value(1)  # Mode RUN
    print("[DD] GT38 en mode RUN (SET=HIGH)")
except Exception as e:
    print("[DD] Erreur pin SET: {}".format(e))
    gt38_set = None

# Initialisation UART avec timeout
print("[DD] Init UART{} à {} bauds".format(UART_PORT, UART_BAUD))
try:
    uart = UART(
        UART_PORT, 
        baudrate=UART_BAUD, 
        tx=Pin(UART_TX_PIN), 
        rx=Pin(UART_RX_PIN),
        timeout=100,  # ✓ NOUVEAU: Timeout 100ms
        rxbuf=256     # ✓ NOUVEAU: Buffer explicite
    )
    print("[DD] UART initialisé (timeout=100ms)")
except Exception as e:
    print("[DD] Erreur UART: {}".format(e))
    # Fallback sans timeout si pas supporté
    uart = UART(UART_PORT, baudrate=UART_BAUD, tx=Pin(UART_TX_PIN), rx=Pin(UART_RX_PIN))

# ========================== WATCHDOG ============================
last_loop_ts = time.ticks_ms()
_wdt_triggered = False
wdt_timer = None

def _blink_led(times, on_ms=80, off_ms=80):
    """Clignotement LED"""
    for _ in range(times):
        led.value(1)
        time.sleep_ms(on_ms)
        led.value(0)
        time.sleep_ms(off_ms)

def wdt_cb(t):
    """Callback watchdog"""
    global last_loop_ts, _wdt_triggered
    if _wdt_triggered:
        return
    if time.ticks_diff(time.ticks_ms(), last_loop_ts) > WATCHDOG_MS:
        _wdt_triggered = True
        print("[DD] WATCHDOG TIMEOUT - RESET")
        try:
            _blink_led(4, 80, 80)
        except Exception:
            pass
        reset()

# Initialiser watchdog si activé
if WATCHDOG_ENABLED and not DEV_MODE:
    try:
        wdt_timer = Timer(0)
        wdt_timer.init(period=max(100, WATCHDOG_MS // 2), mode=Timer.PERIODIC, callback=wdt_cb)
        print("[DD] Watchdog activé ({}s)".format(WATCHDOG_MS // 1000))
    except Exception as e:
        print("[DD] Erreur watchdog: {}".format(e))
        wdt_timer = None
else:
    if DEV_MODE:
        print("[DD] Mode DEV : Watchdog désactivé")
    else:
        print("[DD] Watchdog désactivé par config")

# ======================= OUTILS / PROTOCOLE =====================
def parse_line(line):
    """Parse une ligne de commande reçue"""
    try:
        s = line.decode().strip()
    except Exception:
        return None

    if s.startswith("POLL:"):
        parts = s.split(":", 1)
        if len(parts) >= 2:
            return ("POLL", parts[1].strip(), None)
    
    if s.startswith("SETID:"):
        parts = s.split(":", 1)
        if len(parts) == 2:
            candidate = parts[1].strip()
            if 1 <= len(candidate) <= 8:
                return ("SETID", candidate, None)
    
    return None

def measure_state():
    """Mesure l'état du détecteur"""
    # TODO: Remplacer par mesure réelle (opto/ADC/etc.)
    return 1  # Simulé : alimenté

def _uart_write_str(s):
    """Écriture UART robuste"""
    try:
        uart.write(s.encode())
        return True
    except Exception as e:
        if DEV_MODE:
            print("[DD] Erreur write: {}".format(e))
        return False

def flush_uart_rx():
    """Vide le buffer RX de l'UART (éviter données résiduelles)"""
    flushed = 0
    try:
        while uart.any():
            uart.read(1)
            flushed += 1
            if flushed > 100:  # Limite sécurité
                break
    except Exception:
        pass
    return flushed

def send_ack(det_id, state):
    """Envoie un ACK au TA"""
    # ✓ NOUVEAU: Vider buffer avant réponse pour éviter collisions
    flush_uart_rx()
    
    msg = "ACK:{}:{}\n".format(det_id, 1 if state else 0)
    success = _uart_write_str(msg)
    
    if DEV_MODE and not success:
        print("[DD] Échec envoi ACK")
    
    return success

def send_ack_id_change(ok, new_id):
    """Envoie un ACK pour changement d'ID"""
    flush_uart_rx()
    _uart_write_str("ACKSETID:{}:{}\n".format(new_id, "OK" if ok else "ERR"))

# ======================== STATISTIQUES ==========================
stats = {
    "loop_count": 0,
    "ok_count": 0,           # POLL adressés à ce DD
    "nok_count": 0,          # POLL non adressés
    "setid_ok": 0,
    "setid_err": 0,
    "uart_read_err": 0,
    "parse_err": 0,
    "last_poll_time": 0,     # Timestamp dernier POLL
    "min_response_time": 9999,
    "max_response_time": 0,
    "avg_response_time": 0
}

def print_stats():
    """Affiche les statistiques"""
    print("[STATS] loop={} ok={} nok={} setid_ok={} setid_err={}".format(
        stats["loop_count"], stats["ok_count"], stats["nok_count"],
        stats["setid_ok"], stats["setid_err"]
    ))
    
    if stats["ok_count"] > 0:
        print("[STATS] response_time: min={}ms avg={}ms max={}ms".format(
            stats["min_response_time"],
            stats["avg_response_time"],
            stats["max_response_time"]
        ))
    
    if stats["uart_read_err"] > 0 or stats["parse_err"] > 0:
        print("[STATS] errors: uart={} parse={}".format(
            stats["uart_read_err"], stats["parse_err"]
        ))

# ======================== BOUCLE PRINCIPALE =====================
buf = bytearray()

# Vider buffer au démarrage
time.sleep_ms(200)
flushed = flush_uart_rx()
if flushed > 0 and DEV_MODE:
    print("[DD] Buffer initial vidé: {} bytes".format(flushed))

# Message de boot
_uart_write_str("BOOT:{}\n".format(DETECTOR_ID))
print("[DD] Message BOOT envoyé")
led.value(0)

print("[DD] Boucle principale démarrée (délai {}ms)\n".format(LOOP_DELAY_MS))

while True:
    # Mise à jour watchdog
    last_loop_ts = time.ticks_ms()
    stats["loop_count"] += 1

    # Mise à jour LED non-bloquante
    led_update()

    # Lecture UART
    try:
        if uart.any():
            data = uart.read()
            if data:
                buf.extend(data)
                
                # Traiter toutes les lignes complètes
                while True:
                    nl = buf.find(b'\n')
                    if nl == -1:
                        break
                    
                    # Extraire ligne
                    line = bytes(buf[:nl + 1])
                    buf = bytearray(buf[nl + 1:])

                    # Timestamp début traitement
                    process_start = time.ticks_ms()

                    parsed = parse_line(line)
                    if not parsed:
                        stats["parse_err"] += 1
                        continue

                    cmd, det_id, _ = parsed

                    if cmd == "POLL":
                        if det_id == DETECTOR_ID or det_id.upper() == "ALL":
                            # Commande pour ce détecteur
                            state = measure_state()
                            success = send_ack(DETECTOR_ID, state)
                            
                            if success:
                                stats["ok_count"] += 1
                                
                                # Calculer temps de réponse
                                response_time = time.ticks_diff(time.ticks_ms(), process_start)
                                if response_time < stats["min_response_time"]:
                                    stats["min_response_time"] = response_time
                                if response_time > stats["max_response_time"]:
                                    stats["max_response_time"] = response_time
                                
                                # Moyenne glissante simple
                                stats["avg_response_time"] = (
                                    (stats["avg_response_time"] * (stats["ok_count"] - 1) + response_time)
                                    // stats["ok_count"]
                                )
                                
                                # Feedback LED ultra-rapide non-bloquant
                                led_pulse()
                                
                                if DEV_MODE:
                                    print("[DD] POLL→ACK en {}ms".format(response_time))
                        else:
                            # Commande pour un autre détecteur
                            stats["nok_count"] += 1

                    elif cmd == "SETID":
                        # Changement d'ID
                        new_id = det_id
                        ok = _persist_id_to_nvs(new_id)
                        
                        if ok:
                            DETECTOR_ID = new_id
                            stats["setid_ok"] += 1
                            print("[DD] ID changé: {}".format(new_id))
                            led_pulse()
                        else:
                            stats["setid_err"] += 1
                            print("[DD] Erreur changement ID")
                        
                        send_ack_id_change(ok, new_id)
                        
    except Exception as e:
        stats["uart_read_err"] += 1
        if DEV_MODE:
            print("[DD] Erreur boucle: {}".format(e))
                        
    # Affichage périodique des stats (toutes les 200 boucles ≈ 10s avec 50ms)
    if (stats["loop_count"] % 200) == 0:
        print_stats()

    # ✓ DÉLAI OPTIMISÉ: 50ms au lieu de 500ms (10× plus réactif)
    time.sleep_ms(LOOP_DELAY_MS)