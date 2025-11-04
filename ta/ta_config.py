"""
project : DTD
file: ta_config.py

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/JOM52/esp32-dtd

v1.0.0 : 22.10.2025 --> first prototype
v1.0.1 : 23.10.2025 --> add radio/uart pins for GT38 + board/display metadata
v2.0.0 : 24.10.2025 --> improved config with validation and power management
v2.1.0 : 03.11.2025 --> corrections timing UART et radio
    - UART timeout: 10ms → 100ms
    - POLL_PERIOD_MS: 500ms → 800ms
    - REPLY_TIMEOUT_MS: 250ms → 500ms
    - Ajout validation cohérence timeouts
"""

import st7789
APP_VERSION = "1.0.0"
APP_NAME = "DTD"

__app_name__   = "DTD"
__version_no__ = "2.1.0"
__version_date__ = "03.11.2025"

# ---------------------------------------------------------------------------
# Matériel / carte / écran
# ---------------------------------------------------------------------------
HARDWARE = {
    # Carte et affichage (T-Display-S3 IPS/AMOLED -> 320x170)
    "BOARD_NAME": "LilyGO T-Display-S3",
    "DISPLAY_MODEL": "T-Display-S3-320x170",
    "DISPLAY": {
        "DRIVER": "st7789",
        "LANDSCAPE": True,     # True = 320x170 en paysage, False = portrait
        "WIDTH": 320,
        "HEIGHT": 170,
    },

    # Brochage UART dédié à la radio GT38 (connecteur latéral TX/RX)
    # GT38: TXD -> ESP32 RX (GPIO18), RXD -> ESP32 TX (GPIO17), SET -> GPIO43
    "UART_RADIO": {
        "INDEX": 2,           # UART2
        "BAUD": 9600,         # 9600 bauds (utilisé dans le code maintenant)
        "TX": 17,             # ESP32 TX -> GT38 RXD
        "RX": 18,             # ESP32 RX <- GT38 TXD
        # Broche de contrôle SET du GT38 (haut = fonctionnement, bas = config)
        "PIN_GT38_SET": 43,
        "TIMEOUT_MS": 100,    # 100ms (était 10ms - corrigé pour fiabilité)
    },

    # Pins des boutons
    "BUTTONS": {
        "PIN_UP": 14,
        "PIN_DOWN": 0,
    },

    # Alimentation radio (rappel uniquement, pour documentation)
    "RADIO_POWER": {
        "VCC": "3V3",
        "GND": "GND",
    },
}

# ---------------------------------------------------------------------------
# Paramètres globaux
# ---------------------------------------------------------------------------
MAIN = {
    "APP_NAME": __app_name__,
    "VERSION_NO": __version_no__,
    "VERSION_DATE": __version_date__,
    
    # Mode debug
    "DEBUG_MODE": True,        # Active logs détaillés et métriques
    "TEST_FAULTS": False,       # Injecteur de pannes pour tests
    
    # Watchdog
    "WATCHDOG_ENABLED": False,   # Active le watchdog timer
    "WATCHDOG_TIMEOUT_MS": 30000,  # Timeout avant redémarrage (30s)
}

# ---------------------------------------------------------------------------
# UI / Mise en page
# ---------------------------------------------------------------------------
UI = {
    "PAD": 2,
    "HEADER_H": 22,
    "CONTENT_GAP": 8,
    "FOOTER_H": 18,
    "STATUS_BAR_H": 20,
    "STATUS_BAR_GAP": 4,
    "IND_H": 10,
    "WIDTH": 320,
    "HEIGHT": 170,
    
    # Rafraîchissement
    "REFRESH_RATE_MS": 100,     # Période de rafraîchissement UI
    "DIRTY_TRACKING": True,     # Active l'optimisation dirty tracking
    "ROTATION": 1,              # rotation en paysage

    "WIDTH": 320,           # Largeur en mode paysage
    "HEIGHT": 170,          # Hauteur en mode paysage
    "ROTATION": 1,          # Rotation (1 ou 3 pour paysage)
    "DIRTY_TRACKING": True, # Activer le suivi des modifications
    
    # Hauteurs des zones (en pixels)
    "ZONE_TITLE_HEIGHT": 40,      # Titre en haut
    "ZONE_BARS_HEIGHT": 40,       # Barres de statut DD
    "ZONE_LABELS_HEIGHT": 18,     # Noms des DD
    "ZONE_LOG_HEIGHT": 60,        # Zone de log en bas (augmentée)
    
    # Marges et espacements
    "MARGIN_LEFT": 10,
    "MARGIN_RIGHT": 10,
    "BAR_SPACING": 5,

}

COLORS = {
    "C_BLACK": st7789.BLACK,
    "C_WHITE": st7789.WHITE,
    "C_BG":    st7789.color565(0, 0, 0),
    "C_HDR":   st7789.color565(0, 64, 200),
    "C_STS":   st7789.color565(200, 200, 0),
    "C_ERR":   st7789.color565(255, 0, 0),
    "C_WARN":  st7789.color565(255, 160, 0),
    "C_ON":    st7789.color565(0, 200, 0),
    "C_OFF":   st7789.color565(200, 0, 0),
    "C_UNK":   st7789.color565(120, 120, 120),
    "C_BOX":   st7789.color565(60, 60, 60),
    "C_PGR":   st7789.color565(255, 127, 0),
}

TEXTS = {
    "HEADER_TITLE": "DTD-TAC",
    "FOOTER_LEFT":  "▼ long = test | ▲ court = suivant",
    "FOOTER_RIGHT": "v2.1",
}

BUTTONS = {
    # Index logiques
    "BTN_UP": 0,
    "BTN_DOWN": 1,
    "LONG_MS": 800,
    "DEBOUNCE_MS": 50,
}

# ---------------------------------------------------------------------------
# Radio / Simulation et états
# ---------------------------------------------------------------------------
RADIO = {
    # La source de vérité pour la simulation
    "SIMULATE": False,

    # Groupes testés
    "GROUP_IDS": [1, 2, 3, 4, 5,],

    # Temporisations (CORRIGÉES pour fiabilité)
    "POLL_PERIOD_MS": 800,      # 800ms (était 500ms - éviter saturation)
    "REPLY_TIMEOUT_MS": 500,    # 500ms (était 250ms - GT38 peut être lent)

    # Retry configuration
    "RETRY": {
        "MAX_RETRIES": 3,
        "TIMEOUT_BASE_MS": 500,
        "TIMEOUT_MULTIPLIER": 1.5,
        "BACKOFF_ENABLED": True,
        "BACKOFF_MS": 100,
    },

    # Simulation
    "RNG_SEED": 12345,

    # États normalisés
    "STATE_UNKNOWN": 0,
    "STATE_PRESENT": 1,
    "STATE_ABSENT": 2,

    # Mappage (pour UI/legend)
    "STATUS_LABELS": {
        "OK": "OK",
        "OFF": "ERR",
        "UNKNOWN": "DIM",
        "TESTING": "TESTING",
    },

    # Encodage de base des trames (facultatif pour préparer la suite)
    "FRAME": {
        "START_BYTE": 0xA5,
        "END_BYTE": 0x5A,
        "PROTO_VER": 0x01,
        "MAX_LEN": 16,
        # IDs pseudo par défaut pour DTD 1..5
        "DEFAULT_DEVICE_IDS": [0x1FA1, 0x2FB2, 0x3FC3, 0x4FD4, 0x5FE5],
    },
    
    # Statistiques
    "STATS_ENABLED": True,
}

APP = {
    "HEARTBEAT_MS": 750,
    "AUTO_BRIGHTNESS": 100,
    
    # Gestion d'énergie
    "POWER": {
        "SLEEP_ENABLED": False,           # Active mode veille
        "SLEEP_TIMEOUT_MS": 60000,        # Délai avant veille (1 min)
        "SLEEP_DURATION_MS": 5000,        # Durée du sleep (5s)
        "CPU_FREQ_NORMAL": 160000000,     # 160MHz normal
        "CPU_FREQ_HIGH": 240000000,       # 240MHz performance
        "CPU_FREQ_LOW": 80000000,         # 80MHz économie
    },
}

# ---------------------------------------------------------------------------
# Persistance
# ---------------------------------------------------------------------------
PERSIST = {
    "ENABLED": True,
    "CONFIG_FILE": "/config.json",
    "AUTO_SAVE": True,
    "SAVE_INTERVAL_MS": 30000,  # Sauvegarde toutes les 30s si modifié
}

# Configuration logger
LOGGER = {
    "LEVEL": "INFO",
}

# ---------------------------------------------------------------------------
# Validation de la configuration
# ---------------------------------------------------------------------------
class ConfigValidator:
    """Validateur de configuration au démarrage"""
    
    @staticmethod
    def validate():
        """
        Valide la configuration et retourne la liste des erreurs.
        
        Returns:
            list: Liste des erreurs trouvées (vide si OK)
        """
        errors = []
        
        # Vérifier les pins GPIO
        uart_cfg = HARDWARE["UART_RADIO"]
        if uart_cfg["TX"] == uart_cfg["RX"]:
            errors.append("UART: TX et RX identiques (TX={}, RX={})".format(
                uart_cfg["TX"], uart_cfg["RX"]))
        
        # Vérifier les pins boutons
        btn_cfg = HARDWARE["BUTTONS"]
        if btn_cfg["PIN_UP"] == btn_cfg["PIN_DOWN"]:
            errors.append("Buttons: PIN_UP et PIN_DOWN identiques")
        
        # Vérifier les timeouts (NOUVEAU - cohérence UART/Radio)
        uart_timeout = uart_cfg.get("TIMEOUT_MS", 100)
        reply_timeout = RADIO["REPLY_TIMEOUT_MS"]
        poll_period = RADIO["POLL_PERIOD_MS"]
        
        # UART timeout doit être < REPLY_TIMEOUT
        if uart_timeout >= reply_timeout:
            errors.append("Radio: UART_TIMEOUT ({}) >= REPLY_TIMEOUT ({})".format(
                uart_timeout, reply_timeout))
        
        # REPLY_TIMEOUT doit être < POLL_PERIOD
        if reply_timeout >= poll_period:
            errors.append("Radio: REPLY_TIMEOUT ({}) >= POLL_PERIOD ({})".format(
                reply_timeout, poll_period))
        
        # Vérifier minimum timeout UART (doit être >= 50ms pour 9600 bauds)
        if uart_timeout < 50:
            errors.append("Radio: UART_TIMEOUT trop court ({}ms, min 50ms à 9600 bauds)".format(
                uart_timeout))
        
        # Vérifier les GROUP_IDs
        if not RADIO["GROUP_IDS"]:
            errors.append("Radio: GROUP_IDS est vide")
        
        if len(RADIO["GROUP_IDS"]) > 10:
            errors.append("Radio: Trop de GROUP_IDS ({}, max 10)".format(
                len(RADIO["GROUP_IDS"])))
        
        # Vérifier dimensions écran
        disp = HARDWARE["DISPLAY"]
        if disp["WIDTH"] <= 0 or disp["HEIGHT"] <= 0:
            errors.append("Display: Dimensions invalides ({}x{})".format(
                disp["WIDTH"], disp["HEIGHT"]))
        
        # Vérifier retry config
        retry = RADIO["RETRY"]
        if retry["MAX_RETRIES"] < 1:
            errors.append("Radio: MAX_RETRIES doit être >= 1")
        
        if retry["TIMEOUT_BASE_MS"] < 100:
            errors.append("Radio: TIMEOUT_BASE_MS trop court (<100ms)")
        
        # Vérifier watchdog
        if MAIN["WATCHDOG_ENABLED"] and MAIN["WATCHDOG_TIMEOUT_MS"] < 5000:
            errors.append("Watchdog: Timeout trop court (<5s)")
        
        return errors
    
    @staticmethod
    def validate_or_exit():
        """Valide la config et quitte si erreurs critiques"""
        errors = ConfigValidator.validate()
        if errors:
            print("\n" + "="*60)
            print("ERREURS DE CONFIGURATION DÉTECTÉES:")
            print("="*60)
            for i, err in enumerate(errors, 1):
                print("{}. {}".format(i, err))
            print("="*60)
            print("Veuillez corriger ta_config.py avant de continuer.\n")
            
            # Décider si on continue ou non
            critical_keywords = ["identiques", "vide", "invalides"]
            has_critical = any(kw in err.lower() for err in errors for kw in critical_keywords)
            
            if has_critical:
                print("ERREUR CRITIQUE: Arrêt de l'application.")
                import sys
                sys.exit(1)
            else:
                print("AVERTISSEMENT: L'application va continuer avec des valeurs potentiellement incorrectes.")
        else:
            print("[config] Validation OK: configuration valide")


# Valider au chargement du module (peut être désactivé si nécessaire)
if __name__ != "__main__":
    # Validation silencieuse au chargement
    errors = ConfigValidator.validate()
    if errors:
        print("[config] ATTENTION: {} erreur(s) de configuration".format(len(errors)))
        for err in errors:
            print("[config]   - {}".format(err))
