# config_gt38_1200.py
# Script pour configurer un GT38 à 1200 bauds
# À exécuter sur chaque DD via REPL

from machine import Pin, UART
import time

def configure_gt38_to_1200():
    """Configure le GT38 local à 1200 bauds"""
    
    print("\n" + "="*50)
    print("Configuration GT38 à 1200 bauds")
    print("="*50)
    
    # Init hardware
    set_pin = Pin(43, Pin.OUT)
    
    # Tester d'abord à 9600 bauds
    print("\n[1/4] Test communication @ 9600 bauds...")
    uart = UART(1, baudrate=9600, tx=Pin(17), rx=Pin(18), timeout=500)
    set_pin.value(0)  # Mode CONFIG
    time.sleep_ms(200)
    
    # Vider buffer
    while uart.any():
        uart.read()
    
    # Test AT
    uart.write(b'AT\r\n')
    time.sleep_ms(300)
    response = uart.read()
    
    if response and b'OK' in response:
        print("      ✓ GT38 répond @ 9600 bauds")
        
        # Reconfigurer à 1200
        print("\n[2/4] Envoi commande AT+U=1200...")
        uart.write(b'AT+U=1200\r\n')
        time.sleep_ms(300)
        response = uart.read()
        
        if response and b'OK' in response:
            print("      ✓ Commande acceptée")
            
            # Sauvegarder
            print("\n[3/4] Sauvegarde configuration...")
            uart.write(b'AT+S\r\n')
            time.sleep_ms(300)
            response = uart.read()
            
            if response and b'OK' in response:
                print("      ✓ Configuration sauvegardée en Flash")
            else:
                print("      ✗ Erreur sauvegarde")
                print("      Réponse:", response)
                set_pin.value(1)
                return False
        else:
            print("      ✗ Erreur commande UART")
            print("      Réponse:", response)
            set_pin.value(1)
            return False
    else:
        print("      ✗ Pas de réponse @ 9600 bauds")
        print("      Test si déjà configuré à 1200...")
        
        # Peut-être déjà à 1200 ?
        uart.init(baudrate=1200, timeout=500)
        time.sleep_ms(200)
        
        while uart.any():
            uart.read()
        
        uart.write(b'AT\r\n')
        time.sleep_ms(300)
        response = uart.read()
        
        if response and b'OK' in response:
            print("      ✓ GT38 déjà configuré à 1200 bauds")
            set_pin.value(1)
            print("\n" + "="*50)
            print("GT38 déjà à 1200 bauds - Aucune action")
            print("="*50 + "\n")
            return True
        else:
            print("      ✗ Aucune réponse à aucun baud rate")
            print("      Vérifier:")
            print("        - Câblage TX/RX (GPIO17/16)")
            print("        - Alimentation GT38 (3.3V)")
            print("        - Pin SET (GPIO5)")
            set_pin.value(1)
            return False
    
    # Vérification @ 1200
    print("\n[4/4] Vérification @ 1200 bauds...")
    uart.init(baudrate=1200, timeout=500)
    time.sleep_ms(200)
    
    while uart.any():
        uart.read()
    
    uart.write(b'AT\r\n')
    time.sleep_ms(300)
    response = uart.read()
    
    set_pin.value(1)  # Retour mode RUN
    
    if response and b'OK' in response:
        print("      ✓ GT38 répond correctement @ 1200 bauds")
        print("\n" + "="*50)
        print("✓✓✓ CONFIGURATION REUSSIE ✓✓✓")
        print("="*50 + "\n")
        return True
    else:
        print("      ✗ Pas de réponse @ 1200 bauds")
        print("      Réponse:", response)
        print("\n" + "="*50)
        print("✗✗✗ CONFIGURATION ECHOUEE ✗✗✗")
        print("="*50 + "\n")
        return False

def verify_current_baudrate():
    """Vérifie le baud rate actuel du GT38"""
    print("\n" + "="*50)
    print("Vérification baud rate actuel")
    print("="*50)
    
    set_pin = Pin(43, Pin.OUT)
    set_pin.value(0)  # Mode CONFIG
    time.sleep_ms(200)
    
    baud_rates = [1200, 9600, 115200, 57600, 38400, 19200, 4800, 2400]
    
    for baud in baud_rates:
        print("\nTest @ {} bauds...".format(baud))
        uart = UART(1, baudrate=baud, tx=Pin(17), rx=Pin(18), timeout=300)
        time.sleep_ms(100)
        
        # Vider buffer
        while uart.any():
            uart.read()
        
        uart.write(b'AT\r\n')
        time.sleep_ms(300)
        response = uart.read()
        
        if response and b'OK' in response:
            print("  ✓✓✓ GT38 détecté @ {} bauds".format(baud))
            set_pin.value(1)
            print("\n" + "="*50 + "\n")
            return baud
    
    print("\n✗ Aucun baud rate détecté")
    set_pin.value(1)
    print("="*50 + "\n")
    return None

# Menu interactif
def menu():
    """Menu interactif"""
    while True:
        print("\n" + "="*50)
        print("Configuration GT38 - Menu")
        print("="*50)
        print("1. Vérifier baud rate actuel")
        print("2. Configurer à 1200 bauds")
        print("3. Quitter")
        print("="*50)
        
        choice = input("Choix (1-3): ").strip()
        
        if choice == "1":
            current = verify_current_baudrate()
            if current:
                print("GT38 est actuellement à {} bauds".format(current))
            else:
                print("Impossible de détecter le GT38")
        
        elif choice == "2":
            success = configure_gt38_to_1200()
            if success:
                print("Vous pouvez maintenant modifier dd_main.py:")
                print("  UART_BAUD = 1200")
            else:
                print("Configuration échouée. Vérifier matériel.")
        
        elif choice == "3":
            print("\nAu revoir!")
            break
        
        else:
            print("\nChoix invalide")

# Exécution automatique si lancé directement
if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════╗
║  Configuration GT38 à 1200 Bauds                   ║
║  Pour DD (Détecteur Distant) v1.5                  ║
╚════════════════════════════════════════════════════╝

Ce script va:
1. Détecter le baud rate actuel du GT38
2. Le reconfigurer à 1200 bauds
3. Vérifier la nouvelle configuration

Assurez-vous que:
- GT38 est alimenté (3.3V)
- Câblage correct (TX=GPIO17, RX=GPIO16, SET=GPIO5)
- Pin SET fonctionne

""")
    
    input("Appuyez sur Entrée pour continuer...")
    
    # Vérifier d'abord
    current = verify_current_baudrate()
    
    if current == 1200:
        print("\n✓ GT38 déjà configuré à 1200 bauds")
        print("Aucune action nécessaire")
    elif current:
        print("\nGT38 actuellement @ {} bauds".format(current))
        response = input("Configurer à 1200 bauds ? (o/n): ").strip().lower()
        if response == 'o':
            configure_gt38_to_1200()
    else:
        print("\n✗ GT38 non détecté")
        print("Vérifier matériel avant de continuer")
