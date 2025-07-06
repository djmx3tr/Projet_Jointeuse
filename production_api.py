#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API de Production pour Dashboard Centralisé
Expose les données de chaque machine pour supervision globale
"""

import json
import os
import sys
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
import pyodbc
import threading
import time

# Ajouter le module fins au path
sys.path.append(os.path.join(os.path.dirname(__file__), 'fins'))

class ProductionAPI:
    def __init__(self):
        self.app = Flask(__name__)
        CORS(self.app)  # Permettre les requêtes cross-origin
        
        # Charger la configuration
        self.load_config()
        
        # Cache des données pour éviter trop de requêtes DB
        self.cache = {
            'last_update': None,
            'production_data': [],
            'current_stats': {},
            'machine_status': {}
        }
        self.cache_duration = 30  # 30 secondes de cache
        
        # Définir les routes
        self.setup_routes()
        
        # Démarrer la mise à jour en arrière-plan
        self.start_background_update()
    
    def load_config(self):
        """Charge la configuration depuis config.json"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'CONFIG', 'config.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except Exception as e:
            print(f"❌ Erreur chargement config: {e}")
            # Configuration par défaut
            self.config = {
                "machine": {
                    "id": "L1",
                    "name": "Jointeuse L1",
                    "location": "Atelier Principal"
                },
                "databases": {
                    "production": {
                        "server": "192.168.0.193\\SQLEXPRESS",
                        "database": "KPI_data",
                        "username": "sa",
                        "password": "Excelpro2022!"
                    },
                    "jobs": {
                        "server": "192.168.0.7\\SQLEXPRESS",
                        "database": "PnsiDB",
                        "username": "GeniusExcel",
                        "password": "U_8nB+zUgByuCHgC4"
                    }
                },
                "plc": {
                    "main": {
                        "ip": "192.168.0.157",
                        "port": 9600
                    }
                }
            }
    
    def connect_to_production_database(self):
        """Connexion à la base de données de production"""
        try:
            db_config = self.config['databases']['production']
            connection_string = f"""
            DRIVER={{ODBC Driver 17 for SQL Server}};
            SERVER={db_config['server']};
            DATABASE={db_config['database']};
            UID={db_config['username']};
            PWD={db_config['password']};
            TrustServerCertificate=yes;
            """
            return pyodbc.connect(connection_string, timeout=5)
        except Exception as e:
            print(f"❌ Erreur connexion DB production: {e}")
            return None
    
    def connect_to_jobs_database(self):
        """Connexion à la base de données des jobs"""
        try:
            db_config = self.config['databases']['jobs']
            connection_string = f"""
            DRIVER={{ODBC Driver 17 for SQL Server}};
            SERVER={db_config['server']};
            DATABASE={db_config['database']};
            UID={db_config['username']};
            PWD={db_config['password']};
            TrustServerCertificate=yes;
            """
            return pyodbc.connect(connection_string, timeout=5)
        except Exception as e:
            print(f"❌ Erreur connexion DB jobs: {e}")
            return None
    
    def get_production_data_hourly(self):
        """Récupère les données de production depuis le cache de l'interface"""
        cache_file = os.path.join(os.path.dirname(__file__), 'data_cache.json')
        
        try:
            # Lire le fichier cache créé par l'interface
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                # Vérifier que le cache n'est pas trop ancien (max 5 minutes)
                cache_time = datetime.fromisoformat(cache_data['timestamp'])
                if (datetime.now() - cache_time).total_seconds() < 300:
                    return cache_data.get('hourly_data', [])
                else:
                    print("⚠️ Cache trop ancien, données vides")
                    return []
            else:
                print("⚠️ Fichier cache non trouvé")
                return []
                
        except Exception as e:
            print(f"❌ Erreur lecture cache: {e}")
            return []
    
    def calculate_projection(self, data):
        """Calcule la projection pour l'heure actuelle (identique à l'interface)"""
        current_hour = datetime.now().hour
        current_minute = datetime.now().minute
        
        if not (7 <= current_hour <= 21):
            return None
            
        hour_progress = current_minute / 60.0
        if hour_progress < 0.1:
            return None
            
        current_hour_data = None
        for item in data:
            if item['heure'] == current_hour:
                current_hour_data = item
                break
        
        if not current_hour_data:
            return None
            
        current_feuilles = current_hour_data['feuilles']
        current_joints = current_hour_data['joints']
        current_arrets_min = current_hour_data['arrets_reels_min']
        
        projected_feuilles = current_feuilles / hour_progress if hour_progress > 0 else 0
        projected_joints_moy = (current_joints / current_feuilles) if current_feuilles > 0 else 0
        projected_arrets = current_arrets_min / hour_progress if hour_progress > 0 else 0
        
        projected_feuilles = min(projected_feuilles, 200)
        projected_arrets = min(projected_arrets, 50)
        
        return {
            'hour': current_hour,
            'current_feuilles': current_feuilles,
            'projected_feuilles': round(projected_feuilles),
            'current_joints_moy': round(projected_joints_moy, 1),
            'projected_joints_moy': round(projected_joints_moy, 1),
            'current_arrets': current_arrets_min,
            'projected_arrets': round(projected_arrets, 1),
            'hour_progress': hour_progress
        }
    
    def get_current_stats(self):
        """Récupère les statistiques actuelles depuis le cache"""
        cache_file = os.path.join(os.path.dirname(__file__), 'data_cache.json')
        
        try:
            # Lire le fichier cache créé par l'interface
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                # Vérifier que le cache n'est pas trop ancien (max 5 minutes)
                cache_time = datetime.fromisoformat(cache_data['timestamp'])
                if (datetime.now() - cache_time).total_seconds() < 300:
                    return cache_data.get('current_stats', {})
                else:
                    print("⚠️ Cache trop ancien, stats vides")
                    return {}
            else:
                print("⚠️ Fichier cache non trouvé")
                return {}
                
        except Exception as e:
            print(f"❌ Erreur lecture stats cache: {e}")
            return {}
    
    def update_cache(self):
        """Met à jour le cache des données depuis le fichier cache de l'interface"""
        cache_file = os.path.join(os.path.dirname(__file__), 'data_cache.json')
        
        try:
            # Lire directement le cache de l'interface
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    interface_cache = json.load(f)
                
                # Vérifier que le cache n'est pas trop ancien
                cache_time = datetime.fromisoformat(interface_cache['timestamp'])
                if (datetime.now() - cache_time).total_seconds() < 300:
                    # Utiliser les données de l'interface
                    self.cache = {
                        'last_update': datetime.now(),
                        'production_data': interface_cache.get('hourly_data', []),
                        'current_stats': interface_cache.get('current_stats', {}),
                        'job_info': interface_cache.get('job_info', {}),
                        'projection': interface_cache.get('projection'),
                        'machine_info': interface_cache.get('machine_info', {
                            'id': self.config['station']['id'],
                            'name': self.config['station']['name'],
                            'location': self.config['station']['line'],
                            'status': 'online',
                            'timestamp': datetime.now().isoformat()
                        })
                    }
                else:
                    print("⚠️ Cache interface trop ancien")
                    self.cache = self.get_empty_cache()
            else:
                print("⚠️ Cache interface non trouvé")
                self.cache = self.get_empty_cache()
            
        except Exception as e:
            print(f"❌ Erreur lecture cache interface: {e}")
            self.cache = self.get_empty_cache()
    
    def get_empty_cache(self):
        """Retourne un cache vide"""
        return {
            'last_update': datetime.now(),
            'production_data': [],
            'current_stats': {},
            'job_info': {},
            'projection': None,
            'machine_info': {
                'id': self.config['station']['id'],
                'name': self.config['station']['name'],
                'location': self.config['station']['line'],
                'status': 'offline',
                'timestamp': datetime.now().isoformat()
            }
        }
    
    def is_cache_valid(self):
        """Vérifie si le cache est encore valide"""
        if not self.cache['last_update']:
            return False
        
        elapsed = (datetime.now() - self.cache['last_update']).total_seconds()
        return elapsed < self.cache_duration
    
    def setup_routes(self):
        """Définit les routes de l'API"""
        
        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """Point de santé de l'API"""
            return jsonify({
                'status': 'ok',
                'machine': self.config['station']['id'],
                'timestamp': datetime.now().isoformat(),
                'version': '1.0.0'
            })
        
        @self.app.route('/api/machine/info', methods=['GET'])
        def machine_info():
            """Informations sur la machine"""
            return jsonify(self.config['station'])
        
        @self.app.route('/api/production/current', methods=['GET'])
        def current_production():
            """Données de production actuelles"""
            if not self.is_cache_valid():
                self.update_cache()
            
            return jsonify({
                'machine': self.cache['machine_info'],
                'stats': self.cache['current_stats'],
                'projection': self.cache['projection'],
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/api/production/hourly', methods=['GET'])
        def hourly_production():
            """Données de production par heure"""
            if not self.is_cache_valid():
                self.update_cache()
            
            return jsonify({
                'machine': self.cache['machine_info'],
                'data': self.cache['production_data'],
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/api/production/full', methods=['GET'])
        def full_production():
            """Toutes les données de production (pour le dashboard)"""
            if not self.is_cache_valid():
                self.update_cache()
            
            return jsonify({
                'machine': self.cache['machine_info'],
                'current_stats': self.cache['current_stats'],
                'job_info': self.cache['job_info'],
                'hourly_data': self.cache['production_data'],
                'projection': self.cache['projection'],
                'timestamp': datetime.now().isoformat()
            })
    
    def start_background_update(self):
        """Démarre la mise à jour en arrière-plan"""
        def update_loop():
            while True:
                try:
                    self.update_cache()
                    time.sleep(30)  # Mise à jour toutes les 30 secondes
                except Exception as e:
                    print(f"❌ Erreur update background: {e}")
                    time.sleep(60)  # Attendre plus longtemps en cas d'erreur
        
        thread = threading.Thread(target=update_loop, daemon=True)
        thread.start()
    
    def run(self, host='0.0.0.0', port=5001, debug=False):
        """Lance le serveur API"""
        print(f"🚀 API Production démarrée sur http://{host}:{port}")
        print(f"📊 Machine: {self.config['station']['name']}")
        print(f"🔄 Cache: {self.cache_duration}s")
        self.app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    api = ProductionAPI()
    api.run() 