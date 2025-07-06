#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Guide InduSoft - Utilisation des Palettes en Format HEX
=======================================================

Ce script explique comment InduSoft peut lire les valeurs HEX des palettes 
depuis le PLC et les utiliser dans la base de données.

ADRESSES PLC POUR INDUSOFT:
- D8570: High Word de la valeur HEX palette (16 bits)  
- D8571: Low Word de la valeur HEX palette (16 bits)

RECONSTRUCTION DE LA VALEUR HEX:
palette_hex_value = (D8570 << 16) | D8571

UTILISATION EN BASE DE DONNÉES:
La valeur HEX peut être utilisée directement comme identifiant unique de palette
"""

import zlib
import json
import struct
from datetime import datetime

def palette_to_hex(palette_code):
    """
    Convertit un code palette en valeur HEX (CRC32)
    Utilisé par l'interface Python avant envoi au PLC
    
    Args:
        palette_code (str): Code palette (ex: "PAL-123456")
        
    Returns:
        int: Valeur HEX 32-bits
    """
    return zlib.crc32(palette_code.encode('utf-8')) & 0xffffffff

def hex_to_plc_words(hex_value):
    """
    Divise une valeur HEX 32-bits en 2 mots 16-bits pour le PLC
    
    Args:
        hex_value (int): Valeur HEX 32-bits
        
    Returns:
        tuple: (high_word, low_word) pour D8570 et D8571
    """
    high_word = (hex_value >> 16) & 0xFFFF
    low_word = hex_value & 0xFFFF
    return high_word, low_word

def plc_words_to_hex(high_word, low_word):
    """
    Reconstruit la valeur HEX à partir de 2 mots PLC
    FONCTION POUR INDUSOFT
    
    Args:
        high_word (int): Valeur de D8570
        low_word (int): Valeur de D8571
        
    Returns:
        int: Valeur HEX 32-bits reconstituée
    """
    return (high_word << 16) | low_word

def create_indusoft_example():
    """
    Crée un exemple d'utilisation pour InduSoft
    """
    examples = []
    
    # Exemples de palettes typiques
    test_palettes = [
        "PAL-123456",
        "FRE-39764-147332", 
        "BOJ-45678",
        "SAP-987654-ABC123"
    ]
    
    print("=" * 80)
    print("EXEMPLES POUR INDUSOFT - PALETTES HEX")
    print("=" * 80)
    print(f"{'Palette':<25} {'HEX Value':<12} {'D8570':<8} {'D8571':<8} {'SQL Insert'}")
    print("-" * 80)
    
    for palette in test_palettes:
        hex_val = palette_to_hex(palette)
        high, low = hex_to_plc_words(hex_val)
        
        # Exemple SQL pour InduSoft
        sql_example = f"INSERT INTO TABLE_FEUILLES (NO_PALETTE, ...) VALUES ({hex_val}, ...)"
        
        print(f"{palette:<25} 0x{hex_val:08X} {high:<8} {low:<8}")
        print(f"  SQL: {sql_example}")
        print()
        
        examples.append({
            'palette_code': palette,
            'hex_value': hex_val,
            'hex_string': f"0x{hex_val:08X}",
            'plc_high_word': high,
            'plc_low_word': low,
            'sql_value': hex_val
        })
    
    return examples

def create_indusoft_vbscript_functions():
    """
    Génère des fonctions VBScript pour InduSoft
    """
    vbscript = '''
' ===================================================================
' FONCTIONS VBSCRIPT POUR INDUSOFT - GESTION PALETTES HEX
' ===================================================================

' Fonction pour reconstituer la valeur HEX palette depuis le PLC
Function GetPaletteHexFromPLC()
    Dim HighWord, LowWord, PaletteHex
    
    ' Lire les registres PLC D8570 et D8571
    HighWord = ReadTag("D8570")  ' High Word
    LowWord = ReadTag("D8571")   ' Low Word
    
    ' Reconstituer la valeur HEX 32-bits
    PaletteHex = (HighWord * 65536) + LowWord  ' (HighWord << 16) | LowWord
    
    GetPaletteHexFromPLC = PaletteHex
End Function

' Fonction pour insérer en base de données
Function InsertSheetWithPaletteHex(JobNumber, NbJoint, NbCoupon)
    Dim PaletteHex, SQL, Timestamp
    
    ' Obtenir la valeur HEX de la palette
    PaletteHex = GetPaletteHexFromPLC()
    
    ' Créer le timestamp
    Timestamp = Now()
    
    ' Construire la requête SQL
    SQL = "INSERT INTO dbo.TABLE_FEUILLES " & _
          "(TIMESTAMP, NO_JOB, NO_PALETTE, NB_JOINT, NB_COUPON) " & _
          "VALUES ('" & Timestamp & "', " & JobNumber & ", " & PaletteHex & ", " & NbJoint & ", " & NbCoupon & ")"
    
    ' Exécuter la requête (adapter selon votre connexion DB)
    ExecuteSQL(SQL)
    
    InsertSheetWithPaletteHex = True
End Function

' Fonction pour vérifier si une palette est active
Function IsPaletteActive()
    Dim PaletteHex
    PaletteHex = GetPaletteHexFromPLC()
    
    ' Si > 0, une palette est scannée
    IsPaletteActive = (PaletteHex > 0)
End Function
'''
    
    return vbscript

def save_indusoft_guide():
    """
    Sauvegarde le guide complet pour InduSoft
    """
    # Créer les exemples
    examples = create_indusoft_example()
    
    # Créer le VBScript
    vbscript = create_indusoft_vbscript_functions()
    
    # Guide complet
    guide = {
        'titre': 'Guide InduSoft - Palettes HEX',
        'description': 'Utilisation des valeurs HEX des palettes avec InduSoft',
        'adresses_plc': {
            'D8570': 'High Word (16 bits supérieurs)',
            'D8571': 'Low Word (16 bits inférieurs)'
        },
        'reconstruction': 'palette_hex = (D8570 << 16) | D8571',
        'exemples': examples,
        'vbscript': vbscript,
        'notes': [
            'Les valeurs HEX sont uniques pour chaque palette',
            'Utiliser directement en base de données comme identifiant',
            'Plus efficace que les chaînes ASCII (2 mots vs 15)',
            'Compatible avec tous les formats de palette'
        ]
    }
    
    # Sauvegarder en JSON
    with open('indusoft_palette_hex_guide.json', 'w') as f:
        json.dump(guide, f, indent=2, ensure_ascii=False)
    
    # Sauvegarder le VBScript séparément
    with open('indusoft_palette_functions.vbs', 'w') as f:
        f.write(vbscript)
    
    print("\n" + "=" * 60)
    print("FICHIERS CRÉÉS POUR INDUSOFT:")
    print("=" * 60)
    print("✓ indusoft_palette_hex_guide.json - Guide complet")
    print("✓ indusoft_palette_functions.vbs - Fonctions VBScript")
    print("\nCONFIGURATION INDUSOFT:")
    print("- Lire D8570 et D8571 depuis le PLC")
    print("- Utiliser: palette_hex = (D8570 * 65536) + D8571")
    print("- Insérer palette_hex directement en BD")

if __name__ == "__main__":
    print("Génération du guide InduSoft pour palettes HEX...")
    save_indusoft_guide()
    
    print("\n" + "=" * 60)
    print("RÉSUMÉ POUR INDUSOFT:")
    print("=" * 60)
    print("1. Lire D8570 (High) et D8571 (Low) depuis PLC")
    print("2. Calculer: PaletteHex = (D8570 * 65536) + D8571")
    print("3. Utiliser PaletteHex comme NO_PALETTE en base")
    print("4. Plus besoin de gérer les chaînes ASCII")
    print("5. Valeurs uniques garanties par CRC32") 