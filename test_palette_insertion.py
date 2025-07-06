#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test d'insertion de feuilles avec numéros de palette
Exemple d'utilisation de la nouvelle colonne NO_PALETTE
"""

from database_utils import DatabaseManager, insert_sheet_with_palette, get_job_palettes
from datetime import datetime
import time

def test_palette_insertion():
    """Test complet d'insertion avec palettes"""
    
    print("🧪 === TEST INSERTION AVEC PALETTES ===")
    print(f"⏰ Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # Configuration du test
    test_job = 147999  # Job de test
    
    # Scénario: 3 palettes avec plusieurs feuilles chacune
    test_scenarios = [
        {
            'palette': 'PAL_147999_001',
            'feuilles': [
                {'joints': 8, 'coupons': 9, 'duree': 25},
                {'joints': 7, 'coupons': 8, 'duree': 28},
                {'joints': 9, 'coupons': 10, 'duree': 22},
            ]
        },
        {
            'palette': 'PAL_147999_002', 
            'feuilles': [
                {'joints': 6, 'coupons': 7, 'duree': 30},
                {'joints': 8, 'coupons': 9, 'duree': 26},
            ]
        },
        {
            'palette': 'PAL_147999_003',
            'feuilles': [
                {'joints': 5, 'coupons': 6, 'duree': 32},
                {'joints': 7, 'coupons': 8, 'duree': 27},
                {'joints': 8, 'coupons': 9, 'duree': 24},
                {'joints': 6, 'coupons': 7, 'duree': 29},
            ]
        }
    ]
    
    # Demander confirmation
    total_feuilles = sum(len(scenario['feuilles']) for scenario in test_scenarios)
    print(f"📋 Scénario de test:")
    print(f"   🏷️ Job: {test_job}")
    print(f"   📦 Palettes: {len(test_scenarios)}")
    print(f"   📄 Feuilles: {total_feuilles}")
    
    for i, scenario in enumerate(test_scenarios, 1):
        palette = scenario['palette']
        nb_feuilles = len(scenario['feuilles'])
        total_joints = sum(f['joints'] for f in scenario['feuilles'])
        total_coupons = sum(f['coupons'] for f in scenario['feuilles'])
        
        print(f"   {i}. {palette}: {nb_feuilles} feuilles, {total_joints} joints, {total_coupons} coupons")
    
    response = input(f"\n🤔 Insérer ces données test ? (y/N): ")
    
    if response.lower() not in ['y', 'yes', 'oui', 'o']:
        print("⏭️ Test annulé")
        return
    
    # Insertion des données
    print(f"\n🚀 === INSERTION EN COURS ===")
    
    db = DatabaseManager()
    if not db.connect():
        print("❌ Impossible de se connecter à la base")
        return
    
    inserted_ids = []
    
    try:
        for scenario in test_scenarios:
            palette = scenario['palette']
            print(f"\n📦 Traitement palette: {palette}")
            
            for i, feuille in enumerate(scenario['feuilles'], 1):
                # Insérer la feuille
                feuille_id = db.insert_feuille_with_palette(
                    no_job=test_job,
                    no_palette=palette,
                    nb_joint=feuille['joints'],
                    nb_coupon=feuille['coupons'],
                    duree=feuille['duree'],
                    id_paquet=1000 + len(inserted_ids)  # ID paquet unique
                )
                
                if feuille_id:
                    inserted_ids.append(feuille_id)
                    print(f"   ✅ Feuille {i}: ID={feuille_id}")
                else:
                    print(f"   ❌ Erreur feuille {i}")
                
                # Petit délai pour avoir des timestamps différents
                time.sleep(0.1)
        
        print(f"\n✅ === INSERTION TERMINÉE ===")
        print(f"📊 Total feuilles insérées: {len(inserted_ids)}")
        
        # Vérification des données insérées
        print(f"\n🔍 === VÉRIFICATION DES DONNÉES ===")
        
        palettes = db.get_palettes_by_job(test_job)
        if palettes:
            print(f"📦 Palettes trouvées pour le job {test_job}:")
            print(f"{'Palette':<20} {'Feuilles':<8} {'Joints':<7} {'Coupons':<8} {'Début':<20}")
            print("-" * 70)
            
            for palette in palettes:
                debut_str = palette['debut'].strftime('%H:%M:%S') if palette['debut'] else 'N/A'
                print(f"{palette['no_palette']:<20} {palette['nb_feuilles']:<8} {palette['total_joints']:<7} {palette['total_coupons']:<8} {debut_str:<20}")
        
        else:
            print("⚠️ Aucune palette trouvée")
        
    except Exception as e:
        print(f"❌ Erreur durant l'insertion: {e}")
    
    finally:
        db.disconnect()

def test_palette_generation():
    """Test de génération automatique de numéros de palette"""
    
    print(f"\n🏷️ === TEST GÉNÉRATION PALETTES ===")
    
    db = DatabaseManager()
    if not db.connect():
        print("❌ Impossible de se connecter à la base")
        return
    
    try:
        test_jobs = [147430, 147500, 147999]
        
        for job in test_jobs:
            # Générer plusieurs numéros de palette
            palettes = []
            for i in range(3):
                palette = db.generate_palette_number(job, i + 1)
                palettes.append(palette)
            
            # Génération automatique (sans spécifier sequence)
            auto_palette = db.generate_palette_number(job)
            
            print(f"📋 Job {job}:")
            print(f"   Manuelles: {', '.join(palettes)}")
            print(f"   Auto: {auto_palette}")
    
    except Exception as e:
        print(f"❌ Erreur génération: {e}")
    
    finally:
        db.disconnect()

def show_usage_examples():
    """Montre des exemples d'utilisation pratique"""
    
    print(f"\n📝 === EXEMPLES D'UTILISATION ===")
    
    print(f"\n1️⃣ Insertion simple avec palette:")
    print("""
from database_utils import insert_sheet_with_palette

# Insérer une feuille avec palette
feuille_id = insert_sheet_with_palette(
    no_job=147430,
    no_palette='PAL_147430_001', 
    nb_joint=8,
    nb_coupon=9,
    duree=25
)
print(f"Feuille insérée: {feuille_id}")
    """)
    
    print(f"\n2️⃣ Récupération des palettes d'un job:")
    print("""
from database_utils import get_job_palettes

# Lister toutes les palettes d'un job
palettes = get_job_palettes(147430)
for palette in palettes:
    print(f"Palette {palette['no_palette']}: {palette['nb_feuilles']} feuilles")
    """)
    
    print(f"\n3️⃣ Utilisation avec gestionnaire:")
    print("""
from database_utils import DatabaseManager

db = DatabaseManager()
if db.connect():
    # Générer numéro de palette automatique
    palette = db.generate_palette_number(147430)
    
    # Insérer plusieurs feuilles
    for i in range(5):
        db.insert_feuille_with_palette(
            no_job=147430,
            no_palette=palette,
            nb_joint=8,
            nb_coupon=9
        )
    
    db.disconnect()
    """)

if __name__ == "__main__":
    test_palette_generation()
    test_palette_insertion()
    show_usage_examples() 