from dataclasses import dataclass
from typing import Dict

@dataclass
class Critere:
    nom: str
    cle: str
    description: str
    poids_defaut: int
    seuil_min: float
    seuil_max: float
    unite: str = "m"
    actif: bool = True

CRITERES = {
    'energie': Critere(
        nom="Énergie", cle="energie",
        description="Proximité au réseau HTA (BDTOPO).",
        poids_defaut=35, seuil_min=0, seuil_max=5000
    ),
    'foncier': Critere(
        nom="Foncier", cle="foncier",
        description="Disponibilité foncière (OCSGE / ZAN).",
        poids_defaut=25, seuil_min=0, seuil_max=100,
        unite="score OCSGE"
    ),
    'connectivite': Critere(
        nom="Connectivité", cle="connectivite",
        description="Proximité aux nœuds fibre optique.",
        poids_defaut=25, seuil_min=0, seuil_max=10000
    ),
    'acceptabilite': Critere(
        nom="Acceptabilité territoriale", cle="acceptabilite",
        description="Densité population + espaces protégés.",
        poids_defaut=15, seuil_min=0, seuil_max=10000,
        unite="hab/km²"
    ),
}

SCORES_OCSGE = {
    'US235': 100, 'US230': 90, 'US225': 80, 'US220': 75,
    'US215': 40,  'US210': 35, 'US200': 30,
    'US130': 15,  'US120': 10, 'US115': 5,
    'US110': 0,   'US100': 0,
}

CLASSES_APTITUDE = [
    {'label': 'Très favorable',   'min': 75,  'max': 100, 'couleur': '#1a7a4a'},
    {'label': 'Favorable',        'min': 55,  'max': 74,  'couleur': '#5cb85c'},
    {'label': 'Modéré',           'min': 35,  'max': 54,  'couleur': '#f0ad4e'},
    {'label': 'Défavorable',      'min': 20,  'max': 34,  'couleur': '#d9534f'},
    {'label': 'Très défavorable', 'min': 0,   'max': 19,  'couleur': '#7b1a1a'},
]

def get_poids_defaut():
    return {cle: c.poids_defaut for cle, c in CRITERES.items()}

def valider_poids(poids):
    return abs(sum(poids.values()) - 100) <= 1

def get_classe_aptitude(score):
    for classe in CLASSES_APTITUDE:
        if classe['min'] <= score <= classe['max']:
            return classe
    return CLASSES_APTITUDE[-1]