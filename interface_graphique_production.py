#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Interface Graphique de Production
Affiche les données job et palette en temps réel depuis le PLC et la base de données
"""

import sys
import os
import struct
import time
import pyodbc
import threading
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, font
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import numpy as np

# Ajouter le module fins au path
sys.path.append(os.path.join(os.path.dirname(__file__), 'fins'))
from fins.tcp import TCPFinsConnection

class InterfaceGraphiqueProduction:
    def __init__(self):
        # Configuration PLC
        self.plc_ip = "192.168.0.157"
        self.plc_port = 9600
        self.fins_instance = None
        self.area_code = b'\x82'
        self.palette_address = 8570
        self.sheets_address = 3100  # D3100 pour nombre de feuilles
        self.downtime_address = 3150  # D3150 pour temps d'arrêt
        
        # Configuration base de données JOB
        self.db_server = "192.168.0.7\\SQLEXPRESS"
        self.db_name = "PnsiDB"
        self.db_user = "GeniusExcel"
        self.db_password = "U_8nB+zUgByuCHgC4"
        
        # Configuration base de données PRODUCTION
        self.prod_db_server = "192.168.0.193\\SQLEXPRESS"
        self.prod_db_name = "KPI_data"  # Nom de la base, à ajuster si nécessaire
        self.prod_db_user = "sa"
        self.prod_db_password = "Excelpro2022!"
        
        # Variables d'état
        self.current_job = None
        self.current_palette = None
        self.current_job_info = None
        self.current_sheets = 0
        self.current_downtime = 0
        self.running = True
        self.palette_list = []  # Liste des palettes pour le job actuel
        
        # Variables pour le graphique
        self.figure = None
        self.canvas = None
        self.production_data = []  # Données de production pour le graphique
        
        # Créer l'interface
        self.create_interface()
        
        # Démarrer la lecture automatique
        self.start_monitoring()
    
    def create_interface(self):
        """Crée l'interface graphique"""
        self.root = tk.Tk()
        self.root.title("Interface Complète de Production - Jointeuse")
        
        # Obtenir la taille de l'écran
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Définir la géométrie pour prendre tout l'écran
        self.root.geometry(f"{screen_width}x{screen_height}+0+0")
        self.root.configure(bg='#f0f0f0')
        
        # Maximiser la fenêtre (compatible Linux)
        self.root.attributes('-zoomed', True)
        
        # Styles
        self.setup_styles()
        
        # Configuration COMPLÈTE du grid principal avec proportions exactes
        self.root.grid_rowconfigure(0, weight=0, minsize=80)   # Titre fixe
        self.root.grid_rowconfigure(1, weight=1)                # Contenu principal extensible
        self.root.grid_rowconfigure(2, weight=0, minsize=50)   # Barre de statut fixe
        self.root.grid_columnconfigure(0, weight=1)
        
        # Titre principal
        title_label = tk.Label(
            self.root,
            text="INTERFACE COMPLÈTE DE PRODUCTION",
            font=self.title_font,
            bg='#f0f0f0',
            fg='#2c3e50'
        )
        title_label.grid(row=0, column=0, columnspan=4, pady=15, sticky='ew')
        
        # Container principal DIRECT dans root - plus de frame intermédiaire
        # Configuration des 3 colonnes exactement égales
        self.root.grid_columnconfigure(1, weight=33, uniform="col")  # Colonne gauche 33%
        self.root.grid_columnconfigure(2, weight=33, uniform="col")  # Colonne milieu 33%  
        self.root.grid_columnconfigure(3, weight=34, uniform="col")  # Colonne droite 34% (pour compenser les arrondis)
        
        # Colonne gauche - Informations Job et Palette (1/3)
        self.left_frame = tk.Frame(self.root, bg='#f0f0f0')
        self.left_frame.grid(row=1, column=1, sticky='nsew', padx=(10, 5), pady=(0, 10))
        
        # Colonne milieu - Jointeuse 1 (1/3)
        self.middle_frame = tk.Frame(self.root, bg='#f0f0f0')
        self.middle_frame.grid(row=1, column=2, sticky='nsew', padx=(5, 5), pady=(0, 10))
        
        # Colonne droite - Graphique (1/3)
        self.right_frame = tk.Frame(self.root, bg='#f0f0f0')
        self.right_frame.grid(row=1, column=3, sticky='nsew', padx=(5, 10), pady=(0, 10))
        
        # Créer les sections
        self.create_left_section()
        self.create_middle_section()
        self.create_right_section()
        
        # Status bar avec heure (ligne 2 du grid principal)
        self.create_status_bar()
    
    def setup_styles(self):
        """Configure les styles de police"""
        self.title_font = font.Font(family="Arial", size=28, weight="bold")
        self.section_title_font = font.Font(family="Arial", size=20, weight="bold")
        self.header_font = font.Font(family="Arial", size=16, weight="bold")
        self.job_font = font.Font(family="Arial", size=48, weight="bold")
        self.production_font = font.Font(family="Arial", size=72, weight="bold")
        self.label_font = font.Font(family="Arial", size=14, weight="bold")
        self.value_font = font.Font(family="Arial", size=14)
        self.status_font = font.Font(family="Arial", size=12)
    
    def create_left_section(self):
        """Crée la section gauche avec Job et Palette"""
        # Section JOB NO
        self.create_job_section(self.left_frame)
        
        # Section informations
        self.create_info_section(self.left_frame)
        
        # Section palette
        self.create_palette_section(self.left_frame)
        
        # Scanner de code-barres (invisible mais fonctionnel)
        self.create_barcode_scanner(self.left_frame)
    
    def create_middle_section(self):
        """Crée la section milieu avec Jointeuse 1"""
        # Configuration du grid pour la section milieu
        self.middle_frame.grid_rowconfigure(0, weight=0)  # Titre
        self.middle_frame.grid_rowconfigure(1, weight=1)  # Feuilles
        self.middle_frame.grid_rowconfigure(2, weight=1)  # Temps d'arrêt
        self.middle_frame.grid_columnconfigure(0, weight=1)
        
        # Titre de la section milieu
        middle_title = tk.Label(
            self.middle_frame,
            text="Jointeuse 1",
            font=self.section_title_font,
            bg='#2c3e50',
            fg='white',
            relief=tk.RAISED,
            bd=2,
            height=2
        )
        middle_title.grid(row=0, column=0, sticky='ew', pady=(0, 10))
        
        # Nombre de feuilles produites
        sheets_frame = tk.Frame(self.middle_frame, bg='#34495e', relief=tk.RAISED, bd=3)
        sheets_frame.grid(row=1, column=0, sticky='nsew', pady=(0, 10))
        sheets_frame.grid_rowconfigure(0, weight=0)
        sheets_frame.grid_rowconfigure(1, weight=1)
        sheets_frame.grid_columnconfigure(0, weight=1)
        
        sheets_title = tk.Label(
            sheets_frame,
            text="Nombre de feuilles produites",
            font=self.header_font,
            bg='#34495e',
            fg='white'
        )
        sheets_title.grid(row=0, column=0, pady=(15, 5))
        
        self.sheets_var = tk.StringVar(value="0")
        self.sheets_label = tk.Label(
            sheets_frame,
            textvariable=self.sheets_var,
            font=font.Font(family="Arial", size=64, weight="bold"),
            bg='#34495e',
            fg='#e74c3c',
            relief=tk.SUNKEN,
            bd=2
        )
        self.sheets_label.grid(row=1, column=0, sticky='nsew', pady=(5, 15))
        
        # Section temps d'arrêt
        downtime_frame = tk.Frame(self.middle_frame, bg='#2c3e50', relief=tk.RAISED, bd=3)
        downtime_frame.grid(row=2, column=0, sticky='nsew')
        downtime_frame.grid_rowconfigure(0, weight=0)
        downtime_frame.grid_rowconfigure(1, weight=1)
        downtime_frame.grid_columnconfigure(0, weight=1)
        
        downtime_title = tk.Label(
            downtime_frame,
            text="Temps d'arrêt",
            font=self.header_font,
            bg='#2c3e50',
            fg='white'
        )
        downtime_title.grid(row=0, column=0, pady=(15, 5))
        
        self.downtime_var = tk.StringVar(value="00:00:00")
        self.downtime_label = tk.Label(
            downtime_frame,
            textvariable=self.downtime_var,
            font=font.Font(family="Arial", size=42, weight="bold"),
            bg='#2c3e50',
            fg='#27ae60',
            relief=tk.SUNKEN,
            bd=2
        )
        self.downtime_label.grid(row=1, column=0, sticky='nsew', pady=(5, 15))
    
    def create_right_section(self):
        """Crée la section droite avec le graphique uniquement"""
        # Section graphique de production
        self.create_production_chart(self.right_frame)
    
    def create_job_section(self, parent):
        """Crée la section JOB NO"""
        job_frame = tk.Frame(parent, bg='#34495e', relief=tk.RAISED, bd=2)
        job_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Label JOB NO
        job_label = tk.Label(
            job_frame,
            text="JOB NO",
            font=self.header_font,
            bg='#34495e',
            fg='white'
        )
        job_label.pack(side=tk.LEFT, padx=10, pady=15)  # Réduire padx de 20 à 10
        
        # Numéro de job
        self.job_number_var = tk.StringVar(value="147332")
        self.job_number_label = tk.Label(
            job_frame,
            textvariable=self.job_number_var,
            font=self.job_font,
            bg='#34495e',
            fg='#f39c12',
            relief=tk.SUNKEN,
            bd=2,
            width=10
        )
        self.job_number_label.pack(side=tk.RIGHT, padx=10, pady=10)  # Réduire padx de 20 à 10
    
    def create_info_section(self, parent):
        """Crée la section des informations"""
        info_frame = tk.Frame(parent, bg='#f0f0f0')
        info_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Créer les champs d'information
        self.info_vars = {}
        info_fields = [
            ("Essence :", "essence"),
            ("Coupe :", "coupe"),
            ("Dimension:", "dimension"),
            ("Agence :", "agencement"),
            ("Desc :", "description"),
            ("Mode :", "mode")
        ]
        
        for i, (label_text, var_name) in enumerate(info_fields):
            # Frame pour chaque ligne
            row_frame = tk.Frame(info_frame, bg='#ecf0f1', relief=tk.RAISED, bd=1)
            row_frame.pack(fill=tk.X, pady=2)
            
            # Label
            label = tk.Label(
                row_frame,
                text=label_text,
                font=self.label_font,
                bg='#ecf0f1',
                fg='#2c3e50',
                width=12,
                anchor='w'
            )
            label.pack(side=tk.LEFT, padx=10, pady=8)
            
            # Valeur
            self.info_vars[var_name] = tk.StringVar()
            if var_name == "essence":
                self.info_vars[var_name].set("Maple")
            elif var_name == "coupe":
                self.info_vars[var_name].set("FLAT-CUT")
            elif var_name == "dimension":
                self.info_vars[var_name].set("99' x 50'")
            elif var_name == "agencement":
                self.info_vars[var_name].set("PLK-MATCH")
            elif var_name == "description":
                self.info_vars[var_name].set("TR-MAPLE-PLK-99 X 50")
            elif var_name == "mode":
                self.info_vars[var_name].set("MODE NON DÉFINI")  # Valeur par défaut
            
            value_label = tk.Label(
                row_frame,
                textvariable=self.info_vars[var_name],
                font=self.value_font,
                bg='white',
                fg='#2c3e50',
                relief=tk.SUNKEN,
                bd=1,
                anchor='w',
                padx=10
            )
            value_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), pady=5)
    
    def create_palette_section(self, parent):
        """Crée la section palette avec liste"""
        palette_frame = tk.Frame(parent, bg='#ecf0f1', relief=tk.RAISED, bd=1)
        palette_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))  # Prend tout l'espace restant
        
        # Label Palette en haut
        palette_label = tk.Label(
            palette_frame,
            text="Palette :",
            font=self.label_font,
            bg='#ecf0f1',
            fg='#2c3e50',
            anchor='w'
        )
        palette_label.pack(fill=tk.X, padx=10, pady=(8, 5))
        
        # Zone de texte pour liste de palettes
        self.palette_text = tk.Text(
            palette_frame,
            font=self.value_font,
            bg='white',
            fg='#2c3e50',
            relief=tk.SUNKEN,
            bd=1,
            wrap=tk.WORD,
            state=tk.DISABLED  # En lecture seule
        )
        self.palette_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))  # Prend tout l'espace disponible
    
    def create_barcode_scanner(self, parent):
        """Crée le scanner de code-barres invisible mais fonctionnel"""
        # Champ d'entrée invisible pour capturer les scans
        self.scanner_entry = tk.Entry(parent, width=1)
        self.scanner_entry.place(x=-100, y=-100)  # Hors écran mais fonctionnel
        self.scanner_entry.bind('<Return>', self.on_barcode_scanned)
        self.scanner_entry.focus_set()  # Focus pour capturer les scans
        
        # Timer pour remettre le focus sur le scanner
        self.maintain_scanner_focus()
    
    def maintain_scanner_focus(self):
        """Maintient le focus sur le scanner pour capturer les codes-barres"""
        try:
            self.scanner_entry.focus_set()
        except:
            pass
        # Répéter toutes les 2 secondes
        self.root.after(2000, self.maintain_scanner_focus)
    
    def on_barcode_scanned(self, event):
        """Traite un code-barres scanné"""
        barcode = self.scanner_entry.get().strip()
        self.scanner_entry.delete(0, tk.END)  # Vider le champ
        
        if barcode:
            # Traiter le code-barres (peut être un job ou une palette)
            self.process_barcode(barcode)
    
    def process_barcode(self, barcode):
        """Traite le code-barres scanné"""
        # Logique pour déterminer si c'est un job ou une palette
        if barcode.isdigit() and len(barcode) == 6:
            # Probablement un numéro de job
            job_number = int(barcode)
            self.current_job = job_number
            self.palette_list = []  # Réinitialiser les palettes
            
            # EFFACER LES ANCIENNES DONNÉES DU PLC
            self.clear_job_info_from_plc()
            
            # RÉCUPÉRER LES INFORMATIONS DU JOB
            self.current_job_info = self.get_job_info_from_database(self.current_job)
            
            # ÉCRIRE LE JOB DANS LE PLC
            if self.write_job_to_plc(job_number):
                # ÉCRIRE LES INFORMATIONS COMPLÈTES DU JOB
                if self.current_job_info and self.write_job_info_to_plc(self.current_job_info):
                    self.update_status(f"Job {barcode} complet écrit dans le PLC")
                else:
                    self.update_status(f"Job {barcode} écrit - ERREUR infos complémentaires")
            else:
                self.update_status(f"Job {barcode} scanné - ERREUR envoi PLC")
        else:
            # Probablement une palette
            if barcode not in self.palette_list:
                self.palette_list.append(barcode)
                self.current_palette = barcode
                
                # ÉCRIRE LA PALETTE DANS LE PLC
                if self.write_palette_to_plc(barcode):
                    self.update_status(f"Palette {barcode} scannée et envoyée au PLC")
                else:
                    self.update_status(f"Palette {barcode} scannée - ERREUR envoi PLC")
        
        # Mettre à jour l'affichage
        self.update_display()
    
    def create_production_chart(self, parent):
        """Crée le graphique de production intégré"""
        # Frame pour le graphique
        chart_frame = tk.Frame(parent, bg='#2c3e50', relief=tk.RAISED, bd=3)
        chart_frame.pack(fill=tk.BOTH, expand=True, pady=(20, 0))
        
        # Titre du graphique
        chart_title = tk.Label(
            chart_frame,
            text="Production par heure (7h-17h30)",
            font=self.header_font,
            bg='#2c3e50',
            fg='white'
        )
        chart_title.pack(pady=(10, 5))
        
        # Créer la figure matplotlib avec une taille plus grande
        self.figure = Figure(figsize=(12, 10), dpi=80, facecolor='#2c3e50')
        self.ax = self.figure.add_subplot(111, facecolor='#34495e')
        
        # Configurer le style du graphique
        self.ax.tick_params(colors='white', labelsize=11)
        self.ax.spines['bottom'].set_color('white')
        self.ax.spines['top'].set_color('white')
        self.ax.spines['right'].set_color('white')
        self.ax.spines['left'].set_color('white')
        
        # Canvas matplotlib dans tkinter - occupe tout l'espace disponible
        self.canvas = FigureCanvasTkAgg(self.figure, chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        
        # Initialiser le graphique avec des données vides
        self.update_production_chart()
    
    def create_status_bar(self):
        """Crée la barre de statut visible en bas"""
        status_frame = tk.Frame(self.root, bg='#34495e', relief=tk.RAISED, bd=2, height=40)
        status_frame.grid(row=2, column=0, columnspan=4, sticky='ew', padx=10, pady=(0, 10))
        status_frame.grid_propagate(False)  # Maintenir la hauteur fixe
        
        # Configuration du grid pour la barre de statut
        status_frame.grid_columnconfigure(0, weight=1)
        status_frame.grid_columnconfigure(1, weight=0)
        
        # Message de statut pour la palette
        self.status_var = tk.StringVar(value="✓ Système opérationnel - Scanner actif")
        self.palette_status_text = tk.Label(
            status_frame,
            textvariable=self.status_var,
            font=self.status_font,
            bg='#34495e',
            fg='white',
            anchor='w'
        )
        self.palette_status_text.grid(row=0, column=0, sticky='w', padx=15, pady=8)
        
        # Heure actuelle en petit (dans le coin)
        self.current_time_var = tk.StringVar(value="14:52:15")
        time_label = tk.Label(
            status_frame,
            textvariable=self.current_time_var,
            font=font.Font(family="Arial", size=12, weight="bold"),
            bg='#34495e',
            fg='#f39c12',
            anchor='e'
        )
        time_label.grid(row=0, column=1, sticky='e', padx=15, pady=8)
        
        # Heure de traitement complète (pour l'historique)
        self.process_time_var = tk.StringVar(value="2025-06-18 11:52:15")
        # Pas d'affichage, juste pour garder la compatibilité
    
    def connect_to_plc(self):
        """Connexion au PLC"""
        try:
            self.fins_instance = TCPFinsConnection()
            self.fins_instance.connect(self.plc_ip, self.plc_port)
            return True
        except Exception as e:
            self.update_status(f"Erreur PLC: {e}")
            return False
    
    def connect_to_database(self):
        """Connexion à la base de données JOB"""
        try:
            server_name = self.db_server.split('\\')[0]
            conn_string = (
                "DRIVER={FreeTDS};"
                f"SERVER={server_name};"
                "PORT=1433;"
                f"DATABASE={self.db_name};"
                f"UID={self.db_user};"
                f"PWD={self.db_password};"
                "TDS_Version=8.0;"
            )
            
            conn = pyodbc.connect(conn_string, timeout=5)
            return conn
        except Exception as e:
            self.update_status(f"Erreur DB Job: {e}")
            return None
    
    def connect_to_production_database(self):
        """Connexion à la base de données PRODUCTION"""
        try:
            server_name = self.prod_db_server.split('\\')[0]
            conn_string = (
                "DRIVER={FreeTDS};"
                f"SERVER={server_name};"
                "PORT=1433;"
                f"DATABASE={self.prod_db_name};"
                f"UID={self.prod_db_user};"
                f"PWD={self.prod_db_password};"
                "TDS_Version=8.0;"
            )
            
            conn = pyodbc.connect(conn_string, timeout=5)
            return conn
        except Exception as e:
            self.update_status(f"Erreur DB Production: {e}")
            return None
    
    def read_plc_data(self):
        """Lit les données du PLC (format ASCII pour palette)"""
        try:
            # Lire JOB depuis D8500
            d8500_address = b'\x21\x34\x00'
            response = self.fins_instance.memory_area_read(self.area_code, d8500_address, 2)
            
            job_number = None
            if response and len(response) >= 18:
                data = response[14:18]
                part1, part2 = struct.unpack('>HH', data)
                if part1 > 0 or part2 > 0:
                    job_number = part1 * 10000 + part2
            
            # Lire PALETTE en format ASCII (D8570+ 15 mots)
            memory_address = struct.pack('>HB', self.palette_address, 0)
            response = self.fins_instance.memory_area_read(self.area_code, memory_address, 15)
            
            palette_code = None
            if response and len(response) >= 44:
                data = response[14:44]  # 30 bytes = 15 mots
                palette_str = ""
                
                for i in range(0, len(data), 2):
                    word = struct.unpack('>H', data[i:i+2])[0]
                    if word == 0:
                        break
                    char1 = chr((word >> 8) & 0xFF) if (word >> 8) & 0xFF > 0 else ''
                    char2 = chr(word & 0xFF) if word & 0xFF > 0 else ''
                    palette_str += char1 + char2
                
                palette_code = palette_str.strip() if palette_str.strip() else None
                if palette_code:
                    print(f"[DEBUG] Lu PLC: Palette ASCII = '{palette_code}'")

            # Lire nombre de feuilles depuis D3100
            sheets_address = struct.pack('>HB', self.sheets_address, 0)
            response = self.fins_instance.memory_area_read(self.area_code, sheets_address, 2)
            
            sheets_count = 0
            if response and len(response) >= 18:
                # Essayer comme WORD 16-bit
                data_word = response[14:16]
                sheets_word = struct.unpack('>H', data_word)[0]
                
                # Essayer comme DWORD 32-bit
                data_dword = response[14:18]
                sheets_dword = struct.unpack('>I', data_dword)[0]
                
                # Utiliser la valeur WORD si non-zéro, sinon DWORD
                sheets_count = sheets_word if sheets_word > 0 else sheets_dword
            
            # Lire temps d'arrêt depuis D3150
            downtime_address = struct.pack('>HB', self.downtime_address, 0)
            response = self.fins_instance.memory_area_read(self.area_code, downtime_address, 2)
            
            downtime_seconds = 0
            if response and len(response) >= 18:
                # Essayer comme WORD 16-bit
                data_word = response[14:16]
                downtime_word = struct.unpack('>H', data_word)[0]
                
                # Essayer comme DWORD 32-bit
                data_dword = response[14:18]
                downtime_dword = struct.unpack('>I', data_dword)[0]
                
                # Utiliser la valeur WORD si non-zéro, sinon DWORD
                downtime_seconds = downtime_word if downtime_word > 0 else downtime_dword
            
            return job_number, palette_code, sheets_count, downtime_seconds
            
        except Exception as e:
            self.update_status(f"Erreur lecture PLC: {e}")
            return None, None, 0, 0
    
    def write_job_to_plc(self, job_number):
        """Écrit le numéro de job dans le PLC à l'adresse D8500"""
        try:
            print(f"[DEBUG] Tentative d'écriture job {job_number} dans PLC")
            
            if not self.fins_instance:
                print("[DEBUG] Pas de connexion FINS, tentative de connexion...")
                if not self.connect_to_plc():
                    self.update_status("Erreur: Pas de connexion PLC pour écriture job")
                    return False
            
            # Convertir le job en 2 mots de 16 bits (comme dans la lecture)
            part1 = job_number // 10000  # Les 2 premiers chiffres
            part2 = job_number % 10000   # Les 4 derniers chiffres
            
            print(f"[DEBUG] Job {job_number} -> Part1: {part1}, Part2: {part2}")
            
            # Préparer les données à écrire
            data = struct.pack('>HH', part1, part2)
            print(f"[DEBUG] Data à écrire: {data.hex()}")
            
            # Adresse D8500
            d8500_address = b'\x21\x34\x00'
            print(f"[DEBUG] Adresse D8500: {d8500_address.hex()}")
            
            # Écrire vers le PLC avec number_of_items=2 (2 mots)
            response = self.fins_instance.memory_area_write(
                self.area_code, 
                d8500_address, 
                data, 
                2  # number_of_items: 2 mots
            )
            
            print(f"[DEBUG] Réponse écriture: {response.hex() if response else 'None'}")
            
            if response:
                self.update_status(f"Job {job_number} écrit dans le PLC")
                return True
            else:
                self.update_status("Erreur: Échec écriture job PLC")
                return False
                
        except Exception as e:
            print(f"[DEBUG] Exception lors écriture job: {e}")
            self.update_status(f"Erreur écriture job PLC: {e}")
            return False
    
    def write_palette_to_plc(self, palette_code):
        """Écrit le code palette dans le PLC à l'adresse D8570 (format ASCII)"""
        try:
            if not self.fins_instance:
                if not self.connect_to_plc():
                    self.update_status("Erreur: Pas de connexion PLC pour écriture palette")
                    return False
            
            # Préparer la chaîne palette (30 caractères max)
            palette_padded = palette_code.ljust(30, '\x00')[:30]
            
            # Convertir en mots de 16 bits ASCII
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
            
            # Adresse D8570 (15 mots pour 30 caractères ASCII)
            memory_address = struct.pack('>HB', self.palette_address, 0)
            
            # Écrire vers le PLC avec 15 mots (30 caractères ASCII)
            response = self.fins_instance.memory_area_write(
                self.area_code, 
                memory_address, 
                data, 
                15  # 15 mots pour 30 caractères ASCII
            )
            
            if response:
                print(f"[DEBUG] Palette '{palette_code}' écrite en ASCII dans D{self.palette_address}+")
                self.update_status(f"Palette {palette_code} écrite dans le PLC (ASCII)")
                return True
            else:
                self.update_status("Erreur: Échec écriture palette PLC")
                return False
                
        except Exception as e:
            self.update_status(f"Erreur écriture palette PLC: {e}")
            return False
    
    def clear_job_info_from_plc(self):
        """Efface les informations du job dans le PLC"""
        try:
            if not self.fins_instance:
                if not self.connect_to_plc():
                    return False
            
            # Adresses à effacer (même que write_job_info_to_plc)
            addresses_to_clear = [
                (8520, 15),  # ESSENCE
                (8535, 10),  # COUPE  
                (8545, 10),  # DIMENSION
                (8555, 15),  # AGENCEMENT
                (8590, 15)   # DESCRIPTION
            ]
            
            for address, num_words in addresses_to_clear:
                hex_address = struct.pack('>HB', address, 0)
                # Écrire des zéros
                clear_data = b'\x00' * (num_words * 2)
                self.fins_instance.memory_area_write(self.area_code, hex_address, clear_data, num_words)
            
            print("[DEBUG] Informations job effacées du PLC")
            return True
            
        except Exception as e:
            print(f"[DEBUG] Erreur effacement infos job: {e}")
            return False
    
    def write_job_info_to_plc(self, job_info):
        """Écrit les informations du job dans le PLC pour affichage HMI"""
        if not job_info:
            return False
        
        try:
            print(f"[DEBUG] Écriture infos job dans PLC: {job_info}")
            
            if not self.fins_instance:
                if not self.connect_to_plc():
                    return False
            
            # Adresses PLC pour les informations
            essence_address = 8520    # D8520-D8534 (15 mots = 30 chars)
            coupe_address = 8535      # D8535-D8544 (10 mots = 20 chars)  
            dimensions_address = 8545 # D8545-D8554 (10 mots = 20 chars)
            agencement_address = 8555 # D8555-D8569 (15 mots = 30 chars)
            description_address = 8590 # D8590-D8604 (15 mots = 30 chars)
            
            # Préparer les données
            essence = job_info.get('essence', 'Non spécifiée')[:30]
            coupe = job_info.get('coupe', 'Non spécifiée')[:20]
            dimensions = job_info.get('dimension', 'Non spécifiées')[:20]
            agencement = job_info.get('agencement', 'Non spécifié')[:30]
            description = job_info.get('description', 'Non spécifiée')[:30]
            
            print(f"[DEBUG] Données à écrire - Essence: {essence}, Coupe: {coupe}, Dim: {dimensions}")
            
            # Fonction helper pour écrire une chaîne ASCII
            def write_ascii_string(text, start_address, max_words):
                hex_address = struct.pack('>HB', start_address, 0)
                
                words = []
                for i in range(0, min(len(text), max_words * 2), 2):
                    char1 = text[i] if i < len(text) else '\0'
                    char2 = text[i+1] if i+1 < len(text) else '\0'
                    word_value = (ord(char1) << 8) | ord(char2) if char2 != '\0' else (ord(char1) << 8)
                    words.append(word_value)
                
                while len(words) < max_words:
                    words.append(0)
                
                if len(words) > 0:
                    write_data = struct.pack('>' + 'H' * len(words), *words)
                    response = self.fins_instance.memory_area_write(self.area_code, hex_address, write_data, len(words))
                    print(f"[DEBUG] Écriture {text} à D{start_address}: {response.hex() if response else 'None'}")
            
            # Écrire toutes les informations
            write_ascii_string(essence, essence_address, 15)
            write_ascii_string(coupe, coupe_address, 10)
            write_ascii_string(dimensions, dimensions_address, 10)
            write_ascii_string(agencement, agencement_address, 15)
            write_ascii_string(description, description_address, 15)
            
            print("[DEBUG] Toutes les informations job écrites dans le PLC")
            return True
            
        except Exception as e:
            print(f"[DEBUG] Erreur écriture infos job PLC: {e}")
            return False
    
    def format_downtime(self, seconds):
        """Formate le temps d'arrêt en HH:MM:SS"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def get_job_info_from_database(self, job_number):
        """Récupère les informations du job"""
        conn = self.connect_to_database()
        if not conn:
            return None
        
        try:
            cursor = conn.cursor()
            
            query = """
            SELECT TOP 1 
                DescriptionSpec9 as Essence,
                JOB_COUPE as Coupe,
                Long as Longueur,
                Large as Largeur, 
                SPEC3 as Agencement,
                DES as Description
            FROM vzJobInProgress 
            WHERE JOB = ?
            ORDER BY JOB DESC
            """
            
            cursor.execute(query, (str(job_number),))
            row = cursor.fetchone()
            
            if row:
                # Formatter les dimensions
                def clean_dimension(value):
                    if not value:
                        return ""
                    try:
                        float_val = float(value)
                        if float_val == int(float_val):
                            return str(int(float_val))
                        else:
                            return str(float_val).rstrip('0').rstrip('.')
                    except:
                        return str(value)
                
                longueur = clean_dimension(row.Longueur)
                largeur = clean_dimension(row.Largeur)
                
                if longueur and largeur:
                    dimensions = f"{longueur}' x {largeur}'"
                elif longueur:
                    dimensions = f"{longueur}'"
                elif largeur:
                    dimensions = f"{largeur}'"
                else:
                    dimensions = "Non spécifiées"
                
                job_info = {
                    'essence': row.Essence if row.Essence else 'Non spécifiée',
                    'coupe': row.Coupe if row.Coupe else 'Non spécifiée',
                    'dimension': dimensions,
                    'agencement': row.Agencement if row.Agencement else 'Non spécifié',
                    'description': row.Description if row.Description else 'Non spécifiée'
                }
                return job_info
            else:
                return None
                
        except Exception as e:
            self.update_status(f"Erreur requête DB: {e}")
            return None
        finally:
            conn.close()
    
    def update_palette_list(self):
        """Met à jour la liste des palettes dans le widget Text"""
        self.palette_text.config(state=tk.NORMAL)  # Activer l'édition
        self.palette_text.delete(1.0, tk.END)  # Effacer le contenu
        
        if self.palette_list:
            # Afficher toutes les palettes, une par ligne
            palette_text = "\n".join(self.palette_list)
            self.palette_text.insert(1.0, palette_text)
        else:
            self.palette_text.insert(1.0, "Aucune palette scannée")
        
        self.palette_text.config(state=tk.DISABLED)  # Remettre en lecture seule
    
    def update_display(self):
        """Met à jour l'affichage des données"""
        # Mise à jour côté gauche
        if self.current_job:
            self.job_number_var.set(f"{self.current_job:06d}")
        else:
            self.job_number_var.set("147332")  # Valeur par défaut
        
        if self.current_job_info:
            for key, var in self.info_vars.items():
                value = self.current_job_info.get(key, "Non spécifié")
                var.set(value)
        
        # Mettre à jour la liste des palettes
        self.update_palette_list()
        
        # Mise à jour côté droit - DONNÉES DE PRODUCTION
        # Mettre à jour le nombre de feuilles
        self.sheets_var.set(str(self.current_sheets))
        
        # Mettre à jour le temps d'arrêt
        formatted_downtime = self.format_downtime(self.current_downtime)
        self.downtime_var.set(formatted_downtime)
    
    def update_status(self, message):
        """Met à jour le statut"""
        if hasattr(self, 'status_var'):
            self.status_var.set(f"✓ {message}")
            # Force la mise à jour de l'interface
            self.root.update_idletasks()
    
    def update_time(self):
        """Met à jour l'heure en continu"""
        current_time = datetime.now()
        # Mettre à jour l'heure complète (pour compatibilité)
        self.process_time_var.set(current_time.strftime("%Y-%m-%d %H:%M:%S"))
        # Mettre à jour l'heure dans le coin (format court)
        if hasattr(self, 'current_time_var'):
            self.current_time_var.set(current_time.strftime("%H:%M:%S"))
        # Programmer la prochaine mise à jour dans 1 seconde
        self.root.after(1000, self.update_time)
    
    def get_production_data(self):
        """Récupère les données de production depuis la base de données"""
        conn = self.connect_to_production_database()
        if not conn:
            return []
        
        try:
            cursor = conn.cursor()
            
            # Récupérer les données du jour actuel par heure
            today = datetime.now().strftime("%Y-%m-%d")
            
            query = """
            SELECT 
                DATEPART(HOUR, TIMESTAMP) as Heure,
                SUM(NB_JOINT) as NbJoints,
                SUM(NB_COUPON) as NbCoupons
            FROM dbo.TABLE_FEUILLES 
            WHERE LIGNE = 'L1' 
                AND CAST(TIMESTAMP as DATE) = ?
                AND DATEPART(HOUR, TIMESTAMP) BETWEEN 7 AND 17
                AND NB_JOINT BETWEEN 0 AND 50
                AND NB_COUPON BETWEEN 1 AND 50
            GROUP BY DATEPART(HOUR, TIMESTAMP)
            ORDER BY DATEPART(HOUR, TIMESTAMP)
            """
            
            cursor.execute(query, (today,))
            rows = cursor.fetchall()
            
            # Convertir en liste de dictionnaires
            data = []
            for row in rows:
                data.append({
                    'heure': row.Heure,
                    'joints': row.NbJoints if row.NbJoints else 0,
                    'coupons': row.NbCoupons if row.NbCoupons else 0
                })
            
            return data
            
        except Exception as e:
            self.update_status(f"Erreur récupération données: {e}")
            return []
        finally:
            conn.close()
    
    def update_production_chart(self):
        """Met à jour le graphique de production"""
        if not self.figure or not self.ax:
            return
            
        # Récupérer les nouvelles données
        data = self.get_production_data()
        
        # Nettoyer le graphique
        self.ax.clear()
        
        # Heures de production (7h à 17h30)
        hours = list(range(7, 18))  # 7 à 17h
        joints_data = [0] * len(hours)
        coupons_data = [0] * len(hours)
        
        # Remplir les données
        for item in data:
            if 7 <= item['heure'] <= 17:
                index = item['heure'] - 7
                joints_data[index] = item['joints']
                coupons_data[index] = item['coupons']
        
        # Créer les barres
        x = np.arange(len(hours))
        width = 0.35
        
        bars1 = self.ax.bar(x - width/2, joints_data, width, label='Joints', color='#3498db', alpha=0.8)
        bars2 = self.ax.bar(x + width/2, coupons_data, width, label='Coupons', color='#e74c3c', alpha=0.8)
        
        # Configuration du graphique
        self.ax.set_xlabel('Heures', color='white', fontsize=11)
        self.ax.set_ylabel('Quantité', color='white', fontsize=11)
        self.ax.set_title('Production Jointeuse L1 - Aujourd\'hui', color='white', fontsize=13, fontweight='bold')
        self.ax.set_xticks(x)
        self.ax.set_xticklabels([f"{h}h" for h in hours])
        self.ax.legend(loc='upper left', facecolor='#34495e', edgecolor='white', labelcolor='white')
        
        # Ajouter les valeurs sur les barres
        def add_value_labels(bars):
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    self.ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                               f'{int(height)}',
                               ha='center', va='bottom', color='white', fontsize=9)
        
        add_value_labels(bars1)
        add_value_labels(bars2)
        
        # Style du graphique
        self.ax.grid(True, alpha=0.3, color='white')
        self.ax.tick_params(colors='white', labelsize=10)
        self.ax.spines['bottom'].set_color('white')
        self.ax.spines['top'].set_color('white')
        self.ax.spines['right'].set_color('white')
        self.ax.spines['left'].set_color('white')
        
        # Rafraîchir l'affichage
        self.canvas.draw()
    
    def update_production_chart_timer(self):
        """Timer pour mettre à jour le graphique toutes les 5 minutes"""
        self.update_production_chart()
        # Programmer la prochaine mise à jour dans 5 minutes (300000 ms)
        self.root.after(300000, self.update_production_chart_timer)
    
    def monitoring_loop(self):
        """Boucle de surveillance"""
        try:
            # Essayer de se connecter au PLC
            if not self.connect_to_plc():
                self.update_status("Mode simulation - Pas de connexion PLC")
                # Simuler des données pour les tests
                self.current_sheets = 507
                self.current_downtime = 2694  # 00:44:54 en secondes
            else:
                # Lire les données PLC
                job_number, palette_code, sheets_count, downtime_seconds = self.read_plc_data()
                
                # Vérifier si le job a changé
                if job_number != self.current_job:
                    self.current_job = job_number
                    # RÉINITIALISER la liste des palettes quand le job change
                    self.palette_list = []
                    
                    if job_number:
                        self.current_job_info = self.get_job_info_from_database(job_number)
                        self.update_status(f"Job {job_number} chargé - Liste palettes réinitialisée")
                    else:
                        self.current_job_info = None
                        self.update_status("En attente de job...")
                
                # Vérifier si la palette a changé
                if palette_code != self.current_palette:
                    self.current_palette = palette_code
                    if palette_code:
                        # Ajouter la nouvelle palette à la liste (éviter les doublons)
                        if palette_code not in self.palette_list:
                            self.palette_list.append(palette_code)
                        self.update_status(f"Palette {palette_code} ajoutée à la liste")
                
                # Mettre à jour les données de production
                self.current_sheets = sheets_count
                self.current_downtime = downtime_seconds
            
            # TOUJOURS mettre à jour l'affichage avec les données actuelles
            self.update_display()
            
            # Programmer la prochaine lecture
            self.root.after(1000, self.monitoring_loop)
            
        except Exception as e:
            self.update_status(f"Erreur monitoring: {e}")
            # Programmer la prochaine tentative
            self.root.after(5000, self.monitoring_loop)
    
    def start_monitoring(self):
        """Démarre la surveillance"""
        self.update_status("Système opérationnel - Surveillance active")
        
        # Initialiser avec la palette par défaut
        self.palette_list = ["FRE-39764-147332"]
        
        # Démarrer la surveillance immédiatement
        self.monitoring_loop()
        # Démarrer la mise à jour de l'heure
        self.update_time()
        # Démarrer la mise à jour du graphique
        self.update_production_chart_timer()
    
    def on_closing(self):
        """Gestionnaire de fermeture"""
        self.running = False
        if self.fins_instance:
            try:
                self.fins_instance.close()
            except:
                pass
        self.root.destroy()
    
    def run(self):
        """Lance l'interface"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

def main():
    """Fonction principale"""
    app = InterfaceGraphiqueProduction()
    app.run()

if __name__ == "__main__":
    main() 