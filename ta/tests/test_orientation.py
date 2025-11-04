"""
Test de rotation TFT
Teste les 4 orientations possibles
"""

import st7789s3 as st7789
import tft_config
import time

print("="*60)
print("TEST ROTATION TFT")
print("="*60)

print("\nTest des 4 orientations...")
print("Chaque orientation s'affiche 3 secondes")
print()

rotations = [
    (0, "Portrait (défaut)"),
    (1, "Paysage (90°)"),
    (2, "Portrait inversé (180°)"),
    (3, "Paysage inversé (270°)")
]

for rotation, description in rotations:
    print(f"\n[Rotation {rotation}] {description}")
    print("-"*60)
    
    # Initialiser avec cette rotation
    tft = tft_config.config(rotation=rotation)
    
    # Obtenir dimensions
    width = tft.width
    height = tft.height
    print(f"Dimensions: {width}x{height}")
    
    # Fond noir
    tft.fill(st7789.BLACK)
    time.sleep_ms(200)
    
    # Dessiner repères
    # Bande ROUGE en haut
    tft.fill_rect(0, 0, width, 30, st7789.RED)
    
    # Bande VERTE en bas
    tft.fill_rect(0, height-30, width, 30, st7789.GREEN)
    
    # Bande BLEUE à gauche
    tft.fill_rect(0, 30, 30, height-60, st7789.BLUE)
    
    # Bande JAUNE à droite
    tft.fill_rect(width-30, 30, 30, height-60, st7789.YELLOW)
    
    # Point BLANC au centre
    center_x = width // 2
    center_y = height // 2
    tft.fill_rect(center_x-10, center_y-10, 20, 20, st7789.WHITE)
    
    print("Repères affichés:")
    print("  - ROUGE    = Haut")
    print("  - VERT     = Bas")
    print("  - BLEU     = Gauche")
    print("  - JAUNE    = Droite")
    print("  - BLANC    = Centre")
    print()
    print("Observez l'écran pendant 3 secondes...")
    
    time.sleep_ms(10000)

print("\n" + "="*60)
print("TEST TERMINÉ")
print("="*60)
print("\nQuelle rotation était correcte ?")
print("  0 = Portrait")
print("  1 = Paysage (90°)")
print("  2 = Portrait inversé (180°)")
print("  3 = Paysage inversé (270°)")
print()
print("Modifiez ta_config.py:")
print('  UI = {')
print('      "ROTATION": X,  # <- Mettez le bon numéro')
print('      ...')
print('  }')
print("="*60)