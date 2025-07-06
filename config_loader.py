#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestionnaire de configuration centralisé
Charge et fournit l'accès à toute la configuration depuis config.json
"""

import json
import os
import sys
from typing import Dict, Any

class ConfigLoader:
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, config_file='../CONFIG/config.json'):
        if self._config is None:
            self.load_config(config_file)
    
    def load_config(self, config_file: str):
        """Charge la configuration depuis le fichier JSON"""
        try:
            # Essayer d'abord le chemin relatif
            if not os.path.exists(config_file):
                # Essayer un chemin absolu basé sur le script actuel
                script_dir = os.path.dirname(os.path.abspath(__file__))
                config_file = os.path.join(script_dir, config_file)
            
            if not os.path.exists(config_file):
                # Dernier essai avec CONFIG dans le parent
                script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                config_file = os.path.join(script_dir, 'CONFIG', 'config.json')
            
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
            print(f"✅ Configuration chargée depuis {config_file}")
            
        except FileNotFoundError:
            print(f"❌ Fichier de configuration {config_file} non trouvé")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"❌ Erreur dans le fichier de configuration : {e}")
            sys.exit(1)
    
    def get(self, key_path: str, default=None):
        """
        Récupère une valeur de configuration en utilisant un chemin de clés séparées par des points
        Exemple: get('plc.ip') -> '192.168.0.157'
        """
        if self._config is None:
            return default
        
        keys = key_path.split('.')
        value = self._config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_plc_config(self) -> Dict[str, Any]:
        """Retourne la configuration PLC complète"""
        return self.get('plc', {})
    
    def get_database_config(self, db_name: str) -> Dict[str, Any]:
        """Retourne la configuration d'une base de données spécifique"""
        return self.get(f'databases.{db_name}', {})
    
    def get_interface_config(self) -> Dict[str, Any]:
        """Retourne la configuration interface complète"""
        return self.get('interface', {})
    
    def get_chart_config(self) -> Dict[str, Any]:
        """Retourne la configuration du graphique"""
        return self.get('production_chart', {})
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Retourne la configuration de monitoring"""
        return self.get('monitoring', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Retourne la configuration de logging"""
        return self.get('logging', {})
    
    def get_station_config(self) -> Dict[str, Any]:
        """Retourne la configuration de la station"""
        return self.get('station', {})
    
    def get_barcode_config(self) -> Dict[str, Any]:
        """Retourne la configuration du scanner de codes-barres"""
        return self.get('barcode', {})
    
    # Méthodes de convenance pour les valeurs les plus utilisées
    @property
    def plc_ip(self) -> str:
        return self.get('plc.ip', '192.168.0.157')
    
    @property
    def plc_port(self) -> int:
        return self.get('plc.port', 9600)
    
    @property
    def plc_addresses(self) -> Dict[str, Any]:
        return self.get('plc.addresses', {})
    
    @property
    def jobs_db_server(self) -> str:
        return self.get('databases.jobs.server', '')
    
    @property
    def jobs_db_name(self) -> str:
        return self.get('databases.jobs.database', '')
    
    @property
    def jobs_db_user(self) -> str:
        return self.get('databases.jobs.username', '')
    
    @property
    def jobs_db_password(self) -> str:
        return self.get('databases.jobs.password', '')
    
    @property
    def production_db_server(self) -> str:
        return self.get('databases.production.server', '')
    
    @property
    def production_db_name(self) -> str:
        return self.get('databases.production.database', '')
    
    @property
    def production_db_user(self) -> str:
        return self.get('databases.production.username', '')
    
    @property
    def production_db_password(self) -> str:
        return self.get('databases.production.password', '')
    
    @property
    def interface_title(self) -> str:
        return self.get('interface.title', 'Interface de Production')
    
    @property
    def chart_update_interval(self) -> int:
        return self.get('production_chart.update_interval', 300)
    
    @property
    def plc_update_interval(self) -> int:
        return self.get('monitoring.plc_update_interval', 1)
    
    def print_config_summary(self):
        """Affiche un résumé de la configuration chargée"""
        print("\n🏭 === RÉSUMÉ DE LA CONFIGURATION ===")
        print(f"🏷️  Station: {self.get('station.name')}")
        print(f"🔗 PLC: {self.plc_ip}:{self.plc_port}")
        print(f"🗄️  DB Jobs: {self.jobs_db_server}")
        print(f"📊 DB Production: {self.production_db_server}")
        print(f"⏱️  Mise à jour PLC: {self.plc_update_interval}s")
        print(f"📈 Mise à jour graphique: {self.chart_update_interval}s")
        print("=" * 40)

# Instance globale singleton
config = ConfigLoader()

# Fonction de convenance pour récupérer la configuration
def get_config():
    """Retourne l'instance globale de configuration"""
    return config

if __name__ == "__main__":
    # Test de la configuration
    config = get_config()
    config.print_config_summary()
    print(f"Test accès: PLC IP = {config.plc_ip}")
    print(f"Test accès: Adresses PLC = {config.plc_addresses}") 