from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class Translation:
    code: str
    full_name: str
    language: str
    is_catholic: bool = False

COMMON_TRANSLATIONS = [
    Translation("NABRE", "New American Bible (Revised Edition)", "English", True),
    Translation("RSVCE", "Revised Standard Version Catholic Edition", "English", True),
    Translation("NRSVCE", "New Revised Standard Version Catholic Edition", "English", True),
    Translation("DRA", "Douay-Rheims 1899 American Edition", "English", True),
    Translation("GNT", "Good News Translation", "English", False), # Has Catholic variants
    Translation("KJV", "King James Version", "English", False),
    Translation("ESV", "English Standard Version", "English", False),
    Translation("NIV", "New International Version", "English", False),
    Translation("NRSVUE", "New Revised Standard Version Updated Edition", "English", False),
    Translation("VULGATE", "Biblia Sacra Vulgata", "Latin", True),
]

def get_translation(code: str) -> Optional[Translation]:
    code = code.upper()
    for t in COMMON_TRANSLATIONS:
        if t.code == code:
            return t
    return None
