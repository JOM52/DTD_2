"""
Project: DTD - ta_ui.py v2.2.0
Interface utilisateur pour LilyGO T-Display S3 (mode parallèle 8-bit)
Adapté pour st7789s3 (driver russhughes)
Layout paysage: Titre (DTD + version) | Barres DD (1-5) | Noms DD | Log
Hauteurs configurables via ta_config.py
"""

import ta_config as config
from ta_logger import get_logger

try:
    import st7789s3 as st7789
    import tft_config
    # Import des fonts disponibles
    import vga1_8x16 as font_small
    import vga1_16x32 as font_large
except ImportError:
    print("[WARN] st7789s3, tft_config ou fonts non trouvés - mode simulation")
    st7789 = None
    tft_config = None
    font_small = None
    font_large = None

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
        
        # Layout zones (depuis config)
        self.zone_title_height = config.UI.get("ZONE_TITLE_HEIGHT", 20)
        self.zone_bars_height = config.UI.get("ZONE_BARS_HEIGHT", 45)
        self.zone_labels_height = config.UI.get("ZONE_LABELS_HEIGHT", 15)
        self.zone_log_height = config.UI.get("ZONE_LOG_HEIGHT", 45)
        
        # Positions Y des zones
        self.y_title = 0
        self.y_bars = self.zone_title_height
        self.y_labels = self.y_bars + self.zone_bars_height
        self.y_log = self.height - self.zone_log_height
        
        # Marges et espacements
        self.margin_left = config.UI.get("MARGIN_LEFT", 10)
        self.margin_right = config.UI.get("MARGIN_RIGHT", 10)
        self.bar_spacing = config.UI.get("BAR_SPACING", 5)
        
        # États des groupes
        self.group_states = [None] * len(config.RADIO["GROUP_IDS"])
        self.testing_id = None
        self.log_text = ""
        
        # Historique de log (3 lignes qui défilent)
        self.log_history = []
        self.max_log_lines = 3
        
        # Dirty tracking
        self.dirty_groups = set()
        self.dirty_status = False
        self.dirty_progress = False
        self.dirty_log = False
        
        # Initialiser TFT si pas fourni
        if self.tft is None and tft_config is not None:
            try:
#                 print("rotation:",rotation)
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
        """Dessine le titre en haut avec nom et version"""
        if not self.tft:
            return
        
        try:
            # Fond bleu pour le titre
            self.tft.fill_rect(0, self.y_title, self.width, self.zone_title_height, st7789.BLUE)
            
            # Construire le texte du titre
            app_name = getattr(config, "APP_NAME", "DTD")
            app_version = getattr(config, "APP_VERSION", "1.0.0")
            title_text = "{} v{}".format(app_name, app_version)
            
            # Afficher le texte avec font si disponible
            if font_large:
                # Calculer position centrée
                text_width = len(title_text) * 16  # 16 pixels par caractère
                text_x = (self.width - text_width) // 2
                text_y = self.y_title + 2
                
                # Afficher le texte en blanc
                self.tft.text(font_large, title_text, text_x, text_y, st7789.WHITE, st7789.BLUE)
            else:
                # Fallback: barre blanche
                text_width = len(title_text) * 6
                text_x = (self.width - text_width) // 2
                if text_x < 5:
                    text_x = 5
                self.tft.fill_rect(text_x, self.y_title + 6, 
                                 min(text_width, self.width - 10), 8, st7789.WHITE)
            
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
            available_width = self.width - self.margin_left - self.margin_right
            bar_width = (available_width - (self.bar_spacing * 4)) // 5  # 5 barres avec 4 espacements
            
            x_start = self.margin_left + (index * (bar_width + self.bar_spacing))
            
            # Couleur selon l'état
            if state is True:
                color = st7789.GREEN  # Présent
            elif state is False:
                color = st7789.RED    # Absent
            else:
                color = st7789.color565(100, 100, 100)  # Inconnu (gris)
            
            # === BARRE DE STATUT ===
            bar_y = self.y_bars + 3
            bar_height = self.zone_bars_height - 6
            
            # Dessiner rectangle de statut
            self.tft.fill_rect(x_start, bar_y, bar_width, bar_height, color)
            
            # Bordure noire
            self.tft.rect(x_start, bar_y, bar_width, bar_height, st7789.BLACK)
            
            # === LABEL DD ===
            self._draw_dd_label(index, x_start, bar_width)
            
        except Exception as e:
            logger.error("Erreur draw group {}: {}".format(index, e), "ui")
    
    def _draw_dd_label(self, index, x_start, bar_width):
        """
        Dessine le label d'un DD (DD1, DD2, etc.)
        
        Args:
            index: Index du groupe (0-4)
            x_start: Position X de début
            bar_width: Largeur de la barre
        """
        if not self.tft:
            return
        
        try:
            label_y = self.y_labels + 2
            dd_number = index + 1
            
            # Effacer zone label
            self.tft.fill_rect(x_start, label_y, bar_width, self.zone_labels_height - 4, st7789.BLACK)
            
            # Texte "DD" + numéro
            text = "DD{}".format(dd_number)
            
            # Afficher avec font si disponible
            if font_small:
                # Calculer position centrée
                text_width = len(text) * 8  # 8 pixels par caractère
                text_x = x_start + (bar_width - text_width) // 2
                text_y = label_y
                
                # Afficher en blanc sur fond noir
                self.tft.text(font_small, text, text_x, text_y, st7789.WHITE, st7789.BLACK)
            else:
                # Fallback: rectangles blancs
                char_width = 6
                text_width = len(text) * char_width
                text_x = x_start + (bar_width - text_width) // 2
                text_y = label_y + 3
                
                for i, char in enumerate(text):
                    char_x = text_x + (i * char_width)
                    self.tft.fill_rect(char_x, text_y, 5, 7, st7789.WHITE)
            
        except Exception as e:
            logger.error("Erreur draw DD label {}: {}".format(index, e), "ui")
    
    def _draw_log_zone(self):
        """Dessine la zone de log en bas"""
        if not self.tft:
            return
        
        try:
            # Fond noir pour la zone de log
            self.tft.fill_rect(0, self.y_log, self.width, self.zone_log_height, st7789.BLACK)
            
            # Bordure supérieure grise
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
                available_width = self.width - self.margin_left - self.margin_right
                bar_width = (available_width - (self.bar_spacing * 4)) // 5
                x_start = self.margin_left + (index * (bar_width + self.bar_spacing))
                self._draw_group(index, state)
    
    def status(self, text):
        """
        Affiche un message dans la zone de log en bas (historique de 3 lignes)
        
        Args:
            text: Texte à afficher dans le log
        """
        if not self.tft:
            return
        
        try:
            # Ajouter le nouveau texte à l'historique
            if text and text.strip():
                self.log_history.append(text.strip())
                
                # Garder seulement les 3 dernières lignes
                if len(self.log_history) > self.max_log_lines:
                    self.log_history.pop(0)  # Retirer la plus ancienne
            
            self.dirty_log = True
            
            # Effacer complètement la zone de log
            self.tft.fill_rect(5, self.y_log + 2, self.width - 10, self.zone_log_height - 4, st7789.BLACK)
            
            # Afficher les lignes de l'historique avec font si disponible
            if font_small and self.log_history:
                max_chars_per_line = (self.width - 15) // 8
                
                y_offset = self.y_log + 5
                line_height = 14  # Hauteur par ligne (compact pour afficher 3 lignes)
                
                # Afficher chaque ligne de l'historique
                for i, log_line in enumerate(self.log_history):
                    if i >= self.max_log_lines:
                        break
                    
                    # Vérifier qu'on a assez d'espace
                    if y_offset + 12 > self.y_log + self.zone_log_height:
                        break
                    
                    # Tronquer la ligne si trop longue
                    display_line = log_line
                    if len(display_line) > max_chars_per_line:
                        display_line = display_line[:max_chars_per_line - 3] + "..."
                    
                    # Afficher la ligne
                    # Ligne la plus ancienne en gris, les autres en cyan
                    color = st7789.color565(80, 80, 80) if i == 0 and len(self.log_history) == 3 else st7789.CYAN
                    
                    self.tft.text(font_small, display_line, 8, y_offset, color, st7789.BLACK)
                    y_offset += line_height
                    
            elif self.log_history:
                # Fallback: barres colorées pour chaque ligne
                y_offset = self.y_log + 8
                line_height = 10
                
                for i, log_line in enumerate(self.log_history):
                    if i >= self.max_log_lines:
                        break
                    
                    if y_offset + line_height > self.y_log + self.zone_log_height:
                        break
                    
                    bar_width = min(len(log_line) * 6, self.width - 20)
                    color = st7789.color565(80, 80, 80) if i == 0 and len(self.log_history) == 3 else st7789.CYAN
                    self.tft.fill_rect(10, y_offset, bar_width, 6, color)
                    y_offset += line_height
            
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
                    available_width = self.width - self.margin_left - self.margin_right
                    bar_width = (available_width - (self.bar_spacing * 4)) // 5
                    x_pos = self.margin_left + (index * (bar_width + self.bar_spacing))
                    
                    bar_color = color if color else st7789.YELLOW
                    
                    # Barre horizontale au-dessus de la barre de statut
                    self.tft.fill_rect(x_pos, self.y_bars, bar_width, 3, bar_color)
        
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

logger.info("ta_ui.py v2.2.0 chargé (st7789s3 - layout paysage + fonts lisibles)", "ui")