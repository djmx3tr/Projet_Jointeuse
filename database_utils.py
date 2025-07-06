#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilitaires pour les opérations de base de données
avec support de la nouvelle colonne NO_PALETTE
"""

import pyodbc
from datetime import datetime
from config_loader import get_config

class DatabaseManager:
    """Gestionnaire de base de données pour TABLE_FEUILLES avec NO_PALETTE"""
    
    def __init__(self):
        self.config = get_config()
        self.connection = None
    
    def connect(self):
        """Établit la connexion à la base de données"""
        try:
            server_name = self.config.production_db_server.split('\\')[0]
            conn_string = (
                'DRIVER={FreeTDS};'
                f'SERVER={server_name};'
                'PORT=1433;'
                f'DATABASE={self.config.production_db_name};'
                f'UID={self.config.production_db_user};'
                f'PWD={self.config.production_db_password};'
                'TDS_Version=8.0;'
            )
            
            self.connection = pyodbc.connect(conn_string, timeout=10)
            return True
            
        except Exception as e:
            print(f"❌ Erreur de connexion: {e}")
            return False
    
    def disconnect(self):
        """Ferme la connexion à la base de données"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def insert_feuille_with_palette(self, no_job, no_palette, nb_joint, nb_coupon, 
                                   id_paquet=None, duree=None, ligne='L1'):
        """
        Insère une nouvelle feuille avec numéro de job et palette
        
        Args:
            no_job (int): Numéro de job
            no_palette (str): Numéro de palette 
            nb_joint (int): Nombre de joints
            nb_coupon (int): Nombre de coupons
            id_paquet (int, optional): ID du paquet
            duree (int, optional): Durée en secondes
            ligne (str): Ligne de production (défaut: 'L1')
            
        Returns:
            int: ID de la feuille insérée, ou None si erreur
        """
        
        if not self.connection:
            if not self.connect():
                return None
        
        try:
            cursor = self.connection.cursor()
            
            # Préparer les données
            timestamp = datetime.now()
            
            insert_sql = """
            INSERT INTO dbo.TABLE_FEUILLES 
            (TIMESTAMP, ID_PAQUET, LIGNE, NB_JOINT, NB_COUPON, DUREE, NO_JOB, NO_PALETTE)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            cursor.execute(insert_sql, (
                timestamp,
                id_paquet,
                ligne,
                nb_joint,
                nb_coupon,
                duree,
                no_job,
                no_palette
            ))
            
            self.connection.commit()
            
            # Récupérer l'ID de la feuille insérée
            cursor.execute("SELECT @@IDENTITY")
            new_id = cursor.fetchone()[0]
            
            print(f"✅ Feuille insérée: ID={new_id}, Job={no_job}, Palette={no_palette}")
            return int(new_id)
            
        except Exception as e:
            print(f"❌ Erreur insertion: {e}")
            if self.connection:
                self.connection.rollback()
            return None
    
    def get_palettes_by_job(self, no_job):
        """
        Récupère toutes les palettes pour un job donné
        
        Args:
            no_job (int): Numéro de job
            
        Returns:
            list: Liste des informations par palette
        """
        
        if not self.connection:
            if not self.connect():
                return []
        
        try:
            cursor = self.connection.cursor()
            
            query_sql = """
            SELECT 
                NO_PALETTE,
                COUNT(*) as NB_FEUILLES,
                SUM(NB_JOINT) as TOTAL_JOINTS,
                SUM(NB_COUPON) as TOTAL_COUPONS,
                MIN(TIMESTAMP) as DEBUT,
                MAX(TIMESTAMP) as FIN
            FROM dbo.TABLE_FEUILLES 
            WHERE NO_JOB = ? 
                AND NO_PALETTE IS NOT NULL
                AND LIGNE = 'L1'
            GROUP BY NO_PALETTE
            ORDER BY NO_PALETTE
            """
            
            cursor.execute(query_sql, (no_job,))
            results = cursor.fetchall()
            
            palettes = []
            for row in results:
                palettes.append({
                    'no_palette': row[0],
                    'nb_feuilles': row[1],
                    'total_joints': row[2] or 0,
                    'total_coupons': row[3] or 0,
                    'debut': row[4],
                    'fin': row[5]
                })
            
            return palettes
            
        except Exception as e:
            print(f"❌ Erreur requête palettes: {e}")
            return []
    
    def get_production_summary_with_palettes(self, hours=24):
        """
        Récupère un résumé de production incluant les palettes
        
        Args:
            hours (int): Nombre d'heures à inclure (défaut: 24h)
            
        Returns:
            dict: Résumé de production avec palettes
        """
        
        if not self.connection:
            if not self.connect():
                return {}
        
        try:
            cursor = self.connection.cursor()
            
            query_sql = """
            SELECT 
                COUNT(DISTINCT NO_JOB) as NB_JOBS,
                COUNT(DISTINCT NO_PALETTE) as NB_PALETTES,
                COUNT(*) as NB_FEUILLES,
                SUM(NB_JOINT) as TOTAL_JOINTS,
                SUM(NB_COUPON) as TOTAL_COUPONS
            FROM dbo.TABLE_FEUILLES 
            WHERE LIGNE = 'L1'
                AND TIMESTAMP >= DATEADD(HOUR, -?, GETDATE())
                AND NB_JOINT BETWEEN 0 AND 50
                AND NB_COUPON BETWEEN 1 AND 50
            """
            
            cursor.execute(query_sql, (hours,))
            result = cursor.fetchone()
            
            if result:
                return {
                    'nb_jobs': result[0] or 0,
                    'nb_palettes': result[1] or 0,
                    'nb_feuilles': result[2] or 0,
                    'total_joints': result[3] or 0,
                    'total_coupons': result[4] or 0,
                    'period_hours': hours
                }
            
            return {}
            
        except Exception as e:
            print(f"❌ Erreur résumé production: {e}")
            return {}
    
    def validate_palette_format(self, no_palette):
        """
        Valide le format du numéro de palette
        
        Args:
            no_palette (str): Numéro de palette à valider
            
        Returns:
            bool: True si valide, False sinon
        """
        
        if not no_palette or not isinstance(no_palette, str):
            return False
        
        # Vérifier la longueur (max 50 caractères selon la DB)
        if len(no_palette) > 50:
            return False
        
        # Exemples de formats acceptés:
        # PAL_147430_001, PALETTE_001, 147430-PAL-01, etc.
        
        return True
    
    def generate_palette_number(self, no_job, sequence=None):
        """
        Génère un numéro de palette automatique
        
        Args:
            no_job (int): Numéro de job
            sequence (int, optional): Numéro de séquence (auto si None)
            
        Returns:
            str: Numéro de palette généré
        """
        
        if sequence is None:
            # Trouver la prochaine séquence pour ce job
            if not self.connection:
                if not self.connect():
                    sequence = 1
            else:
                try:
                    cursor = self.connection.cursor()
                    cursor.execute("""
                        SELECT COUNT(DISTINCT NO_PALETTE) + 1
                        FROM dbo.TABLE_FEUILLES 
                        WHERE NO_JOB = ? AND NO_PALETTE IS NOT NULL
                    """, (no_job,))
                    
                    result = cursor.fetchone()
                    sequence = result[0] if result else 1
                    
                except Exception:
                    sequence = 1
        
        return f"PAL_{no_job}_{sequence:03d}"

# Fonctions utilitaires pour faciliter l'usage
def insert_sheet_with_palette(no_job, no_palette, nb_joint, nb_coupon, **kwargs):
    """
    Fonction simple pour insérer une feuille avec palette
    
    Args:
        no_job (int): Numéro de job
        no_palette (str): Numéro de palette
        nb_joint (int): Nombre de joints
        nb_coupon (int): Nombre de coupons
        **kwargs: Autres paramètres optionnels
        
    Returns:
        int: ID de la feuille insérée ou None
    """
    
    db = DatabaseManager()
    try:
        return db.insert_feuille_with_palette(
            no_job, no_palette, nb_joint, nb_coupon, **kwargs
        )
    finally:
        db.disconnect()

def get_job_palettes(no_job):
    """
    Fonction simple pour récupérer les palettes d'un job
    
    Args:
        no_job (int): Numéro de job
        
    Returns:
        list: Liste des palettes
    """
    
    db = DatabaseManager()
    try:
        return db.get_palettes_by_job(no_job)
    finally:
        db.disconnect()

if __name__ == "__main__":
    # Test des fonctions
    print("🧪 === TEST DATABASE_UTILS ===")
    
    db = DatabaseManager()
    if db.connect():
        print("✅ Connexion réussie")
        
        # Test génération numéro palette
        test_job = 147430
        palette_num = db.generate_palette_number(test_job)
        print(f"🏷️ Palette générée: {palette_num}")
        
        # Test résumé production
        summary = db.get_production_summary_with_palettes(24)
        if summary:
            print(f"📊 Production 24h:")
            for key, value in summary.items():
                print(f"   {key}: {value}")
        
        db.disconnect()
    else:
        print("❌ Connexion échouée") 