#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour envoyer une palette spécifique au PLC
=================================================

Envoie "FRE-39764-147332" à l'adresse D8570+ du PLC
"""

import sys
import os
import struct

# Ajouter le module fins au path
sys.path.append(os.path.join(os.path.dirname(__file__), 'fins'))
from fins.tcp import TCPFinsConnection

def send_palette_to_plc(palette_code, plc_ip="192.168.0.157", plc_port=9600):
    """
    Envoie une palette en format ASCII au PLC
    
    Args:
        palette_code (str): Code palette à envoyer
        plc_ip (str): Adresse IP du PLC
        plc_port (int): Port du PLC
    """
    
    print(f"🚀 === ENVOI PALETTE AU PLC ===")
    print(f"🎯 Palette: {palette_code}")
    print(f"🎯 PLC: {plc_ip}:{plc_port}")
    print(f"📍 Adresse: D8570-D8584 (15 mots)")
    print("=" * 50)
    
    # Configuration
    palette_address = 8570
    area_code = b'\x82'  # Data Memory
    fins_instance = None
    
    try:
        # 1. Connexion au PLC
        print("🔌 Connexion au PLC...")
        fins_instance = TCPFinsConnection()
        fins_instance.connect(plc_ip, plc_port)
        print("✅ Connexion PLC établie")
        
        # 2. Préparer la palette (30 caractères max)
        palette_padded = palette_code.ljust(30, '\x00')[:30]
        print(f"📝 Palette préparée: '{palette_code}' ({len(palette_code)} caractères)")
        
        # 3. Convertir en mots ASCII 16-bits
        print("🔄 Conversion en mots ASCII...")
        data = b''
        for i in range(0, len(palette_padded), 2):
            if i + 1 < len(palette_padded):
                char1 = ord(palette_padded[i])
                char2 = ord(palette_padded[i + 1])
                word = (char1 << 8) | char2
            else:
                char1 = ord(palette_padded[i])
                word = char1 << 8
            
            data += struct.pack('>H', word)
            
            # Afficher le détail des premiers mots
            if i < 10:
                c1 = palette_padded[i] if i < len(palette_code) else '\\0'
                c2 = palette_padded[i+1] if i+1 < len(palette_code) else '\\0'
                print(f"   D{palette_address + i//2}: 0x{word:04X} = '{c1}' + '{c2}'")
        
        # 4. Adresse mémoire PLC
        memory_address = struct.pack('>HB', palette_address, 0)
        
        # 5. Écriture vers le PLC
        print(f"\n📤 Écriture vers D{palette_address}+ (15 mots)...")
        response = fins_instance.memory_area_write(
            area_code, 
            memory_address, 
            data, 
            15  # 15 mots pour 30 caractères ASCII
        )
        
        if response:
            print("✅ SUCCÈS: Palette écrite dans le PLC!")
            print(f"✅ '{palette_code}' → D{palette_address}-D{palette_address+14}")
            
            # 6. Vérification par lecture
            print(f"\n🔍 Vérification par lecture...")
            read_response = fins_instance.memory_area_read(area_code, memory_address, 15)
            
            if read_response and len(read_response) >= 44:
                data_read = read_response[14:44]  # 30 bytes = 15 mots
                palette_str = ""
                
                for i in range(0, len(data_read), 2):
                    word = struct.unpack('>H', data_read[i:i+2])[0]
                    if word == 0:
                        break
                    char1 = chr((word >> 8) & 0xFF) if (word >> 8) & 0xFF > 0 else ''
                    char2 = chr(word & 0xFF) if word & 0xFF > 0 else ''
                    palette_str += char1 + char2
                
                palette_read = palette_str.strip()
                print(f"📖 Lu depuis PLC: '{palette_read}'")
                
                if palette_read == palette_code:
                    print("🎉 VÉRIFICATION RÉUSSIE: Les données correspondent!")
                else:
                    print(f"⚠️ ATTENTION: Différence détectée")
                    print(f"   Envoyé: '{palette_code}'")
                    print(f"   Lu: '{palette_read}'")
            
            return True
        else:
            print("❌ ERREUR: Échec de l'écriture PLC")
            return False
            
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        return False
    
    finally:
        if fins_instance:
            print("🔌 Fermeture connexion PLC")

def main():
    """Fonction principale"""
    # Palette à envoyer
    palette_target = "FRE-39764-147332"
    
    print("🎯 ENVOI PALETTE SPÉCIFIQUE AU PLC")
    print(f"Target: {palette_target}")
    print("")
    
    # Vérifier la longueur
    if len(palette_target) > 30:
        print(f"❌ ERREUR: Palette trop longue ({len(palette_target)} caractères, max 30)")
        return 1
    
    # Envoyer au PLC
    success = send_palette_to_plc(palette_target)
    
    if success:
        print("\n🎉 MISSION ACCOMPLIE!")
        print("=" * 40)
        print("✅ Palette envoyée avec succès au PLC")
        print("✅ InduSoft peut maintenant la lire depuis D8570+")
        print("✅ Le texte original apparaîtra en base de données")
        return 0
    else:
        print("\n❌ MISSION ÉCHOUÉE!")
        print("=" * 40)
        print("❌ Impossible d'envoyer la palette")
        return 1

if __name__ == "__main__":
    exit(main()) 