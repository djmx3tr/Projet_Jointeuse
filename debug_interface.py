#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de debug pour identifier pourquoi l'interface ne se met pas à jour
"""

print("🔧 DEBUG - Test de l'interface")
print("=" * 50)

try:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from interface_graphique_production_v2 import InterfaceGraphiqueProductionV2
    
    print("✅ Import réussi")
    
    app = InterfaceGraphiqueProductionV2()
    print("✅ Application créée")
    
    # Test rapide - fermeture automatique après 10 secondes
    app.root.after(10000, app.root.quit)
    
    print("🚀 Interface lancée pour 10 secondes - regardez les messages [DEBUG]")
    print("=" * 50)
    
    app.run()
    
    print("=" * 50)
    print("✅ Test terminé")
    
except Exception as e:
    print(f"❌ ERREUR: {e}")
    import traceback
    traceback.print_exc() 