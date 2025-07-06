#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ajout de la colonne NO_PALETTE à la table TABLE_FEUILLES
et test d'insertion avec palette
"""

import pyodbc
from config_loader import get_config
from datetime import datetime

def add_no_palette_column():
    """Ajoute la colonne NO_PALETTE à TABLE_FEUILLES"""
    
    config = get_config()
    
    print("🔧 === AJOUT COLONNE NO_PALETTE ===")
    print(f"🗄️ Base: {config.production_db_server}/{config.production_db_name}")
    print("=" * 50)
    
    try:
        # Connexion à la base de production
        server_name = config.production_db_server.split('\\')[0]
        conn_string = (
            'DRIVER={FreeTDS};'
            f'SERVER={server_name};'
            'PORT=1433;'
            f'DATABASE={config.production_db_name};'
            f'UID={config.production_db_user};'
            f'PWD={config.production_db_password};'
            'TDS_Version=8.0;'
        )
        
        conn = pyodbc.connect(conn_string, timeout=10)
        print("✅ Connexion réussie !")
        cursor = conn.cursor()
        
        # 1. VÉRIFIER SI LA COLONNE EXISTE DÉJÀ
        print(f"\n🔍 === VÉRIFICATION COLONNE NO_PALETTE ===")
        
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'TABLE_FEUILLES'
            AND TABLE_SCHEMA = 'dbo'
            AND COLUMN_NAME = 'NO_PALETTE'
        """)
        
        existing_column = cursor.fetchone()
        
        if existing_column:
            print("ℹ️ La colonne NO_PALETTE existe déjà !")
            
            # Vérifier la structure
            cursor.execute("""
                SELECT DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'TABLE_FEUILLES'
                AND TABLE_SCHEMA = 'dbo'
                AND COLUMN_NAME = 'NO_PALETTE'
            """)
            
            col_info = cursor.fetchone()
            if col_info:
                print(f"📋 Type: {col_info[0]}, Taille: {col_info[1] or 'N/A'}, Nullable: {col_info[2]}")
        
        else:
            print("🚀 Ajout de la colonne NO_PALETTE...")
            
            # Ajouter la colonne
            sql_add_column = """
            ALTER TABLE dbo.TABLE_FEUILLES
            ADD NO_PALETTE VARCHAR(50) NULL;
            """
            
            cursor.execute(sql_add_column)
            conn.commit()
            print("✅ Colonne NO_PALETTE ajoutée avec succès !")
        
        # 2. VÉRIFIER LA NOUVELLE STRUCTURE
        print(f"\n📋 === STRUCTURE MISE À JOUR ===")
        
        cursor.execute("""
            SELECT 
                ORDINAL_POSITION,
                COLUMN_NAME, 
                DATA_TYPE,
                CHARACTER_MAXIMUM_LENGTH,
                IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'TABLE_FEUILLES'
            AND TABLE_SCHEMA = 'dbo'
            ORDER BY ORDINAL_POSITION
        """)
        
        columns = cursor.fetchall()
        
        print(f"📊 Total colonnes: {len(columns)}")
        for col in columns:
            pos, name, dtype, length, nullable = col
            length_str = str(length) if length else "N/A"
            nullable_str = "OUI" if nullable == "YES" else "NON"
            
            marker = "🆕" if name == "NO_PALETTE" else "  "
            print(f"{marker} {pos:<2} {name:<15} {dtype:<12} {length_str:<8} {nullable_str}")
        
        # 3. TEST D'INSERTION AVEC NO_PALETTE
        print(f"\n🧪 === TEST INSERTION AVEC NO_PALETTE ===")
        
        test_data = {
            'timestamp': datetime.now(),
            'id_paquet': 999,  # ID test
            'ligne': 'L1',
            'nb_joint': 8,
            'nb_coupon': 9,
            'duree': 30,
            'no_job': 147999,  # Job test
            'no_palette': 'PAL_TEST_001'  # Nouvelle palette test
        }
        
        print(f"📝 Données test:")
        for key, value in test_data.items():
            print(f"   {key}: {value}")
        
        # Préparer la requête d'insertion
        insert_sql = """
        INSERT INTO dbo.TABLE_FEUILLES 
        (TIMESTAMP, ID_PAQUET, LIGNE, NB_JOINT, NB_COUPON, DUREE, NO_JOB, NO_PALETTE)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        # Confirmation avant insertion
        response = input("\n🤔 Voulez-vous insérer ces données test ? (y/N): ")
        
        if response.lower() in ['y', 'yes', 'oui', 'o']:
            cursor.execute(insert_sql, (
                test_data['timestamp'],
                test_data['id_paquet'],
                test_data['ligne'],
                test_data['nb_joint'],
                test_data['nb_coupon'],
                test_data['duree'],
                test_data['no_job'],
                test_data['no_palette']
            ))
            
            conn.commit()
            print("✅ Données test insérées avec succès !")
            
            # Vérifier l'insertion
            cursor.execute("""
                SELECT TOP 1 ID_FEUILLE, NO_JOB, NO_PALETTE, NB_JOINT, NB_COUPON, TIMESTAMP
                FROM dbo.TABLE_FEUILLES 
                WHERE NO_JOB = ? AND NO_PALETTE = ?
                ORDER BY ID_FEUILLE DESC
            """, (test_data['no_job'], test_data['no_palette']))
            
            inserted_row = cursor.fetchone()
            if inserted_row:
                print(f"\n📋 Ligne insérée:")
                print(f"   ID_FEUILLE: {inserted_row[0]}")
                print(f"   NO_JOB: {inserted_row[1]}")
                print(f"   NO_PALETTE: {inserted_row[2]}")
                print(f"   JOINTS: {inserted_row[3]}")
                print(f"   COUPONS: {inserted_row[4]}")
                print(f"   TIMESTAMP: {inserted_row[5]}")
        else:
            print("⏭️ Insertion annulée")
        
        conn.close()
        print(f"\n✅ Opération terminée !")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")

def show_insert_example():
    """Montre un exemple d'insertion avec NO_PALETTE"""
    
    print(f"\n📝 === EXEMPLE INSERTION AVEC NO_PALETTE ===")
    
    example_sql = """
-- Exemple d'insertion avec NO_PALETTE
INSERT INTO dbo.TABLE_FEUILLES 
(TIMESTAMP, ID_PAQUET, LIGNE, NB_JOINT, NB_COUPON, DUREE, NO_JOB, NO_PALETTE)
VALUES 
(GETDATE(), 1001, 'L1', 8, 9, 25, 147430, 'PAL_147430_001');

-- Ou avec plusieurs palettes pour le même job
INSERT INTO dbo.TABLE_FEUILLES 
(TIMESTAMP, ID_PAQUET, LIGNE, NB_JOINT, NB_COUPON, DUREE, NO_JOB, NO_PALETTE)
VALUES 
(GETDATE(), 1002, 'L1', 7, 8, 28, 147430, 'PAL_147430_002'),
(GETDATE(), 1003, 'L1', 9, 10, 22, 147430, 'PAL_147430_003');
    """
    
    print(example_sql.strip())
    
    print(f"\n📊 === REQUÊTE POUR LISTER PAR PALETTE ===")
    
    query_example = """
-- Compter feuilles par palette
SELECT 
    NO_JOB,
    NO_PALETTE,
    COUNT(*) as NB_FEUILLES,
    SUM(NB_JOINT) as TOTAL_JOINTS,
    SUM(NB_COUPON) as TOTAL_COUPONS,
    MIN(TIMESTAMP) as DEBUT,
    MAX(TIMESTAMP) as FIN
FROM dbo.TABLE_FEUILLES 
WHERE LIGNE = 'L1' 
    AND NO_JOB IS NOT NULL 
    AND NO_PALETTE IS NOT NULL
GROUP BY NO_JOB, NO_PALETTE
ORDER BY NO_JOB DESC, NO_PALETTE;
    """
    
    print(query_example.strip())

if __name__ == "__main__":
    add_no_palette_column()
    show_insert_example() 