"""
Configuration GT38 pour Détecteur Distant (DD)
Pins: UART1, TX=GPIO32, RX=GPIO33, SET=GPIO5
Version: 1.0
"""
from machine import UART, Pin
import time

# ==================== CONFIGURATION ====================
UART_PORT = 1
UART_BAUD = 9600
UART_TX_PIN = 17    # ESP32 → GT38 RXD
UART_RX_PIN = 18    # ESP32 ← GT38 TXD
GT38_SET_PIN = 43    # Mode CONFIG/RUN

print("="*70)
print(" "*15 + "CONFIGURATION GT38 - DÉTECTEUR DISTANT")
print("="*70)

print("\nConfiguration matérielle:")
print("  • UART Port: {}".format(UART_PORT))
print("  • Baud Rate: {}".format(UART_BAUD))
print("  • TX (ESP32→GT38): GPIO{} → RXD".format(UART_TX_PIN))
print("  • RX (ESP32←GT38): GPIO{} ← TXD".format(UART_RX_PIN))
print("  • SET (Mode):      GPIO{}".format(GT38_SET_PIN))
print("="*70)

# ==================== FONCTIONS UTILITAIRES ====================

def send_at_command(uart, cmd, delay=400):
    """Envoie une commande AT et retourne la réponse"""
    # Vider buffer
    while uart.any():
        uart.read(uart.any())
    
    # Envoyer commande
    uart.write(cmd.encode() + b'\r\n')
    time.sleep_ms(delay)
    
    # Lire réponse
    if uart.any():
        try:
            return uart.read(uart.any()).decode('utf-8', 'ignore').strip()
        except:
            return None
    return None

def print_step(num, total, title):
    """Affiche un titre d'étape"""
    print("\n[{}/{}] {}".format(num, total, title))
    print("-"*70)

def print_result(message, status="info"):
    """Affiche un résultat avec icône"""
    icons = {
        "ok": "✓",
        "error": "✗",
        "warning": "⚠",
        "info": "ℹ"
    }
    print("  {} {}".format(icons.get(status, "•"), message))

# ==================== INITIALISATION ====================

print_step(1, 9, "Initialisation du matériel")

# Pin SET
try:
    pin_set = Pin(GT38_SET_PIN, Pin.OUT)
    pin_set.value(1)  # Démarrer en mode RUN
    print_result("Pin SET (GPIO{}) configurée".format(GT38_SET_PIN), "ok")
except Exception as e:
    print_result("Erreur pin SET: {}".format(e), "error")
    print("\n❌ ARRÊT - Pin SET non fonctionnelle")
    import sys
    sys.exit(1)

# UART
try:
    uart = UART(UART_PORT, 
                baudrate=UART_BAUD,
                tx=Pin(UART_TX_PIN),
                rx=Pin(UART_RX_PIN),
                timeout=200)
    print_result("UART{} initialisé à {} bauds".format(UART_PORT, UART_BAUD), "ok")
    time.sleep_ms(200)
except Exception as e:
    print_result("Erreur UART: {}".format(e), "error")
    print("\n❌ ARRÊT - UART non fonctionnel")
    import sys
    sys.exit(1)

# ==================== MODE CONFIG ====================

print_step(2, 9, "Passage en mode CONFIG")

pin_set.value(0)  # Mode CONFIG
time.sleep(1)
print_result("SET = LOW (mode CONFIG)", "info")

# ==================== TEST CONNEXION ====================

print_step(3, 9, "Test de connexion au GT38")

resp = send_at_command(uart, "AT", delay=300)

if resp and "OK" in resp:
    print_result("Module GT38 répond: {}".format(resp), "ok")
else:
    print_result("Aucune réponse du GT38", "error")
    
    print("\n❌ ÉCHEC - Le GT38 ne répond pas")
    print("\nVérifications à effectuer:")
    print("  1. Câblage:")
    print("     - GPIO{} (TX) → GT38 RXD (croisé !)".format(UART_TX_PIN))
    print("     - GPIO{} (RX) ← GT38 TXD (croisé !)".format(UART_RX_PIN))
    print("     - GPIO{} → GT38 SET".format(GT38_SET_PIN))
    print("  2. Alimentation GT38:")
    print("     - VCC = 3.3V (mesurez avec multimètre)")
    print("     - GND commun avec ESP32")
    print("  3. Module GT38:")
    print("     - LED allumée ?")
    print("     - Module fonctionnel ?")
    
    pin_set.value(1)
    import sys
    sys.exit(1)

# ==================== INFORMATIONS MODULE ====================

print_step(4, 9, "Lecture des informations du module")

# Version
version = send_at_command(uart, "AT+V", delay=400)
if version:
    print_result("Version: {}".format(version.replace('\r\n', ' | ')), "info")
else:
    print_result("Version non disponible", "warning")

# ==================== CONFIGURATION ACTUELLE ====================

print_step(5, 9, "Lecture de la configuration actuelle")

config_resp = send_at_command(uart, "AT+RX", delay=400)

if config_resp:
    print_result("Configuration actuelle:", "info")
    
    lines = config_resp.split('\r\n')
    for line in lines:
        line = line.strip()
        if line and line != "OK":
            print("    • {}".format(line))
    
    # Parser les valeurs importantes
    current_mode = None
    current_baud = None
    current_canal = None
    
    if "FU1" in config_resp:
        current_mode = "FU1"
    elif "FU2" in config_resp:
        current_mode = "FU2 (4800 bauds)"
    elif "FU3" in config_resp:
        current_mode = "FU3 (9600 bauds)"
    elif "FU4" in config_resp:
        current_mode = "FU4 (1200 bauds)"
    
    if "B1200" in config_resp:
        current_baud = "1200"
    elif "B4800" in config_resp:
        current_baud = "4800"
    elif "B9600" in config_resp:
        current_baud = "9600"
    
    # Analyser si configuration correcte
    need_config = False
    
    if current_mode and "FU3" not in current_mode:
        print_result("Mode actuel: {} (doit être FU3)".format(current_mode), "warning")
        need_config = True
    
    if current_baud and current_baud != "9600":
        print_result("Baud actuel: {} (doit être 9600)".format(current_baud), "warning")
        need_config = True
    
    if not need_config:
        print_result("Configuration déjà correcte !", "ok")
else:
    print_result("Impossible de lire la configuration", "error")
    need_config = True

# ==================== NOUVELLE CONFIGURATION ====================

print_step(6, 9, "Application de la nouvelle configuration")

print_result("Configuration cible pour DTD:", "info")
print("    • Canal: 001 (identique au TA)")
print("    • Puissance: 8 = +20dBm (maximum)")
print("    • Mode: FU3 (transparent, 9600 bauds)")

configs = [
    ("AT+C001", "Canal 001"),
    ("AT+P8", "Puissance maximale (+20dBm)"),
    ("AT+FU3", "Mode FU3 (9600 bauds transparent)"),
]

success_count = 0
failed_configs = []

for cmd, description in configs:
    print("\n  Configuration: {}".format(description))
    resp = send_at_command(uart, cmd, delay=400)
    
    if resp and "OK" in resp:
        print_result("{}: {}".format(description, resp), "ok")
        success_count += 1
    else:
        print_result("{}: {} (échec)".format(description, resp if resp else "Pas de réponse"), "error")
        failed_configs.append(description)

# ==================== VÉRIFICATION FINALE ====================

print_step(7, 9, "Vérification de la configuration finale")

final_config = send_at_command(uart, "AT+RX", delay=400)

if final_config:
    print_result("Configuration finale:", "info")
    
    lines = final_config.split('\r\n')
    for line in lines:
        line = line.strip()
        if line and line != "OK":
            print("    • {}".format(line))
    
    # Vérifier que tout est OK
    config_ok = True
    
    if "FU3" not in final_config:
        print_result("Mode FU3 non détecté", "error")
        config_ok = False
    
    if "C001" not in final_config and "C1" not in final_config:
        print_result("Canal 001 non confirmé", "warning")
    
    if "P8" not in final_config and "20dBm" not in final_config:
        print_result("Puissance max non confirmée", "warning")
    
    if config_ok:
        print_result("Configuration vérifiée avec succès !", "ok")
else:
    print_result("Impossible de vérifier la configuration", "warning")

# ==================== RETOUR MODE RUN ====================

print_step(8, 9, "Retour en mode RUN (transparent)")

pin_set.value(1)  # Mode RUN
time.sleep(1)
print_result("SET = HIGH (mode RUN)", "info")
print_result("GT38 prêt pour communication radio", "ok")

# ==================== RÉSUMÉ FINAL ====================

print_step(9, 9, "Résumé de la configuration")

print("\n" + "="*70)

if success_count == len(configs):
    print(" "*20 + "✓✓ CONFIGURATION RÉUSSIE !")
    print("="*70)
    
    print("\n📡 Le GT38 du DD est maintenant configuré:")
    print("  ✓ Canal: 001 (compatible avec TA)")
    print("  ✓ Puissance: +20dBm (portée maximale)")
    print("  ✓ Mode: FU3 (transparent, 9600 bauds)")
    print("  ✓ UART: Port {} à {} bauds".format(UART_PORT, UART_BAUD))
    
    print("\n🎯 Prochaines étapes:")
    print("  1. Uploadez le fichier main.py sur le DD")
    print("  2. Créez config.py avec DETECTOR_ID = \"01\"")
    print("  3. Redémarrez le DD (Ctrl+D)")
    print("  4. Testez la communication avec le TA")
    
    print("\n💡 Test rapide:")
    print("  • Sur TA: Envoyez POLL:01")
    print("  • Sur DD: Devrait répondre ACK:01:1")
    
elif success_count > 0:
    print(" "*15 + "⚠️  CONFIGURATION PARTIELLE")
    print("="*70)
    
    print("\n✓ Configurations réussies: {}/{}".format(success_count, len(configs)))
    
    if failed_configs:
        print("\n✗ Configurations échouées:")
        for config in failed_configs:
            print("  • {}".format(config))
    
    print("\n💡 Recommandation:")
    print("  • Relancez le script de configuration")
    print("  • Ou configurez manuellement en mode CONFIG:")
    for cmd, desc in configs:
        print("    - {} (commande: {})".format(desc, cmd))
    
else:
    print(" "*20 + "❌ CONFIGURATION ÉCHOUÉE")
    print("="*70)
    
    print("\n✗ Aucune configuration n'a réussi")
    print("\n🔧 Actions correctives:")
    print("  1. Vérifiez le câblage (surtout TX/RX croisés)")
    print("  2. Mesurez la tension d'alimentation du GT38")
    print("  3. Testez le GT38 avec un autre système")
    print("  4. Vérifiez que la pin SET fonctionne (GPIO{})".format(GT38_SET_PIN))

print("\n" + "="*70)

print("\n📚 Câblage de référence:")
print("  ESP32 DD          GT38")
print("  ─────────────────────────")
print("  GPIO{:<2} (TX)   →   RXD".format(UART_TX_PIN))
print("  GPIO{:<2} (RX)   ←   TXD".format(UART_RX_PIN))
print("  GPIO{:<2}        →   SET".format(GT38_SET_PIN))
print("  3.3V          →   VCC")
print("  GND           →   GND")

print("\n" + "="*70)
print(" "*25 + "FIN DE LA CONFIGURATION")
print("="*70)