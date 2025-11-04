# 🚀 Démarrage Automatique DD - Guide Rapide

## 📦 Fichiers à Télécharger

1. **[boot.py](boot.py)** - Démarrage automatique avec délai interruption
2. **[dd_main_v1.7.0_PRODUCTION.py](dd_main_v1.7.0_PRODUCTION.py)** - Script principal DD
3. **[GUIDE_BOOT_AUTOSTART.md](GUIDE_BOOT_AUTOSTART.md)** - Documentation complète
4. **[installation_dd.py](installation_dd.py)** - Script d'aide installation

---

## ⚡ Installation Express (5 minutes)

### Étape 1: Préparer les Fichiers

Dans Thonny, ouvrir et copier vers l'ESP32:
- `boot.py` → `/boot.py`
- `dd_main_v1.7.0_PRODUCTION.py` → `/dd_main.py`
- Créer `/config.py` avec:
  ```python
  DETECTOR_ID = "01"  # Changer selon DD
  ```

### Étape 2: Tester

```python
import machine
machine.reset()
```

### Étape 3: Vérifier

Après reset, vous verrez:
```
[BOOT] Démarrage dans 3s... (Ctrl+C pour annuler)
[BOOT] Démarrage dans 2s...
[BOOT] Démarrage dans 1s...
[DD] Démarrage v1.7.0 PRODUCTION
[DD] ID: 01
```

✅ **C'est fait !** Le DD démarre automatiquement.

---

## 🎯 Utilisation Quotidienne

### Démarrage Normal
1. Brancher alimentation
2. Attendre 3 secondes
3. DD démarre automatiquement

### Mode Debug (Interrompre)
1. Brancher USB
2. Dans les 3 secondes: **Ctrl+C**
3. Mode REPL actif
4. Modifier/tester à volonté
5. Relancer: `machine.reset()`

---

## 💡 Feedback LED

| Pattern | Signification |
|---------|---------------|
| Clignotement rapide (3s) | Délai interruption |
| 3 clignotements longs | Démarrage en cours |
| 5 clignotements rapides | Interrompu (Ctrl+C) |
| 10 clignotements | Erreur de démarrage |

---

## 🔧 Configuration boot.py

Pour ajuster le délai:
```python
AUTO_START_ENABLED = True    # True/False
INTERRUPT_DELAY_MS = 3000    # Millisecondes (2000-5000)
```

**Recommandations:**
- Production: 2000ms (2s)
- Développement: 3000ms (3s) ← Par défaut
- Debug intensif: 5000ms (5s)

---

## 📊 Séquence Complète

```
Alimentation → boot.py (3s délai) → dd_main.py → Boucle principale
                    ↓ Ctrl+C
                Mode REPL
```

---

## 🆘 Problèmes Fréquents

### "DD ne démarre pas automatiquement"
- Vérifier `boot.py` présent à la racine
- Vérifier `dd_main.py` présent
- Vérifier `config.py` avec DETECTOR_ID

### "Impossible d'interrompre"
- Appuyer Ctrl+C plus tôt (dès boot)
- Augmenter INTERRUPT_DELAY_MS
- Hard reset (bouton physique)

### "Erreur au démarrage"
```python
# Test manuel:
>>> import dd_main
# Voir l'erreur précise
```

---

## 📖 Documentation Complète

Voir **[GUIDE_BOOT_AUTOSTART.md](GUIDE_BOOT_AUTOSTART.md)** pour:
- Explications détaillées
- Tous les scénarios d'utilisation
- Troubleshooting complet
- Astuces avancées

---

## ✅ Checklist Installation

- [ ] boot.py copié sur ESP32
- [ ] dd_main.py copié sur ESP32 (renommé depuis v1.7.0)
- [ ] config.py créé avec bon DETECTOR_ID
- [ ] Test reset: système démarre après 3s
- [ ] Test interruption: Ctrl+C fonctionne
- [ ] DD fonctionne correctement

---

## 🎉 Résultat Final

**Avant:** Démarrage manuel à chaque fois  
**Après:** Démarrage automatique + possibilité d'interrompre

**Bénéfices:**
- ✅ Déploiement simplifié
- ✅ Redémarrage auto après panne
- ✅ Debug facile avec Ctrl+C
- ✅ Production-ready

---

**Version:** 1.0  
**Compatible:** MicroPython 1.19+, ESP32  
**Date:** 04/11/2025
