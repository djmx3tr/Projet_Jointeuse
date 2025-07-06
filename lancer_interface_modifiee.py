#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de lancement pour l'interface modifiée selon les spécifications
- Suppression des titres "INTERFACE COMPLÈTE DE PRODUCTION V2" et "Jointeuse 1"
- Nouvelle organisation avec graphique étendu
- Sections feuilles et temps d'arrêt côte à côte
- Section palette agrandie avec scrollbar
- Nouvelles métriques dans le graphique
"""

import sys
import os

# Ajouter le répertoire PRODUCTION au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from interface_graphique_production_v2 import InterfaceGraphiqueProductionV2

def main():
    """Lance l'interface modifiée"""
    print("🚀 Démarrage de l'interface de production modifiée...")
    print("📋 Modifications apportées:")
    print("   ✓ Suppression du titre principal")
    print("   ✓ Suppression du titre 'Jointeuse 1'")
    print("   ✓ Graphique étendu sur 2/3 de l'écran")
    print("   ✓ Feuilles et temps d'arrêt côte à côte")
    print("   ✓ Section palette agrandie avec scrollbar")
    print("   ✓ Nouvelles métriques: Feuilles/hr, Joints moy./hr, Arrêts min/hr")
    print("   ✓ Légende repositionnée en bas du graphique")
    print("   ✓ Optimisation des espacements")
    print()
    
    try:
        app = InterfaceGraphiqueProductionV2()
        app.run()
    except KeyboardInterrupt:
        print("\n👋 Interface fermée par l'utilisateur")
    except Exception as e:
        print(f"❌ Erreur lors du lancement: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 