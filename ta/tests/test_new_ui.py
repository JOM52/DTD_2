"""
Test de la nouvelle ta_ui.py adaptée pour st7789s3
"""

print("="*60)
print("TEST NOUVELLE UI - st7789s3")
print("="*60)

try:
    print("\n[1/4] Import des modules...")
    import ta_config as config
    from ta_ui_fixed import UI
    import time
    print("✓ Modules importés")
    
    print("\n[2/4] Initialisation UI...")
    ui = UI()
    print("✓ UI initialisée")
    
    print("\n[3/4] Test affichage des états...")
    time.sleep_ms(1000)
    
    # Tester différents états
    states = [
        (0, True, "DD1: ON"),
        (1, False, "DD2: OFF"),
        (2, None, "DD3: UNKNOWN"),
        (3, True, "DD4: ON"),
        (4, False, "DD5: OFF")
    ]
    
    for index, state, label in states:
        print(f"  {label}...")
        ui.update_group(index, state=state)
        if hasattr(ui, 'render_dirty'):
            ui.render_dirty()
        time.sleep_ms(500)
    
    print("✓ États affichés")
    
    print("\n[4/4] Test animations...")
    
    # Faire clignoter DD1
    for i in range(3):
        print(f"  Clignotement {i+1}/3...")
        ui.update_group(0, state=False)
        ui.render_dirty()
        time.sleep_ms(300)
        ui.update_group(0, state=True)
        ui.render_dirty()
        time.sleep_ms(300)
    
    # Test barre de progression
    print("  Test barre de progression...")
    for dd_id in range(1, 6):
        ui.progress(dd_id)
        time.sleep_ms(300)
    ui.progress(None)  # Effacer
    
    print("✓ Animations terminées")
    
    print("\n" + "="*60)
    print("✓✓✓ UI FONCTIONNE ✓✓✓")
    print("="*60)
    print("\nVérifiez l'écran TFT:")
    print("  - Bande bleue en haut (titre)")
    print("  - 5 rectangles colorés (DD1-5)")
    print("  - DD1 et DD4 en VERT")
    print("  - DD2 et DD5 en ROUGE")
    print("  - DD3 en GRIS")
    print("\nSi oui, la nouvelle UI fonctionne parfaitement !")
    
except Exception as e:
    print("\n" + "="*60)
    print("✗✗✗ ERREUR ✗✗✗")
    print("="*60)
    print(f"Erreur: {e}")
    
    import sys
    sys.print_exception(e)

print("\n" + "="*60)