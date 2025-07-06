#!/usr/bin/env python3
import os
import glob
import select
import struct
import time
import json
import logging
import sys
from datetime import datetime
import fins.tcp
from config_loader import get_config

class ConfigurableBarcodeScanner:
    def __init__(self):
        self.config_loader = get_config()
        self.config = self.config_loader.get_barcode_config()
        self.fins_instance = None
        self.setup_logging()
        
        # Variables pour le scanner
        self.current_barcode = ""
        self.last_key_time = time.time()
        
        # Mapping des touches du clavier
        self.key_map = {
            2: '1', 3: '2', 4: '3', 5: '4', 6: '5', 7: '6', 8: '7', 9: '8', 10: '9', 11: '0',
            16: 'q', 17: 'w', 18: 'e', 19: 'r', 20: 't', 21: 'y', 22: 'u', 23: 'i', 24: 'o', 25: 'p',
            30: 'a', 31: 's', 32: 'd', 33: 'f', 34: 'g', 35: 'h', 36: 'j', 37: 'k', 38: 'l',
            44: 'z', 45: 'x', 46: 'c', 47: 'v', 48: 'b', 49: 'n', 50: 'm',
            12: '-', 13: '=', 26: '[', 27: ']', 39: ';', 40: "'", 41: '`',
            43: '\\', 51: ',', 52: '.', 53: '/', 57: ' '
        }
        
        # Configuration FINS
        self.setup_fins_config()
    
    # Méthode supprimée - utilise maintenant config_loader
    
    def setup_logging(self):
        """Configure le système de logging"""
        logging_config = self.config_loader.get_logging_config()
        if logging_config.get('enabled', True):
            log_level = getattr(logging, logging_config.get('level', 'INFO').upper())
            logging.basicConfig(
                level=log_level,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(logging_config.get('barcode_file', 'barcode_scanner.log')),
                    logging.StreamHandler()
                ]
            )
            self.logger = logging.getLogger(__name__)
        else:
            # Logger vide si désactivé
            self.logger = logging.getLogger(__name__)
            self.logger.addHandler(logging.NullHandler())
    
    def setup_fins_config(self):
        """Configure les paramètres FINS selon la configuration"""
        plc_config = self.config_loader.get_plc_config()
        
        # Zone mémoire
        if plc_config['memory_area'].lower() == 'data':
            self.area_code = b'\x82'  # Data Memory
        elif plc_config['memory_area'].lower() == 'work':
            self.area_code = b'\xB1'  # Work Area
        elif plc_config['memory_area'].lower() == 'holding':
            self.area_code = b'\xB2'  # Holding Area
        else:
            self.area_code = b'\x82'  # Par défaut Data Memory
        
        # Adresse mémoire
        address = plc_config['addresses']['barcode']
        self.memory_address = struct.pack('>HB', address, 0)  # Adresse + bit 0
    
    def connect_to_plc(self):
        """Établit la connexion avec le PLC"""
        plc_config = self.config_loader.get_plc_config()
        try:
            self.fins_instance = fins.tcp.TCPFinsConnection()
            self.fins_instance.connect(plc_config['ip'], plc_config['port'])
            
            message = f"✅ Connexion PLC établie : {plc_config['ip']}:{plc_config['port']}"
            print(message)
            self.logger.info(message)
            return True
        except Exception as e:
            message = f"❌ Erreur connexion PLC : {e}"
            print(message)
            self.logger.error(message)
            return False
    
    def write_barcode_to_plc(self, barcode):
        """Écrit le code-barres dans le PLC selon la configuration"""
        if not self.fins_instance:
            self.logger.error("Pas de connexion PLC active")
            return False
        
        try:
            # Convertir en nombre
            try:
                barcode_value = int(barcode)
            except ValueError:
                self.logger.error(f"Code-barres invalide : {barcode}")
                return False
            
            plc_config = self.config_loader.get_plc_config()
            data_type = plc_config.get('data_type', 'dword').lower()
            
            if data_type == 'word' or barcode_value <= 65535:
                # Écriture simple WORD
                write_data = struct.pack('>H', barcode_value)
                num_words = 1
                self.logger.info(f"Écriture WORD : {barcode_value}")
            else:
                # Écriture DWORD divisée
                barcode_str = str(barcode_value)
                if len(barcode_str) == 6:
                    part1 = int(barcode_str[:4])
                    part2 = int(barcode_str[4:])
                elif len(barcode_str) == 5:
                    part1 = int(barcode_str[:3])
                    part2 = int(barcode_str[3:])
                else:
                    mid = len(barcode_str) // 2
                    part1 = int(barcode_str[:mid])
                    part2 = int(barcode_str[mid:])
                
                write_data = struct.pack('>HH', part1, part2)
                num_words = 2
                self.logger.info(f"Écriture DWORD : D{plc_config['addresses']['barcode']}={part1}, D{plc_config['addresses']['barcode']+1}={part2}")
            
            # Écriture vers le PLC
            write_response = self.fins_instance.memory_area_write(
                self.area_code,
                self.memory_address,
                write_data,
                num_words
            )
            
            if write_response is None:
                self.logger.error(f"Timeout lors de l'écriture : {barcode}")
                return False
            elif len(write_response) >= 14:
                end_code = write_response[12:14]
                if end_code == b'\x00\x00':
                    message = f"✅ Code-barres {barcode} écrit avec succès"
                    print(message)
                    self.logger.info(message)
                    return True
                else:
                    error_code = end_code.hex()
                    self.logger.error(f"Erreur FINS : {error_code}")
                    return False
            else:
                self.logger.error("Réponse PLC invalide")
                return False
                
        except Exception as e:
            self.logger.error(f"Erreur lors de l'écriture : {e}")
            return False
    
    def find_barcode_device(self):
        """Trouve le périphérique d'entrée du lecteur de code-barres"""
        input_devices = glob.glob('/dev/input/event*')
        
        for device in input_devices:
            if os.access(device, os.R_OK):
                return device
        return None
    
    def process_event(self, data):
        """Traite un événement d'entrée"""
        timestamp_sec, timestamp_usec, type_, code, value = struct.unpack('llHHi', data)
        
        if type_ == 1 and value == 1:  # Key press
            current_time = time.time()
            
            # Reset si timeout dépassé
            if current_time - self.last_key_time > self.config['barcode']['timeout']:
                self.current_barcode = ""
            
            self.last_key_time = current_time
            
            # Touche Entrée (fin du code-barres)
            if code == 28:
                self.finalize_barcode()
            # Autres touches
            elif code in self.key_map:
                char = self.key_map[code]
                self.current_barcode += char
                print(f"\rSaisie : {self.current_barcode}", end="", flush=True)
    
    def finalize_barcode(self):
        """Finalise et traite le code-barres"""
        min_length = self.config['barcode']['min_length']
        
        if len(self.current_barcode) >= min_length:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            station = self.config['station']
            
            print(f"\n📱 [{timestamp}] Code-barres scanné : {self.current_barcode}")
            print(f"🏭 Station : {station['name']} ({station['id']})")
            
            # Envoyer au PLC
            if self.write_barcode_to_plc(self.current_barcode):
                print("🚀 Envoyé au PLC avec succès")
                self.logger.info(f"Code-barres {self.current_barcode} traité avec succès")
            else:
                print("⚠️  Échec de l'envoi au PLC")
                self.logger.warning(f"Échec envoi code-barres {self.current_barcode}")
            
            print("-" * 60)
        
        self.current_barcode = ""
    
    def read_input_events(self, device_path):
        """Lit les événements du périphérique d'entrée"""
        try:
            with open(device_path, 'rb') as device:
                print(f"🔍 Écoute sur {device_path}")
                print("📱 Scanner prêt (Ctrl+C pour quitter)")
                print("=" * 60)
                
                while True:
                    if select.select([device], [], [], 0.1)[0]:
                        data = device.read(24)
                        if len(data) == 24:
                            self.process_event(data)
                    
                    # Vérifier le timeout
                    current_time = time.time()
                    if (self.current_barcode and 
                        current_time - self.last_key_time > self.config['barcode']['timeout']):
                        self.finalize_barcode()
                        
        except PermissionError:
            message = f"❌ Erreur de permission pour {device_path}"
            print(message)
            print("💡 Essayez : sudo python3 barcode_scanner_configurable.py")
            self.logger.error(message)
        except Exception as e:
            message = f"❌ Erreur : {e}"
            print(message)
            self.logger.error(message)
    
    def display_config_info(self):
        """Affiche les informations de configuration"""
        station = self.config_loader.get_station_config()
        plc = self.config_loader.get_plc_config()
        
        print("🏭 === Scanner de Codes-barres Configurable ===")
        print(f"🏷️  Station : {station['name']} ({station['id']})")
        print(f"📝 Description : {station['description']}")
        print(f"🎯 PLC : {plc['ip']}:{plc['port']}")
        print(f"📍 Adresse : {plc['memory_area'].upper()}{plc['address']} ({plc['data_type'].upper()})")
        print("=" * 60)
    
    def start(self):
        """Démarre le scanner"""
        self.display_config_info()
        
        # Connexion au PLC
        if not self.connect_to_plc():
            print("❌ Impossible de se connecter au PLC")
            return
        
        # Recherche du lecteur
        device = self.find_barcode_device()
        if device:
            print(f"✅ Lecteur trouvé : {device}")
            self.read_input_events(device)
        else:
            print("❌ Aucun lecteur de code-barres trouvé")
    
    def __del__(self):
        """Nettoyage"""
        if self.fins_instance:
            self.logger.info("Fermeture connexion PLC")

def main():
    scanner = ConfigurableBarcodeScanner()
    try:
        scanner.start()
    except KeyboardInterrupt:
        print("\n\n⏹️  Scanner arrêté")
    except Exception as e:
        print(f"\n❌ Erreur : {e}")

if __name__ == "__main__":
    main() 