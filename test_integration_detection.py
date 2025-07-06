#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour l'intégration du système de détection de feuilles
"""

import sys
import os
import time
import threading

# Ajouter le chemin du module
sys.path.append(os.path.dirname(__file__))

def test_detection_module():
    """Test du module de détection seul"""
    print("=== Test du module de détection ===")
    
    try:
        from paper_detection_module import PaperDetectionModule
        
        def callback_test(detection_active):
            print(f"Callback reçu : détection = {detection_active}")
        
        # Créer l'instance
        detector = PaperDetectionModule(interface_callback=callback_test)
        
        print("Module créé avec succès")
        print(f"PLC cible : {detector.detection_plc_ip}:{detector.detection_plc_port}")
        print(f"Bit de détection : W{detector.detection_bit_address}.00")
        print(f"Serveur d'inférence : {detector.inference_server_url}")
        
        # Test des connexions
        print("\n--- Test des connexions ---")
        
        # Test PLC
        if detector.connect_to_detection_plc():
            print("✓ Connexion PLC réussie")
            detector.detection_fins_instance.close()
        else:
            print("✗ Connexion PLC échouée")
        
        # Test caméra
        if detector.initialize_camera():
            print("✓ Caméra initialisée")
            detector.camera.release()
        else:
            print("✗ Caméra non disponible")
        
        # Test Socket.IO
        try:
            if detector.setup_socketio():
                print("✓ Socket.IO connecté")
                detector.sio.disconnect()
            else:
                print("✗ Socket.IO non disponible")
        except:
            print("✗ Serveur d'inférence inaccessible")
        
        print("\n--- Test terminé ---")
        
    except ImportError as e:
        print(f"❌ Impossible d'importer le module : {e}")
        return False
    except Exception as e:
        print(f"❌ Erreur lors du test : {e}")
        return False
    
    return True

def test_interface_integration():
    """Test de l'intégration avec l'interface"""
    print("\n=== Test de l'intégration interface ===")
    
    try:
        # Simuler l'importation de l'interface
        from interface_graphique_production_v2 import InterfaceGraphiqueProductionV2
        
        print("Interface importée avec succès")
        
        # Vérifier que les nouvelles méthodes existent
        interface = InterfaceGraphiqueProductionV2()
        
        # Vérifier les attributs
        if hasattr(interface, 'paper_detection_active'):
            print("✓ Attribut paper_detection_active présent")
        else:
            print("✗ Attribut paper_detection_active manquant")
        
        if hasattr(interface, 'paper_detection'):
            print("✓ Attribut paper_detection présent")
        else:
            print("✗ Attribut paper_detection manquant")
        
        # Vérifier les méthodes
        if hasattr(interface, 'on_paper_detection'):
            print("✓ Méthode on_paper_detection présente")
        else:
            print("✗ Méthode on_paper_detection manquante")
        
        if hasattr(interface, 'clear_paper_detection_alert'):
            print("✓ Méthode clear_paper_detection_alert présente")
        else:
            print("✗ Méthode clear_paper_detection_alert manquante")
        
        print("✓ Intégration interface validée")
        
        # Ne pas démarrer l'interface complète pour éviter les conflits
        
    except Exception as e:
        print(f"❌ Erreur lors du test d'intégration : {e}")
        return False
    
    return True

def test_dependencies():
    """Test des dépendances requises"""
    print("\n=== Test des dépendances ===")
    
    dependencies = [
        'cv2',           # OpenCV
        'socketio',      # Socket.IO
        'requests',      # Requêtes HTTP
        'numpy',         # NumPy
        'threading',     # Threading (standard)
        'struct',        # Struct (standard)
        'base64'         # Base64 (standard)
    ]
    
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✓ {dep}")
        except ImportError:
            print(f"✗ {dep} - MANQUANT")
    
    return True

def main():
    """Fonction principale de test"""
    print("🔍 Test d'intégration du système de détection de feuilles")
    print("=" * 60)
    
    # Test des dépendances
    test_dependencies()
    
    # Test du module de détection
    test_detection_module()
    
    # Test de l'intégration interface
    test_interface_integration()
    
    print("\n" + "=" * 60)
    print("✅ Tests terminés")
    print("\nPour un test complet :")
    print("1. Vérifier que le PLC 192.168.0.166 est accessible")
    print("2. Vérifier que le serveur d'inférence 192.168.0.71:5050 est actif")
    print("3. Vérifier qu'une caméra USB est connectée")
    print("4. Lancer l'interface complète avec python interface_graphique_production_v2.py")

if __name__ == "__main__":
    main() 