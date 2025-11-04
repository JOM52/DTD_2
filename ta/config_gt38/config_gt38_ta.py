# config_gt38.py
# Script universel pour configurer un GT38 à 1200 bauds
# Compatible DD et TA - Supporte commandes AT courtes et longues
# Version: 2.1 - Correction erreur global

from machine import Pin, UART
import time

# ============== CONFIGURATION (à adapter selon DD/TA) ==============
# Pour TA (Terminal Actif):
#   tx_pin = 17, rx_pin = 18, set_pin_nr = 43, uart_port = 1
# TA
tx_pin = 17
rx_pin = 18
set_pin_nr = 43
uart_port = 1

# Pour DD (Détecteur Distant):
#   tx_pin = 17, rx_pin = 16, set_pin_nr = 5, uart_port = 1
# DD
# tx_pin = 17
# rx_pin = 16
# set_pin_nr = 5
# uart_port = 1

# ============== PARAMÈTRES GT38 ==============
TARGET_BAUDRATE = 1200
TEST_BAUDRATES = [1200, 9600, 115200, 57600, 38400, 19200, 4800, 2400]

# Support des commandes courtes ET longues
USE_SHORT_COMMANDS = True  # True = commandes courtes, False = commandes longues

# ============== CLASSE DE CONFIGURATION ==============

class GT38Config:
    """Classe pour gérer la configuration GT38"""
    
    def __init__(self):
        self.tx_pin = tx_pin
        self.rx_pin = rx_pin
        self.set_pin_nr = set_pin_nr
        self.uart_port = uart_port
        self.target_baudrate = TARGET_BAUDRATE
        self.test_baudrates = TEST_BAUDRATES
        self.use_short_commands = USE_SHORT_COMMANDS
    
    def get_at_command(self, cmd_type):
        """Retourne la commande AT appropriée (courte ou longue)"""
        if self.use_short_commands:
            commands = {
                "test": "AT",
                "set_uart": "AT+U={}",
                "read_uart": "AT+U?",
                "save": "AT+S",
                "reset": "AT+R"
            }
        else:
            commands = {
                "test": "AT",
                "set_uart": "AT+UART={}",
                "read_uart": "AT+UART?",
                "save": "AT+SAVE",
                "reset": "AT+RESET"
            }
        return commands.get(cmd_type, "AT")
    
    def send_at_command(self, uart, command, wait_ms=300):
        """Envoie une commande AT et retourne la réponse"""
        # Vider buffer
        while uart.any():
            uart.read()
        
        # Envoyer commande
        full_cmd = command + "\r\n"
        uart.write(full_cmd.encode())
        print("    → {}".format(command))
        
        # Attendre réponse
        time.sleep_ms(wait_ms)
        response = uart.read()
        
        if response:
            try:
                resp_str = response.decode('utf-8', 'ignore').strip()
                print("    ← {}".format(resp_str))
                return resp_str
            except:
                print("    ← [données binaires]")
                return None
        else:
            print("    ← [pas de réponse]")
            return None
    
    def check_ok_response(self, response):
        """Vérifie si la réponse contient OK"""
        if not response:
            return False
        return 'OK' in response.upper()
    
    def verify_current_baudrate(self):
        """Vérifie le baud rate actuel du GT38"""
        print("\n" + "="*60)
        print("Vérification baud rate actuel")
        print("="*60)
        
        set_pin = Pin(self.set_pin_nr, Pin.OUT)
        set_pin.value(0)  # Mode CONFIG
        time.sleep_ms(200)
        
        for baud in self.test_baudrates:
            print("\nTest @ {} bauds...".format(baud))
            uart = UART(self.uart_port, baudrate=baud, 
                       tx=Pin(self.tx_pin), rx=Pin(self.rx_pin), timeout=300)
            time.sleep_ms(100)
            
            response = self.send_at_command(uart, self.get_at_command("test"), 300)
            
            if self.check_ok_response(response):
                print("  ✓✓✓ GT38 détecté @ {} bauds".format(baud))
                
                # Lire config UART
                self.send_at_command(uart, self.get_at_command("read_uart"), 300)
                
                set_pin.value(1)
                print("\n" + "="*60 + "\n")
                return baud
        
        print("\n✗ Aucun baud rate détecté")
        set_pin.value(1)
        print("="*60 + "\n")
        return None
    
    def configure_to_baudrate(self, target_baud=None):
        """Configure le GT38 au baud rate cible"""
        
        if target_baud is None:
            target_baud = self.target_baudrate
        
        print("\n" + "="*60)
        print("Configuration GT38 à {} bauds".format(target_baud))
        print("Commandes: {}".format("COURTES (AT+U)" if self.use_short_commands else "LONGUES (AT+UART)"))
        print("="*60)
        
        # Init hardware
        set_pin = Pin(self.set_pin_nr, Pin.OUT)
        
        # Détecter baud rate actuel
        print("\n[1/5] Détection du baud rate actuel...")
        current_baud = None
        
        for test_baud in self.test_baudrates:
            print("  Test @ {} bauds...".format(test_baud))
            uart = UART(self.uart_port, baudrate=test_baud, 
                       tx=Pin(self.tx_pin), rx=Pin(self.rx_pin), timeout=500)
            set_pin.value(0)  # Mode CONFIG
            time.sleep_ms(200)
            
            response = self.send_at_command(uart, self.get_at_command("test"), 300)
            
            if self.check_ok_response(response):
                current_baud = test_baud
                print("  ✓✓✓ GT38 détecté @ {} bauds".format(test_baud))
                break
            
            set_pin.value(1)
            time.sleep_ms(100)
        
        if not current_baud:
            print("\n✗ Aucun baud rate détecté")
            print("Vérifier:")
            print("  - Câblage TX/RX (GPIO{}/{})".format(self.tx_pin, self.rx_pin))
            print("  - Alimentation GT38 (3.3V)")
            print("  - Pin SET (GPIO{})".format(self.set_pin_nr))
            set_pin.value(1)
            return False
        
        # Si déjà au bon baud rate
        if current_baud == target_baud:
            print("\n✓ GT38 déjà configuré à {} bauds".format(target_baud))
            print("Aucune action nécessaire")
            set_pin.value(1)
            return True
        
        # Lire configuration actuelle
        print("\n[2/5] Lecture configuration actuelle...")
        uart = UART(self.uart_port, baudrate=current_baud, 
                   tx=Pin(self.tx_pin), rx=Pin(self.rx_pin), timeout=500)
        set_pin.value(0)
        time.sleep_ms(200)
        
        response = self.send_at_command(uart, self.get_at_command("read_uart"), 300)
        if response:
            print("  Configuration actuelle: {}".format(response))
        
        # Reconfigurer à target_baud
        print("\n[3/5] Reconfiguration à {} bauds...".format(target_baud))
        cmd = self.get_at_command("set_uart").format(target_baud)
        response = self.send_at_command(uart, cmd, 300)
        
        if not self.check_ok_response(response):
            print("  ✗ Erreur lors de la reconfiguration")
            print("  Réponse:", response)
            set_pin.value(1)
            return False
        
        print("  ✓ Commande acceptée")
        
        # Sauvegarder
        print("\n[4/5] Sauvegarde en Flash...")
        cmd = self.get_at_command("save")
        response = self.send_at_command(uart, cmd, 300)
        
        if not self.check_ok_response(response):
            print("  ✗ Erreur lors de la sauvegarde")
            print("  Réponse:", response)
            set_pin.value(1)
            return False
        
        print("  ✓ Configuration sauvegardée")
        
        # Vérification au nouveau baud rate
        print("\n[5/5] Vérification @ {} bauds...".format(target_baud))
        uart.init(baudrate=target_baud, timeout=500)
        time.sleep_ms(300)
        
        response = self.send_at_command(uart, self.get_at_command("test"), 300)
        
        set_pin.value(1)  # Retour mode RUN
        
        if self.check_ok_response(response):
            print("  ✓ GT38 répond correctement @ {} bauds".format(target_baud))
            print("\n" + "="*60)
            print("✓✓✓ CONFIGURATION REUSSIE ✓✓✓")
            print("="*60 + "\n")
            return True
        else:
            print("  ✗ Pas de réponse @ {} bauds".format(target_baud))
            print("\n" + "="*60)
            print("✗✗✗ CONFIGURATION ECHOUEE ✗✗✗")
            print("="*60 + "\n")
            return False
    
    def test_communication(self, test_baud=None):
        """Test simple de communication avec le GT38"""
        print("\n" + "="*60)
        print("Test de communication")
        print("="*60)
        
        set_pin = Pin(self.set_pin_nr, Pin.OUT)
        set_pin.value(0)  # Mode CONFIG
        time.sleep_ms(200)
        
        if test_baud:
            bauds_to_test = [test_baud]
        else:
            bauds_to_test = self.test_baudrates
        
        for baud in bauds_to_test:
            print("\n@ {} bauds:".format(baud))
            uart = UART(self.uart_port, baudrate=baud, 
                       tx=Pin(self.tx_pin), rx=Pin(self.rx_pin), timeout=500)
            time.sleep_ms(100)
            
            # Test AT
            response = self.send_at_command(uart, self.get_at_command("test"), 300)
            if self.check_ok_response(response):
                print("  ✓ Communication OK")
                
                # Info supplémentaires
                print("\n  Informations GT38:")
                self.send_at_command(uart, self.get_at_command("read_uart"), 300)
                
                set_pin.value(1)
                return True
            else:
                print("  ✗ Pas de réponse")
        
        set_pin.value(1)
        print("\n✗ Aucune communication établie")
        return False

# Créer instance globale
config = GT38Config()

# ============== FONCTIONS WRAPPER ==============

def verify_current_baudrate():
    """Wrapper pour vérifier baud rate actuel"""
    return config.verify_current_baudrate()

def configure_gt38_to_baudrate(target_baud=None):
    """Wrapper pour configurer GT38"""
    return config.configure_to_baudrate(target_baud)

def test_communication(test_baud=None):
    """Wrapper pour tester communication"""
    return config.test_communication(test_baud)

# ============== MENU INTERACTIF ==============

def menu():
    """Menu interactif"""
    while True:
        print("\n" + "="*60)
        print("Configuration GT38 - Menu Principal")
        print("="*60)
        print("Configuration actuelle:")
        print("  - TX: GPIO{}  RX: GPIO{}  SET: GPIO{}  UART: {}".format(
            config.tx_pin, config.rx_pin, config.set_pin_nr, config.uart_port))
        print("  - Commandes: {}".format("COURTES (AT+U)" if config.use_short_commands else "LONGUES (AT+UART)"))
        print("  - Baud cible: {}".format(config.target_baudrate))
        print("="*60)
        print("1. Vérifier baud rate actuel")
        print("2. Tester communication")
        print("3. Configurer à {} bauds".format(config.target_baudrate))
        print("4. Configurer à un autre baud rate")
        print("5. Changer type de commandes (court/long)")
        print("6. Quitter")
        print("="*60)
        
        try:
            choice = input("Choix (1-6): ").strip()
        except:
            choice = "6"
        
        if choice == "1":
            current = verify_current_baudrate()
            if current:
                print("\n→ GT38 est actuellement à {} bauds".format(current))
            else:
                print("\n→ Impossible de détecter le GT38")
        
        elif choice == "2":
            success = test_communication()
            if not success:
                print("\n→ Vérifier le matériel")
        
        elif choice == "3":
            success = configure_gt38_to_baudrate()
            if success:
                print("\n→ Vous pouvez maintenant modifier votre code:")
                print("   UART_BAUD = {}".format(config.target_baudrate))
            else:
                print("\n→ Configuration échouée. Vérifier matériel.")
        
        elif choice == "4":
            try:
                custom_baud = int(input("Baud rate souhaité (1200-115200): ").strip())
                if custom_baud < 1200 or custom_baud > 115200:
                    print("Baud rate hors limites")
                else:
                    success = configure_gt38_to_baudrate(custom_baud)
                    if success:
                        print("\n→ Configuration réussie à {} bauds".format(custom_baud))
            except:
                print("Valeur invalide")
        
        elif choice == "5":
            config.use_short_commands = not config.use_short_commands
            print("\n→ Type de commandes changé: {}".format(
                "COURTES (AT+U)" if config.use_short_commands else "LONGUES (AT+UART)"))
        
        elif choice == "6":
            print("\nAu revoir!")
            break
        
        else:
            print("\nChoix invalide")

# ============== EXECUTION PRINCIPALE ==============

def auto_configure():
    """Configuration automatique (détection + config si nécessaire)"""
    print("""
╔════════════════════════════════════════════════════════════╗
║  Configuration GT38 - Version 2.1                          ║
║  Support commandes courtes (AT+U) et longues (AT+UART)     ║
╚════════════════════════════════════════════════════════════╝

Configuration actuelle:
  - TX: GPIO{}  RX: GPIO{}  SET: GPIO{}
  - UART Port: {}
  - Commandes: {}
  - Baud cible: {}

Ce script va:
1. Détecter le baud rate actuel du GT38
2. Le reconfigurer à {} bauds si nécessaire
3. Vérifier la nouvelle configuration

Assurez-vous que:
✓ GT38 est alimenté (3.3V stable)
✓ Câblage correct (TX, RX, SET)
✓ Pin SET fonctionne (peut basculer 0/1)
""".format(
        config.tx_pin, config.rx_pin, config.set_pin_nr, config.uart_port,
        "COURTES (AT+U)" if config.use_short_commands else "LONGUES (AT+UART)",
        config.target_baudrate, config.target_baudrate
    ))
    
    try:
        input("Appuyez sur Entrée pour continuer (Ctrl+C pour annuler)...")
    except:
        print("\nAnnulé")
        return
    
    # Vérifier d'abord
    current = verify_current_baudrate()
    
    if current == config.target_baudrate:
        print("\n✓ GT38 déjà configuré à {} bauds".format(config.target_baudrate))
        print("Aucune action nécessaire")
    elif current:
        print("\n→ GT38 actuellement @ {} bauds".format(current))
        try:
            response = input("Configurer à {} bauds ? (o/n): ".format(config.target_baudrate)).strip().lower()
        except:
            response = 'o'
        
        if response == 'o':
            configure_gt38_to_baudrate()
    else:
        print("\n✗ GT38 non détecté")
        print("Vérifier matériel avant de continuer")
        print("\nVoulez-vous tester la communication ?")
        try:
            response = input("(o/n): ").strip().lower()
        except:
            response = 'n'
        
        if response == 'o':
            test_communication()

# Point d'entrée
if __name__ == "__main__":
    auto_configure()

# Pour lancer le menu interactif:
# >>> import config_gt38
# >>> config_gt38.menu()