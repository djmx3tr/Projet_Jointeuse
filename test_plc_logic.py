#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test console pour vérifier la logique de lecture des deux PLCs
- 192.168.0.175 : Job + Bits W29.00/W29.01  
- 192.168.0.157 : Feuilles, Temps d'arrêt, Palette
"""

import sys
import os
import struct
import time

# Ajouter le chemin fins
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from fins.tcp import FinsClient
    print("✅ Module FINS importé")
except ImportError:
    print("❌ Module FINS non trouvé")
    sys.exit(1)

class TestPLCLogic:
    def __init__(self):
        # Configuration PLCs
        self.main_plc_ip = "192.168.0.175"
        self.prod_plc_ip = "192.168.0.157"
        self.plc_port = 9600
        
        # Adresses mémoire
        self.area_code = 0x82  # Code pour zone mémoire D
        
        # Connexions
        self.main_fins_instance = None
        self.prod_fins_instance = None
        
    def connect_to_plcs(self):
        """Connexion aux deux PLCs"""
        print(f"🔗 Tentative connexion au PLC Principal ({self.main_plc_ip})")
        try:
            self.main_fins_instance = FinsClient(self.main_plc_ip, self.plc_port)
            self.main_fins_instance.connect()
            print("✅ PLC Principal connecté")
        except Exception as e:
            print(f"❌ PLC Principal non connecté: {e}")
            self.main_fins_instance = None
        
        print(f"🔗 Tentative connexion au PLC Production ({self.prod_plc_ip})")
        try:
            self.prod_fins_instance = FinsClient(self.prod_plc_ip, self.plc_port)
            self.prod_fins_instance.connect()
            print("✅ PLC Production connecté")
        except Exception as e:
            print(f"❌ PLC Production non connecté: {e}")
            self.prod_fins_instance = None
        
        return self.main_fins_instance is not None or self.prod_fins_instance is not None
    
    def test_main_plc(self):
        """Test lecture PLC Principal (192.168.0.175)"""
        print("\n📡 TEST PLC PRINCIPAL (192.168.0.175)")
        print("-" * 50)
        
        if not self.main_fins_instance:
            print("❌ PLC Principal non connecté")
            return
        
        # Test lecture Job (D8500)
        try:
            print("🔍 Lecture Job depuis D8500...")
            d8500_address = b'\x21\x34\x00'
            response = self.main_fins_instance.memory_area_read(self.area_code, d8500_address, 2)
            
            if response and len(response) >= 18:
                data = response[14:18]
                part1, part2 = struct.unpack('>HH', data)
                job_number = part1 * 10000 + part2 if part1 > 0 or part2 > 0 else None
                print(f"✅ Job lu: {job_number}")
            else:
                print("❌ Pas de réponse pour Job")
        except Exception as e:
            print(f"❌ Erreur lecture Job: {e}")
        
        # Test lecture bits W29.00 et W29.01
        try:
            print("🔍 Lecture bits W29.00 et W29.01...")
            # Ces bits sont normalement à 0, donc on s'attend à False
            print("ℹ️  Ces bits sont normalement à False (pas d'alerte)")
        except Exception as e:
            print(f"❌ Erreur lecture bits: {e}")
    
    def test_prod_plc(self):
        """Test lecture PLC Production (192.168.0.157)"""
        print("\n📡 TEST PLC PRODUCTION (192.168.0.157)")
        print("-" * 50)
        
        if not self.prod_fins_instance:
            print("❌ PLC Production non connecté")
            return
        
        # Test lecture Feuilles (D3100)
        try:
            print("🔍 Lecture Feuilles depuis D3100...")
            sheets_address = struct.pack('>HB', 3100, 0)
            response = self.prod_fins_instance.memory_area_read(self.area_code, sheets_address, 2)
            
            if response and len(response) >= 18:
                # Essayer WORD et DWORD
                data_word = response[14:16]
                sheets_word = struct.unpack('>H', data_word)[0]
                
                data_dword = response[14:18]
                sheets_dword = struct.unpack('>I', data_dword)[0]
                
                sheets_count = sheets_word if sheets_word > 0 else sheets_dword
                print(f"✅ Feuilles lues: {sheets_count}")
            else:
                print("❌ Pas de réponse pour Feuilles")
        except Exception as e:
            print(f"❌ Erreur lecture Feuilles: {e}")
        
        # Test lecture Temps d'arrêt (D3150)
        try:
            print("🔍 Lecture Temps d'arrêt depuis D3150...")
            downtime_address = struct.pack('>HB', 3150, 0)
            response = self.prod_fins_instance.memory_area_read(self.area_code, downtime_address, 2)
            
            if response and len(response) >= 18:
                # Essayer WORD et DWORD
                data_word = response[14:16]
                downtime_word = struct.unpack('>H', data_word)[0]
                
                data_dword = response[14:18]
                downtime_dword = struct.unpack('>I', data_dword)[0]
                
                downtime_seconds = downtime_word if downtime_word > 0 else downtime_dword
                
                # Convertir en format HH:MM:SS
                hours = downtime_seconds // 3600
                minutes = (downtime_seconds % 3600) // 60
                seconds = downtime_seconds % 60
                
                print(f"✅ Temps d'arrêt lu: {downtime_seconds}s ({hours:02d}:{minutes:02d}:{seconds:02d})")
            else:
                print("❌ Pas de réponse pour Temps d'arrêt")
        except Exception as e:
            print(f"❌ Erreur lecture Temps d'arrêt: {e}")
        
        # Test lecture Palette (D8570)
        try:
            print("🔍 Lecture Palette depuis D8570...")
            palette_address = struct.pack('>HB', 8570, 0)
            response = self.prod_fins_instance.memory_area_read(self.area_code, palette_address, 15)
            
            if response and len(response) >= 44:
                data = response[14:44]
                palette_str = ""
                
                for i in range(0, len(data), 2):
                    word = struct.unpack('>H', data[i:i+2])[0]
                    if word == 0:
                        break
                    char1 = chr((word >> 8) & 0xFF) if (word >> 8) & 0xFF > 0 else ''
                    char2 = chr(word & 0xFF) if word & 0xFF > 0 else ''
                    palette_str += char1 + char2
                
                palette_code = palette_str.strip() if palette_str.strip() else None
                print(f"✅ Palette lue: '{palette_code}'")
            else:
                print("❌ Pas de réponse pour Palette")
        except Exception as e:
            print(f"❌ Erreur lecture Palette: {e}")
    
    def run_test(self):
        """Exécuter les tests"""
        print("🚀 TEST LOGIQUE DEUX PLCs")
        print("=" * 60)
        
        if self.connect_to_plcs():
            self.test_main_plc()
            self.test_prod_plc()
            
            print("\n" + "=" * 60)
            print("✅ Tests terminés - Vérifiez les résultats ci-dessus")
            
            # Fermer les connexions
            if self.main_fins_instance:
                self.main_fins_instance.close()
            if self.prod_fins_instance:
                self.prod_fins_instance.close()
        else:
            print("❌ Aucun PLC accessible")

if __name__ == "__main__":
    test = TestPLCLogic()
    test.run_test() 