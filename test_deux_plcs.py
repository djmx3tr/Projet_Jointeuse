#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour l'interface avec deux PLCs
- 192.168.0.175 : Job + Bits W29.00/W29.01
- 192.168.0.157 : Feuilles, Temps d'arrêt, Palette
"""

print("🚀 TEST INTERFACE AVEC DEUX PLCs")
print("=" * 60)
print("📡 PLC Principal (192.168.0.175):")
print("   • Job (D8500)")
print("   • Bits W29.00 (Fin de Job)")
print("   • Bits W29.01 (Fin de Palette)")
print()
print("📡 PLC Production (192.168.0.157):")
print("   • Feuilles (D3100)")
print("   • Temps d'arrêt (D3150)")
print("   • Palette (D8570)")
print()
print("=" * 60)

try:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from interface_graphique_production_v2 import InterfaceGraphiqueProductionV2
    
    print("✅ Import réussi")
    
    app = InterfaceGraphiqueProductionV2()
    print("✅ Application créée avec deux PLCs")
    
    # Test rapide - fermeture automatique après 15 secondes
    app.root.after(15000, app.root.quit)
    
    print("🔍 Interface lancée pour 15 secondes - REGARDEZ LES DONNÉES CHANGER !")
    print("=" * 60)
    
    app.run()
    
    print("=" * 60)
    print("✅ Test terminé - Les données de production devraient maintenant se mettre à jour !")
    
except Exception as e:
    print(f"❌ ERREUR: {e}")
    import traceback
    traceback.print_exc() 