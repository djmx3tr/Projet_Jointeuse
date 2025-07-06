#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test du Système Palette HEX
============================

Script pour tester l'envoi et la lecture des palettes en format HEX
Compatible avec InduSoft
"""

import sys
import os
import struct
import zlib
import time

# Ajouter le module fins au path
sys.path.append(os.path.join(os.path.dirname(__file__), 'fins'))
from fins.tcp import TCPFinsConnection

class PaletteHexTester:
    def __init__(self, plc_ip="192.168.0.157", plc_port=9600):
        self.plc_ip = plc_ip
        self.plc_port = plc_port
        self.fins_instance = None
        self.area_code = b'\x82'
        self.palette_address = 8570  # D8570-D8571
        
        print("🧪 === TEST SYSTÈME PALETTE HEX ===")
        print(f"🎯 PLC: {self.plc_ip}:{self.plc_port}")
        print(f"📍 Adresses: D{self.palette_address}-D{self.palette_address+1}")
        print("=" * 60)
    
    def connect_to_plc(self):
        """Connexion au PLC"""
        try:
            self.fins_instance = TCPFinsConnection()
            self.fins_instance.connect(self.plc_ip, self.plc_port)
            print(f"✅ Connexion PLC établie")
            return True
        except Exception as e:
            print(f"❌ Erreur connexion PLC: {e}")
            return False
    
    def palette_to_hex(self, palette_code):
        """Convertit palette en HEX (CRC32)"""
        return zlib.crc32(palette_code.encode('utf-8')) & 0xffffffff
    
    def write_palette_hex(self, palette_code):
        """Écrit palette en format HEX dans le PLC"""
        try:
            # Convertir en HEX
            hex_value = self.palette_to_hex(palette_code)
            
            # Diviser en 2 mots
            high_word = (hex_value >> 16) & 0xFFFF
            low_word = hex_value & 0xFFFF
            
            print(f"📝 Écriture: '{palette_code}' → 0x{hex_value:08X}")
            print(f"   D{self.palette_address}: 0x{high_word:04X} ({high_word})")
            print(f"   D{self.palette_address+1}: 0x{low_word:04X} ({low_word})")
            
            # Préparer les données
            data = struct.pack('>HH', high_word, low_word)
            memory_address = struct.pack('>HB', self.palette_address, 0)
            
            # Écrire au PLC
            response = self.fins_instance.memory_area_write(
                self.area_code, memory_address, data, 2
            )
            
            if response:
                print(f"✅ Palette écrite avec succès")
                return hex_value
            else:
                print(f"❌ Erreur écriture PLC")
                return None
                
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return None
    
    def read_palette_hex(self):
        """Lit la palette HEX depuis le PLC"""
        try:
            memory_address = struct.pack('>HB', self.palette_address, 0)
            response = self.fins_instance.memory_area_read(self.area_code, memory_address, 2)
            
            if response and len(response) >= 18:
                data = response[14:18]
                high_word, low_word = struct.unpack('>HH', data)
                hex_value = (high_word << 16) | low_word
                
                print(f"📖 Lecture PLC:")
                print(f"   D{self.palette_address}: 0x{high_word:04X} ({high_word})")
                print(f"   D{self.palette_address+1}: 0x{low_word:04X} ({low_word})")
                print(f"   Valeur reconstituée: 0x{hex_value:08X} ({hex_value})")
                
                return hex_value
            else:
                print("❌ Erreur lecture PLC")
                return None
                
        except Exception as e:
            print(f"❌ Erreur lecture: {e}")
            return None
    
    def test_complete_cycle(self, palette_code):
        """Test complet: écriture + lecture + vérification"""
        print(f"\n🔄 TEST COMPLET: {palette_code}")
        print("-" * 50)
        
        # 1. Écriture
        written_hex = self.write_palette_hex(palette_code)
        if not written_hex:
            return False
        
        # 2. Attendre un peu
        time.sleep(0.5)
        
        # 3. Lecture
        read_hex = self.read_palette_hex()
        if not read_hex:
            return False
        
        # 4. Vérification
        if written_hex == read_hex:
            print(f"✅ SUCCÈS: Valeurs correspondent (0x{written_hex:08X})")
            return True
        else:
            print(f"❌ ERREUR: Écrit=0x{written_hex:08X}, Lu=0x{read_hex:08X}")
            return False
    
    def simulate_indusoft_read(self):
        """Simule la lecture InduSoft"""
        print(f"\n🏭 SIMULATION INDUSOFT")
        print("-" * 30)
        
        hex_value = self.read_palette_hex()
        if hex_value and hex_value > 0:
            print(f"💡 Code InduSoft VBScript:")
            print(f"   HighWord = ReadTag(\"D{self.palette_address}\")  ' {(hex_value >> 16) & 0xFFFF}")
            print(f"   LowWord = ReadTag(\"D{self.palette_address+1}\")   ' {hex_value & 0xFFFF}")
            print(f"   PaletteHex = (HighWord * 65536) + LowWord  ' {hex_value}")
            print(f"\n💾 Requête SQL InduSoft:")
            print(f"   INSERT INTO TABLE_FEUILLES (NO_PALETTE, ...) VALUES ({hex_value}, ...)")
            return hex_value
        else:
            print("❓ Aucune palette détectée")
            return None
    
    def run_tests(self):
        """Lance tous les tests"""
        if not self.connect_to_plc():
            return False
        
        # Palettes de test
        test_palettes = [
            "PAL-123456",
            "FRE-39764-147332",
            "BOJ-45678",
            "SAP-987654-ABC123",
            "TEST-999"
        ]
        
        success_count = 0
        
        for palette in test_palettes:
            if self.test_complete_cycle(palette):
                success_count += 1
        
        # Test de lecture InduSoft
        self.simulate_indusoft_read()
        
        # Résultats
        print(f"\n📊 RÉSULTATS FINAUX")
        print("=" * 40)
        print(f"Tests réussis: {success_count}/{len(test_palettes)}")
        print(f"Taux de succès: {(success_count/len(test_palettes)*100):.1f}%")
        
        if success_count == len(test_palettes):
            print("🎉 TOUS LES TESTS RÉUSSIS!")
            print("\n✅ SYSTÈME PRÊT POUR INDUSOFT:")
            print("- Les palettes sont converties en HEX (CRC32)")
            print("- Stockées dans D8570-D8571 (2 mots)")
            print("- InduSoft peut lire directement ces valeurs")
            print("- Utiliser la valeur HEX comme NO_PALETTE en BD")
        else:
            print("⚠️ Certains tests ont échoué")
        
        return success_count == len(test_palettes)

def main():
    """Fonction principale"""
    tester = PaletteHexTester()
    
    try:
        success = tester.run_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n🛑 Test interrompu par l'utilisateur")
        return 1
    except Exception as e:
        print(f"\n❌ Erreur générale: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 