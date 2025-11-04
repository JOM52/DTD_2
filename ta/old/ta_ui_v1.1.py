"""
Project: DTD - ta_ui.py v2.1.0
Interface utilisateur pour LilyGO T-Display S3 (mode parallèle 8-bit)
Adapté pour st7789s3 (driver russhughes)
Layout paysage: Titre | Barres DD (1-5) | Noms DD | Log
"""

import ta_config as config
from ta_logger import get_logger

try:
    import st7789s3 as st7789
    import tft_config
except ImportError:
    print("[WARN] st7789s3 ou tft_config non trouvé - mode simulation")
    st7789 = None
    tft_config = None

logger = get_logger()

class UI:
    """Interface utilisateur TFT"""
    
    def __init__(self, tft=None):
        """Initialise l'UI"""
        self.tft = tft
        
        # Dimensions paysage (rotation 1 ou 3)
        rotation = config.UI.get("ROTATION", 1)
        if rotation in (1, 3):  # Mode paysage
            self.width = config.UI.get("WIDTH", 320)
            self.height = config.UI.get("HEIGHT", 170)
        else:  # Mode portrait
            self.width = config.UI.get("WIDTH", 170)
            self.height = config.UI.get("HEIGHT", 320)
        
        # Layout zones (paysage)
        self.zone_title_height = 25        # Titre en haut
        self.zone_bars_height = 60         # Barres de statut DD
        self.zone_labels_height = 20       # Noms des DD
        self.zone_log_height = 30          # Zone de log en bas
        
        # Positions Y des zones
        self.y_title = 0
        self.y_bars = self.zone_title_height
        self.y_labels = self.y_bars + self.zone_bars_height
        self.y_log = self.height - self.zone_log_height
        
        # États des groupes
        self.group_states = [None] * len(config.RADIO["GROUP_IDS"])
        self.testing_id = None
        self.log_text = ""
        
        # Dirty tracking
        self.dirty_groups = set()
        self.dirty_status = False
        self.dirty_progress = False
        self.dirty_log = False
        
        # Initialiser TFT si pas fourni
        if self.tft is None and tft_config is not None:
            try:
                self.tft = tft_config.config(rotation=rotation)
                logger.info("TFT initialisé via tft_config (rotation={})".format(rotation), "ui")
            except Exception as e:
                logger.error("Erreur init TFT: {}".format(e), "ui")
                self.tft = None
        
        if self.tft:
            self._init_display()
        else:
            logger.warning("Mode sans affichage", "ui")
        
        logger.info("UI initialisée ({}x{}) - Layout paysage".format(self.width, self.height), "ui")
    
    def _init_display(self):
        """Initialise l'affichage"""
        if not self.tft:
            return
        
        try:
            # Remplir fond noir
            self.tft.fill(st7789.BLACK)
            
            # Dessiner le titre
            self._draw_title()
            
            # Dessiner les 5 groupes DD
            for i in range(len(config.RADIO["GROUP_IDS"])):
                self._draw_group(i, None)
            
            # Dessiner zone de log
            self._draw_log_zone()
        
        except Exception as e:
            logger.error("Erreur init display: {}".format(e), "ui")
    
    def _draw_title(self):
        """Dessine le titre en haut (bande horizontale)"""
        if not self.tft:
            return
        
        try:
            # Fond bleu pour le titre
            self.tft.fill_rect(0, self.y_title, self.width, self.zone_title_height, st7789.BLUE)
            
            # TODO: Ajouter texte "DTD-TAC" avec font
            
        except Exception as e:
            logger.error("Erreur draw title: {}".format(e), "ui")
    
    def _draw_group(self, index, state):
        """
        Dessine un groupe de détecteur (barre + label)
        
        Args:
            index: Index du groupe (0-4) pour DD1 à DD5
            state: True (présent), False (absent), None (inconnu)
        """
        if not self.tft:
            return
        
        try:
            # Calcul positions horizontales pour 5 DD
            margin_left = 10
            margin_right = 10
            spacing = 5
            available_width = self.width - margin_left - margin_right
            bar_width = (available_width - (spacing * 4)) // 5  # 5 barres avec 4 espacements
            
            x_start = margin_left + (index * (bar_width + spacing))
            
            # Couleur selon l'état
            if state is True:
                color = st7789.GREEN  # Présent
            elif state is False:
                color = st7789.RED    # Absent
            else:
                color = st7789.color565(100, 100, 100)  # Inconnu (gris)
            
            # === BARRE DE STATUT ===
            bar_y = self.y_bars + 5
            bar_height = self.zone_bars_height - 10
            
            # Dessiner rectangle de statut
            self.tft.fill_rect(x_start, bar_y, bar_width, bar_height, color)
            
            # Bordure noire
            self.tft.rect(x_start, bar_y, bar_width, bar_height, st7789.BLACK)
            
            # === LABEL DD ===
            label_y = self.y_labels + 2
            
            # Effacer zone label
            self.tft.fill_rect(x_start, label_y, bar_width, self.zone_labels_height - 4, st7789.BLACK)
            
            # TODO: Afficher "DD1", "DD2", etc. avec font
            # Pour l'instant, une petite barre colorée comme indicateur
            dd_number = index + 1
            indicator_width = bar_width // 3
            indicator_x = x_start + (bar_width - indicator_width) // 2
            self.tft.fill_rect(indicator_x, label_y + 5, indicator_width, 8, st7789.WHITE)
            
        except Exception as e:
            logger.error("Erreur draw group {}: {}".format(index, e), "ui")
    
    def _draw_log_zone(self):
        """Dessine la zone de log en bas"""
        if not self.tft:
            return
        
        try:
            # Fond noir pour la zone de log
            self.tft.fill_rect(0, self.y_log, self.width, self.zone_log_height, st7789.BLACK)
            
            # Bordure supérieure
            self.tft.hline(0, self.y_log, self.width, st7789.color565(80, 80, 80))
            
        except Exception as e:
            logger.error("Erreur draw log zone: {}".format(e), "ui")
    
    def update_group(self, index, state=None, label=None):
        """
        Met à jour un groupe DD
        
        Args:
            index: Index du groupe (0-4) pour DD1 à DD5
            state: True (présent), False (absent), None (inconnu)
            label: Texte optionnel (non utilisé pour l'instant)
        """
        if index < 0 or index >= len(self.group_states):
            return
        
        # Vérifier si changement
        if self.group_states[index] != state:
            self.group_states[index] = state
            self.dirty_groups.add(index)
            
            # Redessiner immédiatement si pas de dirty tracking
            if not config.UI.get("DIRTY_TRACKING", True):
                self._draw_group(index, state)
    
    def status(self, text):
        """
        Affiche un message dans la zone de log en bas
        
        Args:
            text: Texte à afficher dans le log
        """
        if not self.tft:
            return
        
        try:
            self.log_text = text
            self.dirty_log = True
            
            # Effacer zone de log
            self.tft.fill_rect(2, self.y_log + 2, self.width - 4, self.zone_log_height - 4, st7789.BLACK)
            
            # TODO: Afficher texte avec font
            # Pour l'instant, une barre colorée comme indicateur d'activité
            if text:
                bar_width = min(len(text) * 3, self.width - 20)
                self.tft.fill_rect(10, self.y_log + 10, bar_width, 8, st7789.CYAN)
            
        except Exception as e:
            logger.error("Erreur status: {}".format(e), "ui")
    
    def progress(self, dd_id, color=None):
        """
        Affiche/masque la barre de progression pour un DD en test
        
        Args:
            dd_id: ID du détecteur (1-5) ou None pour masquer
            color: Couleur de la barre (optionnel)
        """
        self.testing_id = dd_id
        self.dirty_progress = True
        
        if not self.tft:
            return
        
        try:
            if dd_id is None:
                # Effacer toutes les barres de progression
                self.tft.fill_rect(0, self.y_bars, self.width, 3, st7789.BLACK)
            else:
                # Afficher barre de progression au-dessus du DD concerné
                index = dd_id - 1
                if 0 <= index < len(config.RADIO["GROUP_IDS"]):
                    # Calcul position X (même logique que _draw_group)
                    margin_left = 10
                    margin_right = 10
                    spacing = 5
                    available_width = self.width - margin_left - margin_right
                    bar_width = (available_width - (spacing * 4)) // 5
                    x_pos = margin_left + (index * (bar_width + spacing))
                    
                    bar_color = color if color else st7789.YELLOW
                    
                    # Barre horizontale au-dessus de la barre de statut
                    self.tft.fill_rect(x_pos, self.y_bars + 1, bar_width, 3, bar_color)
        
        except Exception as e:
            logger.error("Erreur progress: {}".format(e), "ui")
    
    def render_dirty(self):
        """Redessine seulement les éléments modifiés (dirty tracking)"""
        if not self.tft:
            return
        
        try:
            # Redessiner groupes modifiés
            for index in self.dirty_groups:
                if index < len(self.group_states):
                    self._draw_group(index, self.group_states[index])
            
            self.dirty_groups.clear()
            self.dirty_status = False
            self.dirty_progress = False
            self.dirty_log = False
            
        except Exception as e:
            logger.error("Erreur render_dirty: {}".format(e), "ui")

logger.info("ta_ui.py v2.1.0 chargé (st7789s3 - layout paysage optimisé)", "ui")