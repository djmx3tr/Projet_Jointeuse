#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Guide InduSoft - Lecture Palettes ASCII depuis PLC
=================================================

Ce script explique comment InduSoft peut lire les palettes en format ASCII
depuis le PLC et les utiliser directement en base de données.

ADRESSES PLC POUR INDUSOFT:
- D8570 à D8584: Chaîne ASCII palette (15 mots = 30 caractères max)

AVANTAGE:
- Le texte "CHE-28892-399291" apparaît directement en base de données
"""

def create_indusoft_ascii_guide():
    """
    Crée le guide complet pour lire les palettes ASCII avec InduSoft
    """
    
    vbscript_functions = '''
' ===================================================================
' FONCTIONS VBSCRIPT POUR INDUSOFT - LECTURE PALETTES ASCII
' ===================================================================

' Fonction pour lire la palette ASCII depuis le PLC (D8570-D8584)
Function GetPaletteASCIIFromPLC()
    Dim PaletteText, i, HighByte, LowByte, WordValue
    
    PaletteText = ""
    
    ' Lire les 15 mots (D8570 à D8584)
    For i = 8570 To 8584
        WordValue = ReadTag("D" & i)
        
        ' Si le mot est 0, fin de la chaîne
        If WordValue = 0 Then
            Exit For
        End If
        
        ' Extraire les 2 caractères du mot (Big-Endian)
        HighByte = Int(WordValue / 256)  ' Byte supérieur
        LowByte = WordValue Mod 256      ' Byte inférieur
        
        ' Ajouter les caractères (si valides)
        If HighByte > 0 Then
            PaletteText = PaletteText + Chr(HighByte)
        End If
        If LowByte > 0 Then
            PaletteText = PaletteText + Chr(LowByte)
        End If
    Next i
    
    ' Nettoyer la chaîne (supprimer espaces en fin)
    GetPaletteASCIIFromPLC = Trim(PaletteText)
End Function

' Fonction pour insérer en base de données avec palette ASCII
Function InsertSheetWithPaletteASCII(JobNumber, NbJoint, NbCoupon)
    Dim PaletteText, SQL, Timestamp
    
    ' Obtenir le texte de la palette
    PaletteText = GetPaletteASCIIFromPLC()
    
    ' Vérifier qu'une palette est présente
    If Len(PaletteText) = 0 Then
        InsertSheetWithPaletteASCII = False
        Exit Function
    End If
    
    ' Créer le timestamp
    Timestamp = Now()
    
    ' Construire la requête SQL avec texte de palette
    SQL = "INSERT INTO dbo.TABLE_FEUILLES " & _
          "(TIMESTAMP, NO_JOB, NO_PALETTE, NB_JOINT, NB_COUPON) " & _
          "VALUES ('" & Timestamp & "', " & JobNumber & ", '" & PaletteText & "', " & NbJoint & ", " & NbCoupon & ")"
    
    ' Exécuter la requête
    ExecuteSQL(SQL)
    
    InsertSheetWithPaletteASCII = True
End Function

' Fonction pour vérifier si une palette est active
Function IsPaletteASCIIActive()
    Dim PaletteText
    PaletteText = GetPaletteASCIIFromPLC()
    
    ' Si la longueur > 0, une palette est scannée
    IsPaletteASCIIActive = (Len(PaletteText) > 0)
End Function

' Fonction pour afficher la palette sur l'écran InduSoft
Function DisplayCurrentPalette()
    Dim PaletteText
    PaletteText = GetPaletteASCIIFromPLC()
    
    If Len(PaletteText) > 0 Then
        DisplayCurrentPalette = PaletteText
    Else
        DisplayCurrentPalette = "Aucune palette"
    End If
End Function
'''

    # Exemples pratiques
    examples_sql = '''
-- ===================================================================
-- EXEMPLES SQL RÉSULTANTS DANS LA BASE DE DONNÉES
-- ===================================================================

-- Avec le système ASCII, vous verrez directement:
INSERT INTO dbo.TABLE_FEUILLES 
(TIMESTAMP, NO_JOB, NO_PALETTE, NB_JOINT, NB_COUPON)
VALUES 
(GETDATE(), 123456, 'CHE-28892-399291', 150, 3),
(GETDATE(), 123456, 'FRE-39764-147332', 142, 2),
(GETDATE(), 147430, 'BOJ-45678-ABC123', 138, 4);

-- Requêtes d'analyse avec texte de palette:
SELECT 
    NO_PALETTE,
    COUNT(*) as NB_FEUILLES,
    SUM(NB_JOINT) as TOTAL_JOINTS,
    AVG(NB_JOINT) as MOYENNE_JOINTS
FROM dbo.TABLE_FEUILLES 
WHERE NO_PALETTE IS NOT NULL
    AND NO_PALETTE LIKE 'CHE-%'  -- Filtrer par type de palette
GROUP BY NO_PALETTE
ORDER BY NO_PALETTE;

-- Recherche par préfixe de palette:
SELECT * FROM dbo.TABLE_FEUILLES 
WHERE NO_PALETTE LIKE 'FRE-%'  -- Toutes les palettes FRE
ORDER BY TIMESTAMP DESC;
'''

    # Structure des données PLC
    plc_structure = '''
STRUCTURE DES DONNÉES PLC (D8570-D8584):
=========================================

Exemple pour "CHE-28892-399291":
D8570: 0x4348 = 'C' (0x43) + 'H' (0x48)
D8571: 0x452D = 'E' (0x45) + '-' (0x2D)  
D8572: 0x3238 = '2' (0x32) + '8' (0x38)
D8573: 0x3839 = '8' (0x38) + '9' (0x39)
D8574: 0x322D = '2' (0x32) + '-' (0x2D)
D8575: 0x3339 = '3' (0x33) + '9' (0x39)
D8576: 0x3939 = '9' (0x39) + '9' (0x39)
D8577: 0x3239 = '2' (0x32) + '9' (0x39)
D8578: 0x3100 = '1' (0x31) + NULL (0x00)
D8579: 0x0000 = Fin de chaîne
...
D8584: 0x0000 = Non utilisé

DÉCODAGE EN VBSCRIPT:
Word = ReadTag("D8570")  ' = 17224 (décimal)
HighByte = Int(17224 / 256) = 67 = 'C'
LowByte = 17224 Mod 256 = 72 = 'H'
Résultat: "CH"
'''

    print("=" * 70)
    print("GUIDE INDUSOFT - SYSTÈME PALETTE ASCII")
    print("=" * 70)
    print("\n📍 ADRESSES PLC:")
    print("   D8570-D8584: Palette ASCII (15 mots = 30 caractères max)")
    print("\n✅ AVANTAGE:")
    print("   Le texte original apparaît directement en base de données")
    print("   Exemple: 'CHE-28892-399291' → BD: 'CHE-28892-399291'")
    
    # Sauvegarder les fichiers
    with open('indusoft_ascii_functions.vbs', 'w') as f:
        f.write(vbscript_functions)
    
    with open('indusoft_ascii_examples.sql', 'w') as f:
        f.write(examples_sql)
    
    with open('indusoft_plc_structure.txt', 'w') as f:
        f.write(plc_structure)
    
    print("\n📁 FICHIERS CRÉÉS:")
    print("   ✓ indusoft_ascii_functions.vbs - Fonctions VBScript")
    print("   ✓ indusoft_ascii_examples.sql - Exemples SQL")
    print("   ✓ indusoft_plc_structure.txt - Structure PLC")
    
    print("\n🎯 CONFIGURATION INDUSOFT:")
    print("   1. Copier les fonctions VBScript dans votre projet")
    print("   2. Utiliser GetPaletteASCIIFromPLC() pour lire")
    print("   3. Insérer directement le texte en base de données")
    print("   4. Le texte 'CHE-28892-399291' apparaîtra tel quel en BD")

def demo_palette_conversion():
    """
    Démontre la conversion ASCII pour différentes palettes
    """
    test_palettes = [
        "CHE-28892-399291",
        "FRE-39764-147332", 
        "BOJ-45678-ABC123",
        "SAP-987654",
        "PIN-12345"
    ]
    
    print("\n" + "=" * 70)
    print("DÉMONSTRATION CONVERSION ASCII")
    print("=" * 70)
    print(f"{'Palette':<20} {'Longueur':<10} {'Résultat BD'}")
    print("-" * 70)
    
    for palette in test_palettes:
        length = len(palette)
        if length <= 30:
            status = "✅ OK"
        else:
            status = "❌ TROP LONG"
        
        print(f"{palette:<20} {length:<10} {status}")
        
        # Afficher les premiers mots PLC
        print(f"   Premiers mots PLC:")
        for i in range(0, min(len(palette), 8), 2):
            if i + 1 < len(palette):
                char1 = palette[i]
                char2 = palette[i + 1]
                word_val = (ord(char1) << 8) | ord(char2)
                print(f"   D{8570 + i//2}: 0x{word_val:04X} = '{char1}' + '{char2}'")
        print()

if __name__ == "__main__":
    print("🔤 Génération du guide InduSoft ASCII...")
    create_indusoft_ascii_guide()
    demo_palette_conversion()
    
    print("\n" + "=" * 60)
    print("RÉSUMÉ POUR INDUSOFT (SYSTÈME ASCII):")
    print("=" * 60)
    print("1. Lire D8570-D8584 (15 mots) depuis PLC")
    print("2. Décoder chaque mot en 2 caractères ASCII")
    print("3. Assembler la chaîne complète")
    print("4. Insérer le texte directement en BD")
    print("5. Résultat: 'CHE-28892-399291' visible en BD")
    print("\n✅ LE TEXTE ORIGINAL SERA VISIBLE EN BASE DE DONNÉES !") 