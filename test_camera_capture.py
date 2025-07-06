#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour vérifier la capture de nouvelles images par la caméra
"""

import cv2
import time
import os
from datetime import datetime

def test_camera_captures():
    """Test de captures multiples pour vérifier que les images changent"""
    print("🔍 Test de capture caméra - Vérification images fraîches")
    print("=" * 60)
    
    # Initialiser la caméra
    camera = cv2.VideoCapture(0)
    
    if not camera.isOpened():
        print("❌ Impossible d'ouvrir la caméra")
        return False
    
    # Configuration
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    camera.set(cv2.CAP_PROP_FPS, 30)
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Buffer minimal
    
    print("✓ Caméra initialisée")
    time.sleep(1)  # Laisser la caméra se stabiliser
    
    # Créer le dossier de test
    test_dir = "test_captures"
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    
    print(f"📁 Images sauvegardées dans: {test_dir}/")
    print("\n🔄 Test de 5 captures espacées...")
    
    for i in range(5):
        print(f"\n--- Capture {i+1}/5 ---")
        
        # Vider le buffer (comme dans le module de détection)
        print("Vidage du buffer...")
        for j in range(3):
            ret, frame = camera.read()
            if not ret:
                print(f"❌ Erreur lecture buffer {j+1}")
            time.sleep(0.1)
        
        # Capture finale
        ret, frame = camera.read()
        if not ret:
            print(f"❌ Erreur capture finale {i+1}")
            continue
        
        # Ajouter timestamp sur l'image
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        cv2.putText(frame, f"Test {i+1} - {timestamp}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Sauvegarder
        filename = f"{test_dir}/test_capture_{i+1}_{timestamp.replace(':', '-')}.jpg"
        cv2.imwrite(filename, frame)
        
        print(f"✓ Image {i+1} sauvegardée: {filename}")
        print(f"  Timestamp: {timestamp}")
        print(f"  Taille: {frame.shape}")
        
        # Attendre 3 secondes entre captures
        if i < 4:  # Pas d'attente après la dernière
            print("⏰ Attente 3 secondes...")
            time.sleep(3)
    
    camera.release()
    
    print("\n" + "=" * 60)
    print("✅ Test terminé !")
    print(f"\n📋 Vérifiez manuellement les images dans {test_dir}/")
    print("   - Les timestamps doivent être différents")
    print("   - Les images doivent montrer le mouvement/changements")
    print("   - Si toutes identiques → problème de buffer caméra")
    
    return True

def test_detection_simulation():
    """Simule une détection complète comme le ferait le module"""
    print("\n" + "=" * 60)
    print("🎯 Simulation détection complète")
    print("=" * 60)
    
    try:
        from paper_detection_module import PaperDetectionModule
        
        def callback_test(detection_active):
            print(f"📢 Callback reçu: détection = {detection_active}")
        
        # Créer le module
        detector = PaperDetectionModule(interface_callback=callback_test)
        
        print("✓ Module créé")
        
        # Initialiser seulement la caméra
        if detector.initialize_camera():
            print("✓ Caméra initialisée")
            
            # Test de capture
            print("\n🔄 Test de capture avec le module...")
            result = detector.capture_and_detect()
            print(f"Résultat capture: {result}")
            
            # Nettoyage
            detector.camera.release()
        else:
            print("❌ Échec initialisation caméra")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")

def main():
    """Fonction principale"""
    print("📷 Test complet de capture caméra")
    print("Appuyez sur Ctrl+C pour arrêter")
    
    try:
        # Test 1: Captures basiques
        test_camera_captures()
        
        # Test 2: Avec le module de détection
        test_detection_simulation()
        
    except KeyboardInterrupt:
        print("\n⏹️  Test arrêté par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")

if __name__ == "__main__":
    main() 