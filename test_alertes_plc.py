#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour les nouvelles alertes PLC W29.00 et W29.01
Test de changement de couleurs et messages d'alerte
"""

import sys
import os

# Ajouter le répertoire PRODUCTION au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from interface_graphique_production_v2 import InterfaceGraphiqueProductionV2

def main():
    """Lance l'interface avec les nouvelles alertes PLC"""
    print("🚀 Interface de Production avec Alertes PLC")
    print("📋 Nouvelles fonctionnalités:")
    print("   🔗 Connexion PLC: 192.168.0.175")
    print("   📡 Lecture W29.00 (Fin de Job)")
    print("   📡 Lecture W29.01 (Fin de Palette)")
    print()
    print("🎨 Alertes visuelles:")
    print("   🔴 W29.00 activé → JOB NO et Palette en ROUGE")
    print("   🔴 W29.01 activé → Palette en ROUGE seulement")
    print("   ⚠️  Message: 'Changement de Job / Palette Requis'")
    print()
    print("📞 Mode Simulation supprimé - Connexion PLC directe")
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