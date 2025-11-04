# boot.py - Démarrage automatique DD avec possibilité d'interruption
# Version : 1.0
# 
# Ce fichier est exécuté automatiquement au démarrage de l'ESP32
# Il offre un délai pour permettre l'interruption (Ctrl+C) avant
# de lancer automatiquement dd_main.py

import sys
import time
from machine import Pin

# ============================ CONFIG ============================
AUTO_START_ENABLED = True    # True pour démarrage auto, False pour debug
INTERRUPT_DELAY_MS = 3000    # 3 secondes pour appuyer sur Ctrl+C
LED_PIN = 2                  # LED pour feedback visuel
BLINK_FAST_MS = 100         # Clignotement rapide pendant délai
MAIN_SCRIPT = "dd_main"      # Script à lancer (sans .py)

# ======================== INITIALISATION ========================
print("\n" + "="*60)
print("BOOT DD - Démarrage automatique avec délai d'interruption")
print("="*60)

# LED pour feedback visuel
try:
    led = Pin(LED_PIN, Pin.OUT)
    led_available = True
except:
    led_available = False
    print("[BOOT] LED non disponible")

def led_blink(times, on_ms=100, off_ms=100):
    """Clignotement LED"""
    if not led_available:
        return
    for _ in range(times):
        led.value(1)
        time.sleep_ms(on_ms)
        led.value(0)
        time.sleep_ms(off_ms)

def led_pattern_waiting():
    """Pattern LED: en attente d'interruption"""
    if led_available:
        led.value(1)
        time.sleep_ms(50)
        led.value(0)

def led_pattern_starting():
    """Pattern LED: démarrage en cours"""
    led_blink(3, 200, 100)

def led_pattern_interrupted():
    """Pattern LED: interrompu par utilisateur"""
    led_blink(5, 50, 50)

# ==================== FONCTION DÉMARRAGE AUTO ===================
def auto_start():
    """Lance le script principal après délai d'interruption"""
    
    print("\n[BOOT] Démarrage automatique activé")
    print("[BOOT] Appuyez sur Ctrl+C dans les {}s pour interrompre".format(
        INTERRUPT_DELAY_MS // 1000))
    print("[BOOT] LED clignote pendant le délai...\n")
    
    # Délai avec possibilité d'interruption
    start_time = time.ticks_ms()
    interrupted = False
    
    try:
        # Boucle de délai avec clignotement LED
        while time.ticks_diff(time.ticks_ms(), start_time) < INTERRUPT_DELAY_MS:
            # Pattern LED
            led_pattern_waiting()
            
            # Afficher progression tous les 500ms
            elapsed = time.ticks_diff(time.ticks_ms(), start_time)
            if elapsed % 500 < 50:  # Toutes les 500ms
                remaining = (INTERRUPT_DELAY_MS - elapsed) // 1000 + 1
                sys.stdout.write("\r[BOOT] Démarrage dans {}s... (Ctrl+C pour annuler)  ".format(
                    remaining))
            
            time.sleep_ms(50)
        
        print("\r[BOOT] Délai écoulé - Lancement du script principal...          ")
        
    except KeyboardInterrupt:
        # Ctrl+C pressé
        interrupted = True
        print("\n\n[BOOT] *** INTERROMPU PAR UTILISATEUR ***")
        led_pattern_interrupted()
        
        print("[BOOT] Démarrage automatique annulé")
        print("[BOOT] Vous êtes maintenant en mode REPL")
        print("[BOOT] Pour lancer manuellement: import dd_main")
        print("="*60 + "\n")
        
        if led_available:
            led.value(0)
        
        return False
    
    # Si pas interrompu, lancer le script
    if not interrupted:
        led_pattern_starting()
        print("[BOOT] Lancement de {}...".format(MAIN_SCRIPT))
        print("="*60 + "\n")
        
        try:
            # Import et exécution du script principal
            __import__(MAIN_SCRIPT)
            return True
            
        except Exception as e:
            print("\n[BOOT] ERREUR lors du lancement de {}:".format(MAIN_SCRIPT))
            print("[BOOT] {}".format(e))
            
            # Afficher traceback complet
            sys.print_exception(e)
            
            print("\n[BOOT] Le script n'a pas pu démarrer")
            print("[BOOT] Vous êtes en mode REPL pour debug")
            print("="*60 + "\n")
            
            # Clignotement erreur
            led_blink(10, 100, 100)
            if led_available:
                led.value(0)
            
            return False
    
    return False

# ==================== FONCTION INFO SYSTÈME ====================
def print_system_info():
    """Affiche informations système"""
    import os
    
    print("\n[BOOT] Informations système:")
    
    # Version MicroPython
    print("[BOOT]   MicroPython: {}".format(sys.version))
    
    # Fichiers présents
    try:
        files = os.listdir()
        print("[BOOT]   Fichiers racine: {}".format(", ".join(files)))
        
        # Vérifier présence des fichiers essentiels
        essential_files = ["dd_main.py", "config.py"]
        for f in essential_files:
            if f in files:
                print("[BOOT]   ✓ {} présent".format(f))
            else:
                print("[BOOT]   ✗ {} MANQUANT".format(f))
                
    except Exception as e:
        print("[BOOT]   Erreur listage fichiers: {}".format(e))
    
    # Mémoire
    try:
        import gc
        gc.collect()
        print("[BOOT]   Mémoire libre: {} bytes".format(gc.mem_free()))
    except:
        pass
    
    print()

# ====================== POINT D'ENTRÉE ==========================

# Afficher info système
print_system_info()

# Vérifier si auto-start activé
if AUTO_START_ENABLED:
    # Lancer avec délai d'interruption
    auto_start()
else:
    print("[BOOT] Démarrage automatique DÉSACTIVÉ")
    print("[BOOT] Mode debug - Vous êtes en mode REPL")
    print("[BOOT] Pour lancer manuellement: import dd_main")
    print("="*60 + "\n")
    
    # Clignotement court pour indiquer mode debug
    led_blink(2, 100, 100)
    if led_available:
        led.value(0)

# Note: Si auto_start() lance dd_main avec succès, le script dd_main
# prend le contrôle et cette partie du code n'est plus exécutée.
# Si interrompu ou erreur, on reste en mode REPL.