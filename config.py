# config.py

import os
DB_PATH = os.path.join(os.path.dirname(__file__), "SuperMart.db")

CATEGORIES = [
    "Analgesic", "Antibiotic", "Antacid",
    "Antifungal", "Supplement", "Vaccine", "Other"
]

SUPPLIERS = [
    "GSK", "Pfizer", "Neimeth", "Meyer", "Jawa", "Others"
]

SECRET_KEY = "restock123"