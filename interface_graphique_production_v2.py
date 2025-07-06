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
import random
import json

# Ajouter le module fins au path
sys.path.append(os.path.join(os.path.dirname(__file__), 'fins'))
from fins.tcp import TCPFinsConnection

# Import du module de détection de feuilles
try:
    from paper_detection_module import PaperDetectionModule
    PAPER_DETECTION_AVAILABLE = True
except ImportError as e:
    PAPER_DETECTION_AVAILABLE = False

class InterfaceGraphiqueProductionV2:
    def load_config(self):
        """Charge la configuration depuis le fichier JSON"""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'CONFIG', 'config.json')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            print(f"❌ Fichier de configuration non trouvé : {config_path}")
            # Configuration par défaut si le fichier n'existe pas
            self.config = self.get_default_config()
        except json.JSONDecodeError as e:
            print(f"❌ Erreur dans le fichier de configuration : {e}")
            self.config = self.get_default_config()
    
    def get_default_config(self):
        """Configuration par défaut en cas d'erreur"""
        return {
            "plc": {
                "main": {"ip": "192.168.0.175", "port": 9600},
                "production": {"ip": "192.168.0.157", "port": 9600}
            },
            "paper_detection": {
                "enabled": True,
                "plc": {"ip": "192.168.0.166", "port": 9600, "bit_address": "W160.00"},
                "inference_server": {"url": "http://192.168.0.71:5050"},
                "client_id": "PRODUCTION_INTERFACE_J1"
            },
            "databases": {
                "jobs": {
                    "server": "192.168.0.7\\SQLEXPRESS",
                    "database": "PnsiDB",
                    "username": "GeniusExcel",
                    "password": "U_8nB+zUgByuCHgC4"
                },
                "production": {
                    "server": "192.168.0.193\\SQLEXPRESS",
                    "database": "KPI_data",
                    "username": "sa",
                    "password": "Excelpro2022!"
                }
            },
            "station": {"id": "STATION_01", "name": "Jointeuse Ligne 1"}
        }
    
    def __init__(self):
        # Charger la configuration
        self.load_config()
        
        # Configuration PLC principal (Job + Alertes)
        self.main_plc_ip = self.config['plc']['main']['ip']
        self.main_plc_port = self.config['plc']['main']['port']
        self.main_fins_instance = None
        
        # Configuration PLC production (Feuilles, Temps d'arrêt, Palette)
        self.prod_plc_ip = self.config['plc']['production']['ip']
        self.prod_plc_port = self.config['plc']['production']['port']
        self.prod_fins_instance = None
        
        # NOUVEAU : Module de détection de feuilles
        if PAPER_DETECTION_AVAILABLE and self.config.get('paper_detection', {}).get('enabled', False):
            # Passer la configuration au module de détection
            self.paper_detection = PaperDetectionModule(
                interface_callback=self.on_paper_detection,
                config=self.config['paper_detection']
            )
        else:
            self.paper_detection = None
        
        self.area_code = b'\x82'
        self.palette_address = 8570
        self.sheets_address = 3100  # D3100 pour nombre de feuilles
        self.downtime_address = 3150  # D3150 pour temps d'arrêt
        
        # Nouvelles adresses pour les alertes (sur PLC principal)
        self.job_end_bit_address = 29  # W29.00 - Fin de job
        self.palette_end_bit_address = 29  # W29.01 - Fin de palette
        self.work_bit_area_code = b'\x31'  # Work Bit Memory Area
        
        # Variables d'état pour les alertes
        self.job_end_active = False
        self.palette_end_active = False
        self.paper_detection_active = False
        
        # Configuration base de données JOB
        self.db_server = self.config['databases']['jobs']['server']
        self.db_name = self.config['databases']['jobs']['database']
        self.db_user = self.config['databases']['jobs']['username']
        self.db_password = self.config['databases']['jobs']['password']
        
        # Configuration base de données PRODUCTION
        self.prod_db_server = self.config['databases']['production']['server']
        self.prod_db_name = self.config['databases']['production']['database']
        self.prod_db_user = self.config['databases']['production']['username']
        self.prod_db_password = self.config['databases']['production']['password']
        
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
        
        # NOUVEAU : Démarrer le module de détection
        if PAPER_DETECTION_AVAILABLE and self.paper_detection:
            self.start_paper_detection()
    
    def create_interface(self):
        """Crée l'interface graphique"""
        self.root = tk.Tk()
        self.root.title("Interface Complète de Production V2 - Jointeuse (3 Barres)")
        
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
        
        # Configuration COMPLÈTE du grid principal avec nouveau layout
        self.root.grid_rowconfigure(0, weight=1)                # Contenu principal extensible (plus de titre)
        self.root.grid_rowconfigure(1, weight=0, minsize=50)   # Barre de statut fixe
        self.root.grid_columnconfigure(0, weight=1)
        
        # Container principal DIRECT dans root
        # Configuration des colonnes : 1/3 pour infos, 2/3 pour le reste
        self.root.grid_columnconfigure(1, weight=33, uniform="col")  # Colonne gauche 33%
        self.root.grid_columnconfigure(2, weight=67, uniform="col")  # Colonne droite 67% (milieu + graphique)
        
        # Colonne gauche - Informations Job et Palette (1/3)
        self.left_frame = tk.Frame(self.root, bg='#f0f0f0')
        self.left_frame.grid(row=0, column=1, sticky='nsew', padx=(10, 5), pady=10)
        
        # Colonne droite - Sections milieu et graphique (2/3)
        self.right_container = tk.Frame(self.root, bg='#f0f0f0')
        self.right_container.grid(row=0, column=2, sticky='nsew', padx=(5, 10), pady=10)
        
        # Configuration du grid pour le container droit
        self.right_container.grid_rowconfigure(0, weight=0, minsize=140)  # Section milieu hauteur fixe
        self.right_container.grid_rowconfigure(1, weight=1)  # Graphique prend le reste de l'espace
        self.right_container.grid_columnconfigure(0, weight=1)
        
        # Section milieu dans la partie haute du container droit
        self.middle_frame = tk.Frame(self.right_container, bg='#f0f0f0')
        self.middle_frame.grid(row=0, column=0, sticky='nsew', pady=(0, 10))
        
        # Section graphique dans la partie basse du container droit
        self.graph_frame = tk.Frame(self.right_container, bg='#f0f0f0')
        self.graph_frame.grid(row=1, column=0, sticky='nsew')
        
        # Créer les sections
        self.create_left_section()
        self.create_middle_section()
        self.create_graph_section()
        
        # Status bar avec heure (ligne 1 du grid principal)
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
        """Crée la section milieu avec feuilles et temps d'arrêt côte à côte"""
        # Configuration du grid pour la section milieu - 2 colonnes égales
        self.middle_frame.grid_rowconfigure(0, weight=1)  # Une seule ligne
        self.middle_frame.grid_columnconfigure(0, weight=1)  # Feuilles à gauche
        self.middle_frame.grid_columnconfigure(1, weight=1)  # Temps d'arrêt à droite
        
        # Nombre de feuilles produites (côté gauche)
        sheets_frame = tk.Frame(self.middle_frame, bg='#34495e', relief=tk.RAISED, bd=3)
        sheets_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        sheets_frame.grid_rowconfigure(0, weight=0, minsize=35)  # Hauteur fixe pour le titre
        sheets_frame.grid_rowconfigure(1, weight=1, minsize=80)  # Hauteur minimale pour le chiffre
        sheets_frame.grid_columnconfigure(0, weight=1)
        
        sheets_title = tk.Label(
            sheets_frame,
            text="Nombre de feuilles produites",
            font=self.header_font,
            bg='#34495e',
            fg='white'
        )
        sheets_title.grid(row=0, column=0, pady=(8, 2), sticky='ew')  # Centré et collé en haut
        
        self.sheets_var = tk.StringVar(value="0")  # Valeur par défaut dynamique
        self.sheets_label = tk.Label(
            sheets_frame,
            textvariable=self.sheets_var,
            font=font.Font(family="Arial", size=52, weight="bold"),  # Taille augmentée
            bg='#34495e',
            fg='#2ecc71',  # VERT pour correspondre au graphique
            relief=tk.SUNKEN,
            bd=2
        )
        self.sheets_label.grid(row=1, column=0, sticky='nsew', pady=(2, 8))  # Prend tout l'espace
        
        # Section temps d'arrêt (côté droit)
        downtime_frame = tk.Frame(self.middle_frame, bg='#2c3e50', relief=tk.RAISED, bd=3)
        downtime_frame.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        downtime_frame.grid_rowconfigure(0, weight=0, minsize=35)  # Hauteur fixe pour le titre
        downtime_frame.grid_rowconfigure(1, weight=1, minsize=80)  # Hauteur minimale pour le chiffre
        downtime_frame.grid_columnconfigure(0, weight=1)
        
        downtime_title = tk.Label(
            downtime_frame,
            text="Temps d'arrêt",
            font=self.header_font,
            bg='#2c3e50',
            fg='white'
        )
        downtime_title.grid(row=0, column=0, pady=(8, 2), sticky='ew')  # Centré et collé en haut
        
        self.downtime_var = tk.StringVar(value="00:00:00")  # Valeur par défaut dynamique
        self.downtime_label = tk.Label(
            downtime_frame,
            textvariable=self.downtime_var,
            font=font.Font(family="Arial", size=42, weight="bold"),  # Taille augmentée
            bg='#2c3e50',
            fg='#e74c3c',  # ROUGE pour correspondre au graphique
            relief=tk.SUNKEN,
            bd=2
        )
        self.downtime_label.grid(row=1, column=0, sticky='nsew', pady=(2, 8))  # Prend tout l'espace
    
    def create_graph_section(self):
        """Crée la section graphique de production"""
        # Section graphique de production
        self.create_production_chart(self.graph_frame)
    
    def create_job_section(self, parent):
        """Crée la section JOB NO avec hauteur réduite"""
        job_frame = tk.Frame(parent, bg='#34495e', relief=tk.RAISED, bd=2)
        job_frame.pack(fill=tk.X, pady=(0, 10))  # Réduire l'espacement
        
        # Label JOB NO
        job_label = tk.Label(
            job_frame,
            text="JOB NO",
            font=self.header_font,
            bg='#34495e',
            fg='white'
        )
        job_label.pack(side=tk.LEFT, padx=10, pady=8)  # Réduire padding vertical
        
        # Numéro de job
        self.job_number_var = tk.StringVar(value="147310")
        self.job_number_label = tk.Label(
            job_frame,
            textvariable=self.job_number_var,
            font=font.Font(family="Arial", size=36, weight="bold"),  # Réduire la taille
            bg='#34495e',
            fg='#f39c12',
            relief=tk.SUNKEN,
            bd=2,
            width=8  # Réduire la largeur
        )
        self.job_number_label.pack(side=tk.RIGHT, padx=10, pady=5)  # Réduire padding
    
    def create_info_section(self, parent):
        """Crée la section des informations avec espacement optimisé"""
        info_frame = tk.Frame(parent, bg='#f0f0f0')
        info_frame.pack(fill=tk.X, pady=(0, 10))  # Réduire l'espacement vertical
        
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
            row_frame.pack(fill=tk.X, pady=1)  # Réduire l'espacement entre les lignes
            
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
            label.pack(side=tk.LEFT, padx=10, pady=6)  # Réduire padding vertical
            
            # Valeur
            self.info_vars[var_name] = tk.StringVar()
            if var_name == "essence":
                self.info_vars[var_name].set("Maple")
            elif var_name == "coupe":
                self.info_vars[var_name].set("FLAT-CUT")
            elif var_name == "dimension":
                self.info_vars[var_name].set("75' x 50'")
            elif var_name == "agencement":
                self.info_vars[var_name].set("PLK-MATCH")
            elif var_name == "description":
                self.info_vars[var_name].set("TR-MAPLE-PLK-75 X 50")
            elif var_name == "mode":
                self.info_vars[var_name].set("Non spécifié")
            
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
            value_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), pady=3)  # Réduire padding
    
    def create_palette_section(self, parent):
        """Crée la section palette avec plus d'espace pour la liste"""
        palette_frame = tk.Frame(parent, bg='#ecf0f1', relief=tk.RAISED, bd=1)
        palette_frame.pack(fill=tk.BOTH, expand=True)  # Prendre tout l'espace restant disponible
        
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
        
        # Zone de texte pour liste de palettes avec scrollbar
        text_frame = tk.Frame(palette_frame, bg='white')
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))
        
        self.palette_text = tk.Text(
            text_frame,
            font=self.value_font,
            bg='white',
            fg='#2c3e50',
            relief=tk.SUNKEN,
            bd=1,
            wrap=tk.NONE,  # Pas de retour à la ligne automatique
            state=tk.DISABLED,  # En lecture seule
            height=10  # Hauteur minimale pour voir plusieurs palettes
        )
        
        # Scrollbar verticale
        scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.palette_text.yview)
        self.palette_text.configure(yscrollcommand=scrollbar.set)
        
        # Pack les éléments
        self.palette_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
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
        chart_frame.pack(fill=tk.BOTH, expand=True)
        
        # Titre du graphique (UNIQUE)
        chart_title = tk.Label(
            chart_frame,
            text="Production par heure",
            font=self.header_font,
            bg='#2c3e50',
            fg='white'
        )
        chart_title.pack(pady=(10, 5))
        
        # Créer la figure matplotlib avec ajustements
        self.figure = Figure(figsize=(14, 8), dpi=80, facecolor='#2c3e50')
        self.ax = self.figure.add_subplot(111, facecolor='#34495e')
        
        # Configurer le style du graphique
        self.ax.tick_params(colors='white', labelsize=11)
        self.ax.spines['bottom'].set_color('white')
        self.ax.spines['top'].set_color('white')
        self.ax.spines['right'].set_color('white')
        self.ax.spines['left'].set_color('white')
        
        # Canvas matplotlib dans tkinter - avec marges ajustées
        self.canvas = FigureCanvasTkAgg(self.figure, chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 10))
        
        # Initialiser le graphique avec des données vides
        self.update_production_chart()
    
    def create_status_bar(self):
        """Crée la barre de statut visible en bas sur toute la largeur"""
        status_frame = tk.Frame(self.root, bg='#34495e', relief=tk.RAISED, bd=2, height=40)
        status_frame.grid(row=1, column=0, columnspan=3, sticky='ew', padx=0, pady=(0, 0))  # Toute la largeur
        status_frame.grid_propagate(False)  # Maintenir la hauteur fixe
        
        # Configuration du grid pour la barre de statut
        status_frame.grid_columnconfigure(0, weight=1)
        status_frame.grid_columnconfigure(1, weight=0)
        
        # Message de statut pour la palette
        self.status_var = tk.StringVar(value="✓ Palette FRE-39764-147332 ajoutée à la liste")
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
        self.current_time_var = tk.StringVar(value="09:15:35")
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
        """Connexion aux deux PLCs"""
        try:
            self.main_fins_instance = TCPFinsConnection()
            self.main_fins_instance.connect(self.main_plc_ip, self.main_plc_port)
            
            self.prod_fins_instance = TCPFinsConnection()
            self.prod_fins_instance.connect(self.prod_plc_ip, self.prod_plc_port)
            
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
        """Lit les données des deux PLCs"""
        try:
            # ========== LECTURE PLC PRINCIPAL (192.168.0.175) ==========
            # Lire les bits W29.00 et W29.01 depuis PLC principal
            job_end_bit = False
            palette_end_bit = False
            
            if self.main_fins_instance:
                try:
                    
                    # Lire W29.00 (fin de job) - utiliser Work Bit Memory
                    job_end_address = struct.pack('>HB', self.job_end_bit_address, 0)  # W29.00
                    response = self.main_fins_instance.memory_area_read(
                        self.work_bit_area_code, job_end_address, 1
                    )
                    if response and len(response) >= 15:
                        bit_data = response[14]  # Un seul byte pour le bit
                        job_end_bit = bool(bit_data & 0x01)
                    
                    # Lire W29.01 (fin de palette) - utiliser Work Bit Memory
                    palette_end_address = struct.pack('>HB', self.palette_end_bit_address, 1)  # W29.01
                    response = self.main_fins_instance.memory_area_read(
                        self.work_bit_area_code, palette_end_address, 1
                    )
                    if response and len(response) >= 15:
                        bit_data = response[14]  # Un seul byte pour le bit
                        palette_end_bit = bool(bit_data & 0x01)
                        
                except Exception as e:
                    pass
            
            # ========== LECTURE PLC PRODUCTION (192.168.0.157) ==========
            job_number = None
            palette_code = None
            sheets_count = 0
            downtime_seconds = 0
            
            if self.prod_fins_instance:
                
                # Lire JOB depuis D8500 (même PLC que palette)
                d8500_address = b'\x21\x34\x00'
                response = self.prod_fins_instance.memory_area_read(self.area_code, d8500_address, 2)
                
                if response and len(response) >= 18:
                    data = response[14:18]
                    part1, part2 = struct.unpack('>HH', data)
                    if part1 > 0 or part2 > 0:
                        job_number = part1 * 10000 + part2
                
                # Lire PALETTE depuis PLC production
                memory_address = struct.pack('>HB', self.palette_address, 0)
                response = self.prod_fins_instance.memory_area_read(self.area_code, memory_address, 15)
                
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
                
                # Lire nombre de feuilles depuis D3100
                sheets_address = struct.pack('>HB', self.sheets_address, 0)
                response = self.prod_fins_instance.memory_area_read(self.area_code, sheets_address, 2)
                
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
                response = self.prod_fins_instance.memory_area_read(self.area_code, downtime_address, 2)
                
                if response and len(response) >= 18:
                    # Essayer comme WORD 16-bit
                    data_word = response[14:16]
                    downtime_word = struct.unpack('>H', data_word)[0]
                    
                    # Essayer comme DWORD 32-bit
                    data_dword = response[14:18]
                    downtime_dword = struct.unpack('>I', data_dword)[0]
                    
                    # Utiliser la valeur WORD si non-zéro, sinon DWORD
                    downtime_seconds = downtime_word if downtime_word > 0 else downtime_dword
            
            # Mettre à jour les variables d'état
            self.job_end_active = job_end_bit
            self.palette_end_active = palette_end_bit
            
            
            return job_number, palette_code, sheets_count, downtime_seconds
            
        except Exception as e:
            self.update_status(f"Erreur lecture PLC: {e}")
            return None, None, 0, 0
    
    def write_job_to_plc(self, job_number):
        """Écrit le numéro de job dans le PLC à l'adresse D8500"""
        try:
            
            if not self.prod_fins_instance:
                if not self.connect_to_plc():
                    self.update_status("Erreur: Pas de connexion PLC production pour écriture job")
                    return False
            
            # Convertir le job en 2 mots de 16 bits (comme dans la lecture)
            part1 = job_number // 10000  # Les 2 premiers chiffres
            part2 = job_number % 10000   # Les 4 derniers chiffres
            
            
            # Préparer les données à écrire
            data = struct.pack('>HH', part1, part2)
            
            # Adresse D8500
            d8500_address = b'\x21\x34\x00'
            
            # Écrire vers le PLC production avec number_of_items=2 (2 mots)
            response = self.prod_fins_instance.memory_area_write(
                self.area_code, 
                d8500_address, 
                data, 
                2  # number_of_items: 2 mots
            )
            
            
            if response:
                self.update_status(f"Job {job_number} écrit dans le PLC production")
                return True
            else:
                self.update_status("Erreur: Échec écriture job PLC production")
                return False
                
        except Exception as e:
            self.update_status(f"Erreur écriture job PLC production: {e}")
            return False
    
    def write_palette_to_plc(self, palette_code):
        """Écrit le code palette dans le PLC à l'adresse D8570"""
        try:
            if not self.prod_fins_instance:
                if not self.connect_to_plc():
                    self.update_status("Erreur: Pas de connexion PLC production pour écriture palette")
                    return False
            
            # Préparer la chaîne palette (30 caractères max)
            palette_padded = palette_code.ljust(30, '\x00')[:30]
            
            # Convertir en mots de 16 bits
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
            
            # Adresse D8570
            memory_address = struct.pack('>HB', self.palette_address, 0)
            
            # Écrire vers le PLC production avec number_of_items=15 (15 mots pour 30 caractères)
            response = self.prod_fins_instance.memory_area_write(
                self.area_code, 
                memory_address, 
                data, 
                15  # number_of_items: 15 mots pour 30 caractères
            )
            
            if response:
                self.update_status(f"Palette {palette_code} écrite dans le PLC production")
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
            if not self.main_fins_instance:
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
                self.main_fins_instance.memory_area_write(self.area_code, hex_address, clear_data, num_words)
            
            return True
            
        except Exception as e:
            return False
    
    def write_job_info_to_plc(self, job_info):
        """Écrit les informations du job dans le PLC pour affichage HMI"""
        if not job_info:
            return False
        
        try:
            
            if not self.main_fins_instance:
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
                    response = self.main_fins_instance.memory_area_write(self.area_code, hex_address, write_data, len(words))
            
            # Écrire toutes les informations
            write_ascii_string(essence, essence_address, 15)
            write_ascii_string(coupe, coupe_address, 10)
            write_ascii_string(dimensions, dimensions_address, 10)
            write_ascii_string(agencement, agencement_address, 15)
            write_ascii_string(description, description_address, 15)
            
            return True
            
        except Exception as e:
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
        """Met à jour l'affichage des données avec debug"""
        
        # Mise à jour côté gauche
        if self.current_job:
            job_display = f"{self.current_job:06d}"
            self.job_number_var.set(job_display)
        else:
            self.job_number_var.set("147310")  # Valeur par défaut correspondant à l'image
        
        if self.current_job_info:
            for key, var in self.info_vars.items():
                value = self.current_job_info.get(key, "Non spécifié")
                var.set(value)
        
        # Mettre à jour la liste des palettes
        self.update_palette_list()
        
        # Mise à jour des données de production - UTILISER LES VRAIES DONNÉES DYNAMIQUES
        # Mettre à jour le nombre de feuilles
        sheets_display = str(self.current_sheets)
        self.sheets_var.set(sheets_display)
        
        # Mettre à jour le temps d'arrêt
        formatted_downtime = self.format_downtime(self.current_downtime)
        self.downtime_var.set(formatted_downtime)
        
        # NOUVEAU: Mettre à jour les couleurs d'alerte
        self.update_alert_colors()
        
        # NOUVEAU: Mettre à jour le message de statut avec les alertes
        alert_message = self.get_alert_message()
        self.status_var.set(alert_message)
        
        # Forcer la mise à jour de l'interface
        self.root.update_idletasks()
    
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
            
            # Récupérer les données de production par heure depuis TABLE_FEUILLES
            query_production = """
            SELECT 
                DATEPART(HOUR, TIMESTAMP) as Heure,
                SUM(NB_JOINT) as NbJoints,
                SUM(NB_COUPON) as NbCoupons,
                COUNT(*) as NbFeuilles,
                SUM(DUREE) as TotalDuree
            FROM dbo.TABLE_FEUILLES 
            WHERE LIGNE = 'L1' 
                AND CAST(TIMESTAMP as DATE) = ?
                AND DATEPART(HOUR, TIMESTAMP) BETWEEN 7 AND 21
                AND NB_JOINT BETWEEN 0 AND 50
                AND NB_COUPON BETWEEN 1 AND 50
            GROUP BY DATEPART(HOUR, TIMESTAMP)
            ORDER BY DATEPART(HOUR, TIMESTAMP)
            """
            
            # Récupérer les VRAIS temps d'arrêt depuis TABLE_ARRETS
            query_arrets = """
            SELECT 
                DATEPART(HOUR, TIMESTAMP) as Heure,
                SUM(DUREE) as TotalArrets
            FROM dbo.TABLE_ARRETS 
            WHERE LIGNE = 'L1' 
                AND CAST(TIMESTAMP as DATE) = ?
                AND DATEPART(HOUR, TIMESTAMP) BETWEEN 7 AND 21
            GROUP BY DATEPART(HOUR, TIMESTAMP)
            ORDER BY DATEPART(HOUR, TIMESTAMP)
            """
            
            # Exécuter les deux requêtes
            cursor.execute(query_production, (today,))
            production_rows = cursor.fetchall()
            
            cursor.execute(query_arrets, (today,))
            arrets_rows = cursor.fetchall()
            
            # Créer un dictionnaire des arrêts par heure
            arrets_by_hour = {}
            for row in arrets_rows:
                heure = row.Heure
                total_arrets_sec = row.TotalArrets or 0
                # Convertir en minutes
                arrets_by_hour[heure] = round(total_arrets_sec / 60, 1)
            
            # Convertir en liste de dictionnaires avec VRAIS temps d'arrêt
            data = []
            for row in production_rows:
                heure = row.Heure
                # Récupérer le vrai temps d'arrêt depuis TABLE_ARRETS
                vrais_arrets_min = arrets_by_hour.get(heure, 0)
                
                data.append({
                    'heure': heure,
                    'joints': row.NbJoints if row.NbJoints else 0,
                    'coupons': row.NbCoupons if row.NbCoupons else 0,
                    'feuilles': row.NbFeuilles if row.NbFeuilles else 0,
                    'duree_totale': row.TotalDuree if row.TotalDuree else 0,
                    'arrets_reels_min': vrais_arrets_min
                })
            
            # Sauvegarder les données pour l'API
            self.save_production_data_cache(data)
            
            return data
            
        except Exception as e:
            self.update_status(f"Erreur récupération données: {e}")
            return []
        finally:
            conn.close()
    
    def save_production_data_cache(self, hourly_data):
        """Sauvegarde les données de production dans un fichier cache pour l'API"""
        try:
            # Calculer les statistiques du jour
            total_feuilles = sum(item['feuilles'] for item in hourly_data)
            total_joints = sum(item['joints'] for item in hourly_data)
            total_coupons = sum(item['coupons'] for item in hourly_data)
            total_arrets_min = sum(item['arrets_reels_min'] for item in hourly_data)
            
            # Calculer la projection
            projection = self.calculate_current_hour_projection(hourly_data)
            
            # Données à sauvegarder
            cache_data = {
                'timestamp': datetime.now().isoformat(),
                'machine_info': {
                    'id': self.config['station']['id'],
                    'name': self.config['station']['name'],
                    'location': self.config['station']['line'],
                    'status': 'online'
                },
                'current_stats': {
                    'feuilles_jour': total_feuilles,
                    'joints_jour': total_joints,
                    'coupons_jour': total_coupons,
                    'arrets_jour_min': round(total_arrets_min, 1),
                    'feuilles_actuelles': self.current_sheets,
                    'temps_arret_actuel': self.format_downtime(self.current_downtime),
                    'last_update': datetime.now().isoformat()
                },
                'job_info': {
                    'job_number': self.current_job,
                    'job_details': self.current_job_info if self.current_job_info else {},
                    'current_palette': self.current_palette,
                    'palette_list': self.palette_list
                },
                'hourly_data': hourly_data,
                'projection': projection
            }
            
            # Sauvegarder dans le fichier cache
            cache_file = os.path.join(os.path.dirname(__file__), 'data_cache.json')
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"❌ Erreur sauvegarde cache: {e}")
    
    def calculate_current_hour_projection(self, data):
        """Calcule la projection pour l'heure en cours basée sur la tendance actuelle"""
        current_hour = datetime.now().hour
        current_minute = datetime.now().minute
        
        # Vérifier si nous sommes dans les heures de production
        if not (7 <= current_hour <= 21):
            return None
            
        # Progression dans l'heure actuelle (0.0 à 1.0)
        hour_progress = current_minute / 60.0
        
        if hour_progress < 0.1:  # Moins de 6 minutes dans l'heure, pas assez de données
            return None
            
        # Chercher les données de l'heure actuelle
        current_hour_data = None
        for item in data:
            if item['heure'] == current_hour:
                current_hour_data = item
                break
        
        if not current_hour_data:
            return None
            
        # Calculer la tendance basée sur les données actuelles
        current_feuilles = current_hour_data['feuilles']
        current_joints = current_hour_data['joints']
        current_arrets_min = current_hour_data['arrets_reels_min']
        
        # Projection linéaire simple basée sur la progression actuelle
        projected_feuilles = current_feuilles / hour_progress if hour_progress > 0 else 0
        projected_joints_moy = (current_joints / current_feuilles) if current_feuilles > 0 else 0
        projected_arrets = current_arrets_min / hour_progress if hour_progress > 0 else 0
        
        # Limiter les projections à des valeurs réalistes
        projected_feuilles = min(projected_feuilles, 200)  # Maximum 200 feuilles/heure
        projected_arrets = min(projected_arrets, 50)       # Maximum 50 minutes d'arrêt/heure
        
        return {
            'hour': current_hour,
            'current_feuilles': current_feuilles,
            'projected_feuilles': round(projected_feuilles),
            'current_joints_moy': round(projected_joints_moy, 1),
            'projected_joints_moy': round(projected_joints_moy, 1),
            'current_arrets': current_arrets_min,
            'projected_arrets': round(projected_arrets, 1),
            'hour_progress': hour_progress
        }

    def update_production_chart(self):
        """Met à jour le graphique de production avec projection de tendance"""
        if not self.figure or not self.ax:
            return
            
        # Récupérer les nouvelles données
        data = self.get_production_data()
        
        # Calculer la projection pour l'heure en cours
        projection = self.calculate_current_hour_projection(data)
        
        # Nettoyer le graphique
        self.ax.clear()
        
        # Heures de production (7h à 21h pour heures supplémentaires)
        hours = list(range(7, 22))  # 7h à 21h
        feuilles_hr = [0] * len(hours)
        joints_moyens_hr = [0] * len(hours)
        arrets_min_hr = [0] * len(hours)  # Temps d'arrêt réel depuis la base de données
        
        # Remplir les données
        for item in data:
            if 7 <= item['heure'] <= 21:
                index = item['heure'] - 7
                feuilles_hr[index] = item['feuilles']
                # Calculer la moyenne de joints par feuille
                if item['feuilles'] > 0:
                    joints_moyens_hr[index] = round(item['joints'] / item['feuilles'], 1)
                else:
                    joints_moyens_hr[index] = 0
                
                # Utiliser les VRAIS temps d'arrêt depuis TABLE_ARRETS
                # Données réelles en minutes depuis la base de données
                arrets_min_hr[index] = item['arrets_reels_min']
        
        # Créer les barres (3 métriques avec largeur ajustée)
        x = np.arange(len(hours))
        width = 0.25  # Largeur pour 3 barres
        
        # Barres principales
        bars1 = self.ax.bar(x - width, feuilles_hr, width, 
                           label='Feuilles/hr', color='#2ecc71', alpha=0.8)
        bars2 = self.ax.bar(x, joints_moyens_hr, width, 
                           label='Joints moy./hr', color='#3498db', alpha=0.8)
        bars3 = self.ax.bar(x + width, arrets_min_hr, width, 
                           label='Arrêts min/hr', color='#e74c3c', alpha=0.8)
        
        # Ajouter la projection pour l'heure en cours (extension de la barre verte)
        if projection and projection['hour_progress'] > 0.1:
            current_hour_index = projection['hour'] - 7  # Index dans le tableau hours
            if 0 <= current_hour_index < len(hours):
                current_real = projection['current_feuilles']
                projected_total = projection['projected_feuilles']
                projected_extension = max(0, projected_total - current_real)
                
                if projected_extension > 0:
                    # Utiliser EXACTEMENT les mêmes coordonnées que la barre verte existante
                    green_bar = bars1[current_hour_index]  # Récupérer la barre verte correspondante
                    bar_x_start = green_bar.get_x()        # Position X exacte de la barre
                    bar_width = green_bar.get_width()      # Largeur exacte de la barre
                    bar_x_end = bar_x_start + bar_width
                    bar_y_bottom = current_real
                    bar_y_top = projected_total
                    
                    # Dessiner le contour en pointillés avec les coordonnées EXACTES de la barre
                    self.ax.plot(
                        [bar_x_start, bar_x_start, bar_x_end, bar_x_end, bar_x_start],
                        [bar_y_bottom, bar_y_top, bar_y_top, bar_y_bottom, bar_y_bottom],
                        color='#27ae60',
                        linestyle='--',
                        linewidth=2,
                        alpha=0.8,
                        label='Projection tendance' if current_hour_index == 0 else ""
                    )
                    
                    # Ajouter une annotation pour la projection
                    progress_percent = int(projection['hour_progress'] * 100)
                    self.ax.annotate(
                        f'Proj: {projected_total}\n({progress_percent}% heure)',
                        xy=(x[current_hour_index] - width, projected_total),
                        xytext=(5, 5),
                        textcoords='offset points',
                        fontsize=8,
                        color='#27ae60',
                        weight='bold',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8)
                    )
        
        # Configuration du graphique (SANS titre supplémentaire)
        self.ax.set_xlabel('Heures', color='white', fontsize=12)
        self.ax.set_ylabel('Quantité', color='white', fontsize=12)
        # PAS DE TITRE ICI - il est déjà dans le tkinter Label
        self.ax.set_xticks(x)
        self.ax.set_xticklabels([f"{h}h" for h in hours])
        
        # Positionner la légende en haut à droite pour ne pas masquer l'axe X
        self.ax.legend(loc='upper right', facecolor='#34495e', edgecolor='white', 
                      labelcolor='white', fontsize=10)
        
        # Ajouter les valeurs sur les barres
        def add_value_labels(bars, offset_y=0):
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    self.ax.text(bar.get_x() + bar.get_width()/2., height + offset_y + 0.5,
                               f'{height:.1f}' if isinstance(height, float) else f'{int(height)}',
                               ha='center', va='bottom', color='white', fontsize=8)
        
        add_value_labels(bars1)
        add_value_labels(bars2)
        add_value_labels(bars3)
        
        # Style du graphique
        self.ax.grid(True, alpha=0.3, color='white')
        self.ax.tick_params(colors='white', labelsize=10)
        self.ax.spines['bottom'].set_color('white')
        self.ax.spines['top'].set_color('white')
        self.ax.spines['right'].set_color('white')
        self.ax.spines['left'].set_color('white')
        
        # Ajuster le layout automatiquement
        self.figure.tight_layout(pad=1.0)
        
        # Rafraîchir l'affichage
        self.canvas.draw()
    
    def update_production_chart_timer(self):
        """Timer pour mettre à jour le graphique toutes les 2 minutes (pour projection temps réel)"""
        self.update_production_chart()
        # Programmer la prochaine mise à jour dans 2 minutes (120000 ms) pour mise à jour projection
        self.root.after(120000, self.update_production_chart_timer)
    
    def monitoring_loop(self):
        """Boucle de surveillance avec deux PLCs"""
        try:
            
            # Se connecter aux PLCs et lire les données
            if not self.connect_to_plc():
                self.update_status("⚠️ Mode fallback - PLCs non accessibles")
                
                # Mode fallback avec des données simulées qui varient
                import random
                from datetime import datetime
                
                # Simuler des données qui changent pour vérifier que l'interface fonctionne
                base_sheets = 193
                base_downtime = 1052  # 00:17:32 en secondes
                
                # Variation légère pour voir les changements
                self.current_sheets = base_sheets + random.randint(-3, 8)
                self.current_downtime = base_downtime + random.randint(-45, 90)
                
                # Simuler parfois les bits d'alerte pour tester
                current_minute = datetime.now().minute
                self.job_end_active = (current_minute % 4) == 0  # Toutes les 4 minutes
                self.palette_end_active = (current_minute % 3) == 0  # Toutes les 3 minutes
                
                
            else:
                
                # Lire les données des deux PLCs
                job_number, palette_code, sheets_count, downtime_seconds = self.read_plc_data()
                
                
                # Vérifier si le job a changé
                if job_number != self.current_job:
                    self.current_job = job_number
                    # RÉINITIALISER la liste des palettes quand le job change
                    self.palette_list = []
                    
                    if job_number:
                        self.current_job_info = self.get_job_info_from_database(job_number)
                    else:
                        self.current_job_info = None
                
                # Vérifier si la palette a changé
                if palette_code != self.current_palette:
                    self.current_palette = palette_code
                    if palette_code:
                        # Ajouter la nouvelle palette à la liste (éviter les doublons)
                        if palette_code not in self.palette_list:
                            self.palette_list.append(palette_code)
                
                # Mettre à jour les données de production
                self.current_sheets = sheets_count
                self.current_downtime = downtime_seconds
            
            # TOUJOURS mettre à jour l'affichage avec les données actuelles
            self.update_display()
            
            # Programmer la prochaine lecture dans 2 secondes (plus visible pour debug)
            self.root.after(2000, self.monitoring_loop)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.update_status(f"❌ Erreur monitoring: {e}")
            # Programmer la prochaine tentative
            self.root.after(5000, self.monitoring_loop)
    
    def start_monitoring(self):
        """Démarre la surveillance avec initialisation robuste"""
        
        # Initialiser les variables si elles ne le sont pas déjà
        if not hasattr(self, 'current_sheets'):
            self.current_sheets = 0
        if not hasattr(self, 'current_downtime'):
            self.current_downtime = 0
        if not hasattr(self, 'job_end_active'):
            self.job_end_active = False
        if not hasattr(self, 'palette_end_active'):
            self.palette_end_active = False
        if not hasattr(self, 'palette_list'):
            self.palette_list = ["FRE-39764-147332"]
            
        
        self.update_status("🔄 Démarrage surveillance...")
        
        # Faire une première mise à jour immédiate
        self.update_display()
        
        # Démarrer la surveillance immédiatement
        self.monitoring_loop()
        
        # Démarrer la mise à jour de l'heure
        self.update_time()
        
        # Démarrer la mise à jour du graphique
        self.update_production_chart_timer()
    
    def start_paper_detection(self):
        """Démarre le module de détection de feuilles"""
        try:
            if self.paper_detection and self.paper_detection.start():
                self.update_status("📷 Module de détection de feuilles activé")
            else:
                self.update_status("❌ Échec activation module de détection")
        except Exception as e:
            self.update_status(f"❌ Erreur module détection: {e}")
    
    def on_paper_detection(self, detection_active):
        """Callback appelé par le module de détection"""
        self.paper_detection_active = detection_active
        
        # Programmer l'effacement automatique après 10 secondes si détection positive
        if detection_active:
            self.root.after(10000, self.clear_paper_detection_alert)
    
    def clear_paper_detection_alert(self):
        """Efface l'alerte de détection de feuille"""
        self.paper_detection_active = False
        if hasattr(self, 'paper_detection'):
            self.paper_detection.clear_detection()
        # Forcer la mise à jour immédiate de l'affichage
        self.update_display()
    
    def on_closing(self):
        """Gestionnaire de fermeture"""
        self.running = False
        
        # Arrêter le module de détection
        if hasattr(self, 'paper_detection'):
            try:
                self.paper_detection.stop()
            except:
                pass
        
        if self.main_fins_instance:
            try:
                self.main_fins_instance.close()
            except:
                pass
        if self.prod_fins_instance:
            try:
                self.prod_fins_instance.close()
            except:
                pass
        self.root.destroy()
    
    def run(self):
        """Lance l'interface"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
    
    def update_alert_colors(self):
        """Met à jour les couleurs selon les alertes W29.00, W29.01 et détection de feuille"""
        try:
            # Couleurs par défaut
            job_bg_color = '#34495e'  # Bleu par défaut
            palette_bg_color = '#ecf0f1'  # Gris par défaut
            
            # Si W29.00 (fin de job) est actif : JOB NO et Palette en rouge
            if self.job_end_active:
                job_bg_color = '#e74c3c'  # Rouge
                palette_bg_color = '#e74c3c'  # Rouge
            # Sinon si W29.01 (fin de palette) est actif : seulement Palette en rouge
            elif self.palette_end_active:
                palette_bg_color = '#e74c3c'  # Rouge
            # NOUVEAU : Si détection de feuille active : JOB NO en orange (différent mais visible)
            elif self.paper_detection_active:
                job_bg_color = '#f39c12'  # Orange pour différencier de l'alerte rouge
            
            # Appliquer les couleurs à la section JOB NO
            if hasattr(self, 'job_number_label'):
                parent_frame = self.job_number_label.master
                parent_frame.configure(bg=job_bg_color)
                # Mettre à jour aussi le label JOB NO
                for widget in parent_frame.winfo_children():
                    if isinstance(widget, tk.Label) and widget != self.job_number_label:
                        widget.configure(bg=job_bg_color)
            
            # Appliquer les couleurs à la section Palette
            if hasattr(self, 'palette_text'):
                palette_frame = self.palette_text.master.master  # Remonter au frame principal
                palette_frame.configure(bg=palette_bg_color)
                # Mettre à jour aussi le label Palette
                for widget in palette_frame.winfo_children():
                    if isinstance(widget, tk.Label):
                        widget.configure(bg=palette_bg_color)
                        
        except Exception as e:
            pass
    
    def get_alert_message(self):
        """Retourne le message d'alerte approprié"""
        if self.job_end_active or self.palette_end_active:
            return "⚠️ Changement de Job / Palette Requis"
        elif self.paper_detection_active:
            return "🔍 FEUILLE JOB/PALETTE DÉTECTÉE - Vérification requise"
        elif hasattr(self, 'palette_list') and self.palette_list:
            return f"✓ Palette {self.palette_list[-1]} ajoutée à la liste"
        else:
            return "✓ Système opérationnel - Scanner actif"

def main():
    """Fonction principale"""
    app = InterfaceGraphiqueProductionV2()
    app.run()

if __name__ == "__main__":
    main() 