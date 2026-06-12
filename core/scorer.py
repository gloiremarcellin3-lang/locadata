from qgis.core import (
    QgsVectorLayer, QgsFeature, QgsSpatialIndex,
    QgsField, QgsProject,
)
from PyQt5.QtCore import QVariant
import math

class DataCenterScorer:
    def __init__(self, weights=None):
        self.weights = weights or {
            'energie': 35, 'foncier': 25,
            'connectivite': 25, 'acceptabilite': 15
        }

    def score_energie(self, zone_geom, layer_hta):
        if not layer_hta or not layer_hta.isValid():
            return 0.0
        index = QgsSpatialIndex(layer_hta.getFeatures())
        centroid = zone_geom.centroid()
        nearest_ids = index.nearestNeighbor(centroid.asPoint(), 1)
        if not nearest_ids:
            return 0.0
        nearest_feat = layer_hta.getFeature(nearest_ids[0])
        distance = centroid.distance(nearest_feat.geometry())
        return round(max(0.0, 100.0 * (1 - distance / 5000)), 2)

    def score_foncier(self, zone_geom, layer_ocsge, layer_zan=None):
        if not layer_ocsge or not layer_ocsge.isValid():
            return 50.0
        scores_ocsge = {
            'US235': 100, 'US230': 90, 'US225': 80,
            'US215': 40,  'US120': 10, 'US110': 0, 'US100': 0,
        }
        total_area = 0.0
        weighted_score = 0.0
        for feat in layer_ocsge.getFeatures():
            intersection = zone_geom.intersection(feat.geometry())
            if intersection.isEmpty():
                continue
            area = intersection.area()
            code = feat['CODE_CS'] if 'CODE_CS' in feat.fields().names() else 'US235'
            weighted_score += scores_ocsge.get(code, 50) * area
            total_area += area
        score_base = (weighted_score / total_area) if total_area > 0 else 50.0
        if layer_zan and layer_zan.isValid():
            for feat in layer_zan.getFeatures():
                if zone_geom.intersects(feat.geometry()):
                    score_base *= 0.6
                    break
        return round(min(100.0, max(0.0, score_base)), 2)

    def score_connectivite(self, zone_geom, layer_fibre):
        if not layer_fibre or not layer_fibre.isValid():
            return 0.0
        index = QgsSpatialIndex(layer_fibre.getFeatures())
        centroid = zone_geom.centroid()
        nearest_ids = index.nearestNeighbor(centroid.asPoint(), 1)
        if not nearest_ids:
            return 0.0
        nearest_feat = layer_fibre.getFeature(nearest_ids[0])
        distance = centroid.distance(nearest_feat.geometry())
        return round(max(0.0, 100.0 * (1 - distance / 10000)), 2)

    def score_acceptabilite(self, zone_geom, densite_pop, layer_proteges=None):
        if densite_pop <= 0:
            score_pop = 100.0
        elif densite_pop >= 10000:
            score_pop = 0.0
        else:
            score_pop = 100.0 * (1 - math.log10(densite_pop + 1) / math.log10(10001))
        penalite = 0.0
        if layer_proteges and layer_proteges.isValid():
            for feat in layer_proteges.getFeatures():
                if zone_geom.intersects(feat.geometry()):
                    penalite = 40.0
                    break
        return round(max(0.0, score_pop - penalite), 2)

    def score_global(self, s_e, s_f, s_c, s_a):
        return round(
            s_e * self.weights['energie']       / 100 +
            s_f * self.weights['foncier']        / 100 +
            s_c * self.weights['connectivite']   / 100 +
            s_a * self.weights['acceptabilite']  / 100, 2
        )

    def _classe_aptitude(self, score):
        if score >= 75: return "Très favorable"
        elif score >= 55: return "Favorable"
        elif score >= 35: return "Modéré"
        elif score >= 20: return "Défavorable"
        else: return "Très défavorable"

    def run(self, layer_zones, layer_hta, layer_ocsge, layer_fibre,
            layer_zan=None, layer_proteges=None, champ_densite='DENS_POP'):
        result_layer = QgsVectorLayer(
            f"Polygon?crs={layer_zones.crs().authid()}",
            "Scores_LocaData", "memory"
        )
        provider = result_layer.dataProvider()
        fields = layer_zones.fields()
        score_fields = [
            QgsField("SC_ENERGIE",  QVariant.Double),
            QgsField("SC_FONCIER",  QVariant.Double),
            QgsField("SC_CONNECT",  QVariant.Double),
            QgsField("SC_ACCEPT",   QVariant.Double),
            QgsField("SC_GLOBAL",   QVariant.Double),
            QgsField("APTITUDE",    QVariant.String),
        ]
        provider.addAttributes(fields.toList() + score_fields)
        result_layer.updateFields()
        features_out = []
        for feat in layer_zones.getFeatures():
            geom = feat.geometry()
            densite = 0.0
            if champ_densite in feat.fields().names():
                val = feat[champ_densite]
                densite = float(val) if val else 0.0
            s_e = self.score_energie(geom, layer_hta)
            s_f = self.score_foncier(geom, layer_ocsge, layer_zan)
            s_c = self.score_connectivite(geom, layer_fibre)
            s_a = self.score_acceptabilite(geom, densite, layer_proteges)
            s_g = self.score_global(s_e, s_f, s_c, s_a)
            new_feat = QgsFeature(result_layer.fields())
            new_feat.setGeometry(geom)
            for field in fields:
                new_feat[field.name()] = feat[field.name()]
            new_feat["SC_ENERGIE"] = s_e
            new_feat["SC_FONCIER"] = s_f
            new_feat["SC_CONNECT"] = s_c
            new_feat["SC_ACCEPT"]  = s_a
            new_feat["SC_GLOBAL"]  = s_g
            new_feat["APTITUDE"]   = self._classe_aptitude(s_g)
            features_out.append(new_feat)
        provider.addFeatures(features_out)
        result_layer.updateExtents()
        return result_layer