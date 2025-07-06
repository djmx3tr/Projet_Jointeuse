#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de détection de feuilles pour l'interface de production
Intégration avec le système d'alertes existant
"""

import sys
import os
import struct
import time
import threading
import requests
import logging
from datetime import datetime
import socketio
import base64
import cv2
import numpy as np

# Ajouter le module fins au path
sys.path.append(os.path.join(os.path.dirname(__file__), 'fins'))
from fins.tcp import TCPFinsConnection

# Configuration du logger - ERREURS SEULEMENT
logging.basicConfig(
    level=logging.ERROR,
    format='[%(asctime)s] %(levelname)s [%(name)s]: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("PaperDetection")

class PaperDetectionModule:
    """Module de détection de feuilles intégré à l'interface de production"""
    
    def __init__(self, interface_callback=None, config=None):
        """
        Initialise le module de détection
        
        Args:
            interface_callback: Fonction callback de l'interface principale pour les alertes
            config: Configuration depuis config.json
        """
        # Configuration par défaut
        default_config = {
            "plc": {"ip": "192.168.0.166", "port": 9600, "bit_address": "W160.00"},
            "inference_server": {"url": "http://192.168.0.71:5050"},
            "client_id": "PRODUCTION_INTERFACE_J1",
            "camera": {"device_id": 0, "width": 1280, "height": 720}
        }
        
        # Utiliser la configuration fournie ou celle par défaut
        self.config = config if config else default_config
        
        # Configuration PLC de détection
        self.detection_plc_ip = self.config['plc']['ip']
        self.detection_plc_port = self.config['plc']['port']
        self.detection_fins_instance = None
        
        # Configuration du bit d'activation - extraire le numéro depuis "W160.00"
        bit_address_str = self.config['plc']['bit_address']
        self.detection_bit_address = int(bit_address_str.replace('W', '').split('.')[0])  # 160 depuis W160.00
        self.work_bit_area_code = b'\x31'  # Work Bit Memory Area
        
        # Configuration du serveur d'inférence
        self.inference_server_url = self.config['inference_server']['url']
        self.client_id = self.config['client_id']
        
        # Configuration caméra
        self.camera_port = self.config['camera']['device_id']
        self.camera_width = self.config['camera']['width']
        self.camera_height = self.config['camera']['height']
        self.camera = None
        
        # Variables d'état
        self.running = False
        self.detection_active = False
        self.previous_bit_value = False
        self.interface_callback = interface_callback
        
        # Socket.IO pour communication avec serveur d'inférence
        self.sio = socketio.Client()
        self.detection_result = None
        self.detection_event = threading.Event()
        
        # Thread de surveillance
        self.monitor_thread = None
        
        # Module de détection de feuilles initialisé silencieusement
    
    def connect_to_detection_plc(self):
        """Connexion au PLC de détection"""
        try:
            self.detection_fins_instance = TCPFinsConnection()
            self.detection_fins_instance.connect(self.detection_plc_ip, self.detection_plc_port)
            return True
        except Exception as e:
            logger.error(f"Erreur connexion PLC détection {self.detection_plc_ip}: {e}")
            return False
    
    def initialize_camera(self):
        """Initialise la caméra"""
        try:
            logger.info(f"Initialisation caméra port {self.camera_port}")
            self.camera = cv2.VideoCapture(self.camera_port)
            
            if not self.camera.isOpened():
                logger.warning("Caméra non disponible - Module de détection désactivé")
                self.camera = None
                return False
            
            # Configuration de la caméra
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            
            # NOUVEAU : Configuration pour éviter les images figées
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Buffer minimal
            self.camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Auto exposition
            
            # Attendre que la caméra se stabilise
            time.sleep(1)
            
            # Test de capture avec vidage du buffer
            logger.info("Test initial de la caméra avec vidage du buffer...")
            for i in range(3):  # Capturer 3 images pour tester
                ret, frame = self.camera.read()
                if not ret:
                    logger.error(f"Impossible de capturer l'image de test {i+1}")
                    if i == 0:  # Si même la première échoue
                        return False
                time.sleep(0.2)
            
            logger.info("Caméra initialisée avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur initialisation caméra: {e}")
            return False
    
    def setup_socketio(self):
        """Configure Socket.IO pour le serveur d'inférence"""
        try:
            @self.sio.event
            def connect():
                logger.info("Socket.IO connecté au serveur d'inférence")
                
            @self.sio.event
            def disconnect():
                logger.info("Socket.IO déconnecté du serveur d'inférence")
                
            @self.sio.on('detection_result')
            def on_detection_result(data):
                self.detection_result = data
                self.detection_event.set()
            
            # Connexion au serveur
            self.sio.connect(self.inference_server_url)
            logger.info("Socket.IO configuré et connecté")
            return True
            
        except Exception as e:
            logger.error(f"Erreur configuration Socket.IO: {e}")
            return False
    
    def read_detection_bit(self):
        """Lit le bit de détection W160.00"""
        try:
            if not self.detection_fins_instance:
                return False
            
            # Lire W160.00
            detection_address = struct.pack('>HB', self.detection_bit_address, 0)  # W160.00
            response = self.detection_fins_instance.memory_area_read(
                self.work_bit_area_code, detection_address, 1
            )
            
            if response and len(response) >= 15:
                bit_data = response[14]
                current_bit_value = bool(bit_data & 0x01)
                return current_bit_value
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur lecture bit détection: {e}")
            return False
    
    def capture_and_detect(self):
        """Capture une image et effectue la détection"""
        try:
            if not self.camera:
                logger.error("Caméra non initialisée")
                return False
            
            # NOUVEAU : Vider le buffer de la caméra pour avoir une image fraîche
            logger.info("Vidage du buffer caméra pour image fraîche...")
            for i in range(5):  # Lire 5 images pour vider le buffer
                ret, frame = self.camera.read()
                if not ret:
                    logger.error(f"Impossible de capturer l'image {i+1}/5")
                    if i == 0:  # Si même la première échoue
                        return False
                time.sleep(0.1)  # 100ms entre chaque capture
            
            # Maintenant capturer l'image finale
            ret, frame = self.camera.read()
            if not ret:
                logger.error("Impossible de capturer l'image finale")
                return False
            
            # Image capturée sans modification
            
            # Encoder l'image pour l'envoi
            _, img_encoded = cv2.imencode('.jpg', frame)
            image_base64 = base64.b64encode(img_encoded.tobytes()).decode('utf-8')
            
            # Préparer le message pour le serveur d'inférence
            message = {
                "image": image_base64,
                "client_id": self.client_id,
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
            }
            
            # Réinitialiser l'événement de détection
            self.detection_event.clear()
            self.detection_result = None
            
            # Envoyer au serveur d'inférence
            self.sio.emit('detect_image', message)
            
            # Attendre la réponse (timeout 5 secondes)
            if self.detection_event.wait(timeout=5.0):
                # Analyser le résultat
                detections = self.detection_result.get("detections", [])
                
                # Vérifier si une feuille a été détectée
                paper_detected = len(detections) > 0
                
                if paper_detected:
                    logger.info(f"Feuille détectée ! Nombre de détections: {len(detections)}")
                    
                    # Notifier l'interface principale
                    if self.interface_callback:
                        self.interface_callback(True)  # Activer l'alerte
                    
                    return True
                else:
                    logger.info("Aucune feuille détectée")
                    return False
            else:
                logger.error("Timeout lors de la détection")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors de la capture et détection: {e}")
            return False
    
    def monitor_detection_loop(self):
        """Boucle de surveillance du bit de détection"""
        logger.info("Démarrage de la surveillance de détection")
        
        while self.running:
            try:
                # Lire le bit de détection
                current_bit_value = self.read_detection_bit()
                
                # Détecter le front montant (passage de False à True)
                if current_bit_value and not self.previous_bit_value:
                    logger.info("Front montant détecté sur W160.00 - Démarrage détection")
                    
                    # Lancer la détection
                    detection_result = self.capture_and_detect()
                    
                    if detection_result:
                        logger.info("Détection positive - Alerte activée")
                        self.detection_active = True
                    else:
                        logger.info("Détection négative")
                        self.detection_active = False
                
                # Mémoriser l'état précédent
                self.previous_bit_value = current_bit_value
                
                # Attendre avant la prochaine lecture
                time.sleep(0.1)  # 100ms
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle de surveillance: {e}")
                time.sleep(1.0)  # Attendre plus longtemps en cas d'erreur
        
        logger.info("Arrêt de la surveillance de détection")
    
    def start(self):
        """Démarre le module de détection"""
        try:
            logger.info("Démarrage du module de détection")
            
            # Connexion au PLC de détection
            if not self.connect_to_detection_plc():
                logger.warning("PLC de détection non accessible - Module désactivé")
                return False
            
            # Initialisation de la caméra
            if not self.initialize_camera():
                logger.warning("Caméra non accessible - Module désactivé")
                return False
            
            # Configuration Socket.IO
            if not self.setup_socketio():
                logger.warning("Serveur d'inférence non accessible - Module désactivé")
                return False
            
            # Démarrer la surveillance
            self.running = True
            self.monitor_thread = threading.Thread(target=self.monitor_detection_loop)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            logger.info("Module de détection démarré avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du démarrage: {e}")
            return False
    
    def stop(self):
        """Arrête le module de détection"""
        logger.info("Arrêt du module de détection")
        
        self.running = False
        
        # Arrêter le thread de surveillance
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        
        # Fermer la caméra
        if self.camera:
            self.camera.release()
        
        # Fermer la connexion PLC
        if self.detection_fins_instance:
            try:
                self.detection_fins_instance.close()
            except:
                pass
        
        # Fermer Socket.IO
        if self.sio.connected:
            self.sio.disconnect()
        
        logger.info("Module de détection arrêté")
    
    def is_detection_active(self):
        """Retourne True si une détection est active"""
        return self.detection_active
    
    def clear_detection(self):
        """Efface l'état de détection active"""
        self.detection_active = False
        logger.info("État de détection effacé") 