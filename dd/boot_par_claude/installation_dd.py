# installation_dd.py - Script d'installation complète d'un DD
# À exécuter dans Thonny pour installer boot.py + dd_main.py + config.py
# Version: 1.0

"""
Ce script facilite l'installation complète d'un détecteur distant (DD).

Usage:
1. Connecter ESP32 via USB
2. Dans Thonny: File > Open > installation_dd.py
3. Exécuter (F5)
4. Suivre les instructions
"""

import os
import time
import machine

def print_header(title):
    """Affiche un en-tête"""
    print("\n" + "="*60)
    print(title)
    print("="*60)

def print_step(step, description):
    """Affiche une étape"""
    print("\n[{}] {}".format(step, description))

def check_file_exists(filename):
    """Vérifie si un fichier existe"""
    try:
        files = os.listdir()
        return filename in files
    except:
        return False

def list_files():
    """Liste les fichiers présents"""
    try:
        files = os.listdir()
        print("Fichiers présents: {}".format(", ".join(files)))
        return files
    except Exception as e:
        print("Erreur: {}".format(e))
        return []

def verify_installation():
    """Vérifie que tous les fichiers sont présents"""
    print_header("VÉRIFICATION INSTALLATION")
    
    required_files = {
        "boot.py": "Démarrage automatique",
        "dd_main.py": "Script principal DD",
        "config.py": "Configuration ID détecteur"
    }
    
    all_ok = True
    
    for filename, description in required_files.items():
        exists = check_file_exists(filename)
        status = "✓ OK" if exists else "✗ MANQUANT"
        print("[{}] {} - {}".format(status, filename, description))
        
        if not exists:
            all_ok = False
    
    return all_ok

def show_config():
    """Affiche la configuration actuelle"""
    print_header("CONFIGURATION ACTUELLE")
    
    try:
        import config
        detector_id = getattr(config, "DETECTOR_ID", "NON DÉFINI")
        print("DETECTOR_ID = '{}'".format(detector_id))
        
        if detector_id == "NON DÉFINI":
            print("\n⚠️  ATTENTION: DETECTOR_ID non défini dans config.py")
            return False
        
        return True
        
    except ImportError:
        print("⚠️  ERREUR: config.py non trouvé ou invalide")
        return False
    except Exception as e:
        print("⚠️  ERREUR: {}".format(e))
        return False

def test_dd_import():
    """Test l'import de dd_main"""
    print_header("TEST IMPORT DD_MAIN")
    
    print("Tentative d'import de dd_main...")
    print("(Utilisez Ctrl+C pour interrompre si nécessaire)\n")
    
    try:
        # Note: Ceci va lancer dd_main.py
        # Il faudra Ctrl+C pour l'arrêter
        import dd_main
        return True
    except Exception as e:
        print("\n⚠️  ERREUR lors de l'import:")
        print(str(e))
        import sys
        sys.print_exception(e)
        return False

def create_default_config(detector_id="01"):
    """Crée un config.py par défaut"""
    content = '# config.py\nDETECTOR_ID = "{}"\n'.format(detector_id)
    
    try:
        with open("config.py", "w") as f:
            f.write(content)
        print("✓ config.py créé avec DETECTOR_ID = '{}'".format(detector_id))
        return True
    except Exception as e:
        print("✗ Erreur création config.py: {}".format(e))
        return False

def show_memory_info():
    """Affiche info mémoire"""
    try:
        import gc
        gc.collect()
        free = gc.mem_free()
        print("Mémoire libre: {} bytes ({:.1f} KB)".format(free, free/1024))
    except:
        pass

def interactive_setup():
    """Setup interactif"""
    print_header("INSTALLATION INTERACTIVE DD")
    
    print("\nCe script va vous guider pour installer un détecteur distant.")
    print("Assurez-vous que l'ESP32 est connecté via USB.")
    
    # Étape 1: Vérifier fichiers présents
    print_step("1/5", "Vérification des fichiers")
    time.sleep(1)
    
    files = list_files()
    
    # Étape 2: Vérifier/créer config.py
    print_step("2/5", "Configuration DETECTOR_ID")
    
    if not check_file_exists("config.py"):
        print("\n⚠️  config.py n'existe pas")
        response = input("Voulez-vous créer config.py ? (o/n): ")
        
        if response.lower() == 'o':
            det_id = input("Entrez l'ID du détecteur (01-05): ")
            if create_default_config(det_id):
                print("✓ config.py créé")
            else:
                print("✗ Échec création config.py")
                return
        else:
            print("Installation annulée - config.py requis")
            return
    else:
        show_config()
    
    # Étape 3: Vérifier boot.py
    print_step("3/5", "Vérification boot.py")
    
    if not check_file_exists("boot.py"):
        print("\n⚠️  boot.py n'existe pas")
        print("Vous devez copier boot.py manuellement dans Thonny")
        print("(File > Open > boot.py puis Save as sur l'ESP32)")
    else:
        print("✓ boot.py présent")
    
    # Étape 4: Vérifier dd_main.py
    print_step("4/5", "Vérification dd_main.py")
    
    if not check_file_exists("dd_main.py"):
        print("\n⚠️  dd_main.py n'existe pas")
        print("Vous devez copier dd_main.py manuellement dans Thonny")
    else:
        print("✓ dd_main.py présent")
    
    # Étape 5: Résumé
    print_step("5/5", "Résumé installation")
    
    all_ok = verify_installation()
    show_memory_info()
    
    if all_ok:
        print("\n✓ ✓ ✓ INSTALLATION COMPLÈTE ✓ ✓ ✓")
        print("\nVous pouvez maintenant:")
        print("1. Tester avec: import dd_main")
        print("2. Ou faire un reset: machine.reset()")
        print("   (auto-start après 3s, Ctrl+C pour interrompre)")
    else:
        print("\n⚠️  INSTALLATION INCOMPLÈTE")
        print("Veuillez copier les fichiers manquants")

def quick_check():
    """Vérification rapide"""
    print_header("VÉRIFICATION RAPIDE DD")
    
    print("\nFichiers:")
    list_files()
    
    print("\nInstallation:")
    all_ok = verify_installation()
    
    print("\nConfiguration:")
    config_ok = show_config()
    
    print("\nMémoire:")
    show_memory_info()
    
    if all_ok and config_ok:
        print("\n✓ Système OK - Prêt à démarrer")
    else:
        print("\n⚠️  Problèmes détectés")

# ====================== MENU PRINCIPAL ==========================

def main():
    """Menu principal"""
    print_header("INSTALLATION DD - Menu Principal")
    
    print("\nOptions:")
    print("1. Installation interactive (guidée)")
    print("2. Vérification rapide")
    print("3. Test import dd_main")
    print("4. Créer config.py")
    print("5. Lister fichiers")
    print("6. Reset ESP32")
    print("q. Quitter")
    
    choice = input("\nVotre choix: ")
    
    if choice == "1":
        interactive_setup()
    elif choice == "2":
        quick_check()
    elif choice == "3":
        test_dd_import()
    elif choice == "4":
        det_id = input("ID détecteur (01-05): ")
        create_default_config(det_id)
    elif choice == "5":
        list_files()
    elif choice == "6":
        print("\nReset dans 2 secondes...")
        time.sleep(2)
        machine.reset()
    elif choice.lower() == "q":
        print("Au revoir!")
    else:
        print("Choix invalide")

# Point d'entrée
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrompu par utilisateur")
    except Exception as e:
        print("\nErreur: {}".format(e))
        import sys
        sys.print_exception(e)

# Si exécuté directement, lancer menu
print("\n" + "="*60)
print("Script d'installation DD chargé")
print("="*60)
print("\nPour utiliser:")
print("  >>> main()              # Menu interactif")
print("  >>> quick_check()       # Vérification rapide")
print("  >>> verify_installation() # Vérifier fichiers")
print("  >>> show_config()       # Voir config actuelle")
print("="*60 + "\n")
