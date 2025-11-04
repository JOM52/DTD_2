# main.py - Détecteur Distant (DD) pour ESP32 + GT38 (MicroPython)
# Version : 1.5 - SET sur GPIO5, Radio toujours ON

from machine import Pin, UART, Timer, reset
import time

# ============================ CONFIG ============================
UART_PORT = 1
UART_BAUD = 9600
UART_TX_PIN = 17         # ESP32 → GT38 RX
UART_RX_PIN = 16         # ESP32 ← GT38 TX
GT38_SET_PIN = 5         # Pin SET du GT38 (mode CONFIG/RUN)
LED_PIN = 2              # LED de statut (ou LED intégrée)

# Watchdog
WATCHDOG_ENABLED = False  # Mettre False pour debug avec Thonny
WATCHDOG_MS = 30000      # 30 s

# Mode développement
DEV_MODE = True         # True pour désactiver watchdog

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
        # on réserve 8 octets maximum
        b = bytearray(8)
        ln = n.get_blob("id", b)
        if ln and ln > 0:
            return b[:ln].decode()
    except Exception:
        pass
    return None

def _get_id_from_straps():
    try:
        # définir broches straps; pull-up attendu, strap à la masse pour 0
        pA = Pin(18, Pin.IN, Pin.PULL_UP)
        pB = Pin(19, Pin.IN, Pin.PULL_UP)
        pC = Pin(21, Pin.IN, Pin.PULL_UP)
        # lire bits (0 si serré à la masse)
        bit0 = 0 if pA.value() == 0 else 1
        bit1 = 0 if pB.value() == 0 else 1
        bit2 = 0 if pC.value() == 0 else 1
        val = (bit2 << 2) | (bit1 << 1) | (bit0 << 0)
        # mapping explicite: val range 0..7 ; on ignore 0 et >5
        mapping = {
            1: "01",
            2: "02",
            3: "03",
            4: "04",
            5: "05"
        }
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
print("[DD] Démarrage v1.5")
print("[DD] ID: {}".format(DETECTOR_ID))

# LED
led = Pin(LED_PIN, Pin.OUT)
# Clignotement court pour indiquer boot
led.value(1)
time.sleep_ms(100)
led.value(0)

# Pin SET du GT38 (mode RUN par défaut)
print("[DD] Init pin SET (GPIO{})".format(GT38_SET_PIN))
try:
    gt38_set = Pin(GT38_SET_PIN, Pin.OUT)
    gt38_set.value(1)  # Mode RUN (transparent)
    print("[DD] GT38 en mode RUN (SET=HIGH)")
except Exception as e:
    print("[DD] Erreur pin SET: {}".format(e))
    gt38_set = None

# Initialisation UART (MicroPython ESP32)
print("[DD] Init UART{} à {} bauds".format(UART_PORT, UART_BAUD))
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
    # Protéger contre réentrance
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

# Initialiser watchdog seulement si activé et pas en mode dev
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
    except Exception:
        # Tentative d'écriture en bytes si encode échoue
        try:
            uart.write(bytes(s))
        except Exception:
            pass

def send_ack(det_id, state):
    """Envoie un ACK au TA"""
    _uart_write_str("ACK:{}:{}\n".format(det_id, 1 if state else 0))

def send_ack_id_change(ok, new_id):
    """Envoie un ACK pour changement d'ID"""
    _uart_write_str("ACKSETID:{}:{}\n".format(new_id, "OK" if ok else "ERR"))

# ======================== BOUCLE PRINCIPALE =====================
# Buffer réutilisable
buf = bytearray()
loop_count = 0
ok_count = 0           # POLL adressés à ce DD (ou ALL)
nok_count = 0          # POLL non adressés à ce DD
setid_ok_count = 0     # SETID persistés avec succès
setid_err_count = 0    # SETID en erreur (échec NVS)

# Vider le buffer UART au démarrage (éviter données parasites)
time.sleep_ms(200)
while uart.any():
    uart.read()

# Message de boot
_uart_write_str("BOOT:{}\n".format(DETECTOR_ID))
print("[DD] Message BOOT envoyé")
led.value(0)

print("[DD] Boucle principale démarrée\n")

while True:
    # Mise à jour watchdog
    last_loop_ts = time.ticks_ms()
    loop_count += 1

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
                    
                    # Extraire ligne sans copie lourde
                    line = bytes(buf[:nl + 1])
                    # Supprimer consommé
                    buf = bytearray(buf[nl + 1:])

                    parsed = parse_line(line)
                    if not parsed:
                        continue

                    cmd, det_id, _ = parsed

                    if cmd == "POLL":
                        if det_id == DETECTOR_ID or det_id.upper() == "ALL":
                            # Commande pour ce détecteur
                            state = measure_state()
                            send_ack(DETECTOR_ID, state)
                            ok_count += 1
                            
                            # Feedback LED bref
                            try:
                                led.value(1)
                                time.sleep_ms(40)
                                led.value(0)
                            except Exception:
                                pass
                        else:
                            # Commande pour un autre détecteur
                            nok_count += 1

                    elif cmd == "SETID":
                        # Changement d'ID
                        new_id = det_id
                        ok = _persist_id_to_nvs(new_id)
                        
                        if ok:
                            DETECTOR_ID = new_id
                            setid_ok_count += 1
                            print("[DD] ID changé: {}".format(new_id))
                            
                            # Feedback LED long
                            try:
                                led.value(1)
                                time.sleep_ms(100)
                                led.value(0)
                            except Exception:
                                pass
                        else:
                            setid_err_count += 1
                            print("[DD] Erreur changement ID")
                        
                        send_ack_id_change(ok, new_id)
    except Exception as e:
        if DEV_MODE:
            print("[DD] Erreur boucle: {}".format(e))
                        
    # Affichage périodique des stats (toutes les 100 boucles = 10s)
    if (loop_count % 100) == 0:
        try:
            print("[{}] id={} ok={} nok={} setid_ok={} setid_err={}".format(
                loop_count, DETECTOR_ID, ok_count, nok_count, 
                setid_ok_count, setid_err_count
            ))
        except Exception:
            pass

    # Délai de boucle (100ms)
    time.sleep_ms(500)
# ```
# 
# ---
# 
# ## 🔌 Câblage DD avec SET sur GPIO5
# ```
# ESP32 DD          GT38
# ─────────────────────────
# GPIO32 (TX)   →   RXD
# GPIO33 (RX)   ←   TXD
# GPIO5         →   SET    ← Configuration mode
# 3.3V          →   VCC    (toujours alimenté)
# GND           →   GND