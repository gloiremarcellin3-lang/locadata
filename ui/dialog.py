import os
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QFileDialog
from qgis.PyQt.QtCore import QThread, pyqtSignal
from qgis.core import QgsProject, QgsVectorLayer, QgsMapLayerProxyModel

from ..core.scorer import DataCenterScorer
from ..core.criteria import get_poids_defaut, valider_poids, CLASSES_APTITUDE


class ScoringThread(QThread):
    finished = pyqtSignal(object)
    error    = pyqtSignal(str)

    def __init__(self, scorer, layers, champ_densite):
        super().__init__()
        self.scorer        = scorer
        self.layers        = layers
        self.champ_densite = champ_densite

    def run(self):
        try:
            result = self.scorer.run(
                layer_zones    = self.layers['zones'],
                layer_hta      = self.layers['hta'],
                layer_ocsge    = self.layers['ocsge'],
                layer_fibre    = self.layers.get('fibre'),
                layer_zan      = self.layers.get('zan'),
                layer_proteges = self.layers.get('proteges'),
                champ_densite  = self.champ_densite,
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class LocaDataDialog(QDialog):

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface        = iface
        self.result_layer = None
        self.thread       = None
        self.setWindowTitle("LocaData — Localisation optimale des data centers")
        self.setMinimumWidth(500)
        self._build_ui()
        self._connect_signals()
        self._init_sliders()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # Onglets
        self.tabs = QtWidgets.QTabWidget()
        layout.addWidget(self.tabs)

        # --- Onglet Couches ---
        tab_couches = QtWidgets.QWidget()
        form_couches = QtWidgets.QFormLayout(tab_couches)

        self.cbo_zones = QtWidgets.QComboBox()
        self.cbo_hta   = QtWidgets.QComboBox()
        self.cbo_ocsge = QtWidgets.QComboBox()
        self.cbo_fibre = QtWidgets.QComboBox()
        self.cbo_zan   = QtWidgets.QComboBox()

        self._remplir_combos()

        form_couches.addRow("Zones d'analyse :", self.cbo_zones)
        form_couches.addRow("Réseau HTA (BDTOPO) :", self.cbo_hta)
        form_couches.addRow("Occupation sol (OCSGE) :", self.cbo_ocsge)
        form_couches.addRow("Fibre optique :", self.cbo_fibre)
        form_couches.addRow("Contraintes ZAN :", self.cbo_zan)
        self.tabs.addTab(tab_couches, "Couches")

        # --- Onglet Critères ---
        tab_criteres = QtWidgets.QWidget()
        form_criteres = QtWidgets.QFormLayout(tab_criteres)

        self.sld_energie       = QtWidgets.QSlider(1)
        self.sld_foncier       = QtWidgets.QSlider(1)
        self.sld_connectivite  = QtWidgets.QSlider(1)
        self.sld_acceptabilite = QtWidgets.QSlider(1)

        self.lbl_energie       = QtWidgets.QLabel("35 %")
        self.lbl_foncier       = QtWidgets.QLabel("25 %")
        self.lbl_connectivite  = QtWidgets.QLabel("25 %")
        self.lbl_acceptabilite = QtWidgets.QLabel("15 %")
        self.lbl_total_poids   = QtWidgets.QLabel("Total : 100 %")

        for sld in [self.sld_energie, self.sld_foncier,
                    self.sld_connectivite, self.sld_acceptabilite]:
            sld.setMinimum(0)
            sld.setMaximum(100)
            sld.setSingleStep(5)

        def _row(sld, lbl):
            w = QtWidgets.QWidget()
            h = QtWidgets.QHBoxLayout(w)
            h.setContentsMargins(0,0,0,0)
            h.addWidget(sld)
            h.addWidget(lbl)
            return w

        form_criteres.addRow("Énergie :",              _row(self.sld_energie, self.lbl_energie))
        form_criteres.addRow("Foncier :",              _row(self.sld_foncier, self.lbl_foncier))
        form_criteres.addRow("Connectivité :",         _row(self.sld_connectivite, self.lbl_connectivite))
        form_criteres.addRow("Acceptabilité :",        _row(self.sld_acceptabilite, self.lbl_acceptabilite))
        form_criteres.addRow("",                       self.lbl_total_poids)
        self.tabs.addTab(tab_criteres, "Critères")

        # --- Onglet Résultats ---
        tab_resultats = QtWidgets.QWidget()
        v_res = QtWidgets.QVBoxLayout(tab_resultats)
        self.lbl_score_moyen = QtWidgets.QLabel("—")
        self.lbl_score_moyen.setStyleSheet("font-size:28px; color:#534AB7; font-weight:bold;")
        self.txt_repartition = QtWidgets.QPlainTextEdit()
        self.txt_repartition.setReadOnly(True)
        v_res.addWidget(QtWidgets.QLabel("Score moyen global :"))
        v_res.addWidget(self.lbl_score_moyen)
        v_res.addWidget(QtWidgets.QLabel("Répartition par classe :"))
        v_res.addWidget(self.txt_repartition)
        self.tabs.addTab(tab_resultats, "Résultats")

        # --- Onglet Export ---
        tab_export = QtWidgets.QWidget()
        form_export = QtWidgets.QFormLayout(tab_export)
        self.cbo_format_export  = QtWidgets.QComboBox()
        self.cbo_format_export.addItems(["Rapport PDF", "CSV", "GeoJSON", "PNG carte"])
        self.txt_dossier_export = QtWidgets.QLineEdit()
        self.txt_titre_rapport  = QtWidgets.QLineEdit("Analyse LocaData — Île-de-France 2026")
        self.btn_parcourir      = QtWidgets.QPushButton("Parcourir...")
        self.btn_exporter       = QtWidgets.QPushButton("Exporter")
        form_export.addRow("Format :", self.cbo_format_export)
        form_export.addRow("Dossier :", self.txt_dossier_export)
        form_export.addRow("", self.btn_parcourir)
        form_export.addRow("Titre :", self.txt_titre_rapport)
        form_export.addRow("", self.btn_exporter)
        self.tabs.addTab(tab_export, "Export")

        # Boutons bas
        self.btn_calculer = QtWidgets.QPushButton("Lancer le calcul")
        self.btn_calculer.setStyleSheet(
            "background:#534AB7; color:white; padding:8px; font-weight:bold;"
        )
        self.btn_fermer = QtWidgets.QPushButton("Fermer")
        self.progressBar = QtWidgets.QProgressBar()
        self.progressBar.setVisible(False)

        h_btn = QtWidgets.QHBoxLayout()
        h_btn.addWidget(self.btn_calculer)
        h_btn.addWidget(self.btn_fermer)
        layout.addWidget(self.progressBar)
        layout.addLayout(h_btn)

    def _remplir_combos(self):
        layers = QgsProject.instance().mapLayers().values()
        noms = ["(aucune)"] + [l.name() for l in layers
                               if l.type() == l.VectorLayer]
        for cbo in [self.cbo_zones, self.cbo_hta, self.cbo_ocsge,
                    self.cbo_fibre, self.cbo_zan]:
            cbo.addItems(noms)

    def _get_layer(self, cbo):
        nom = cbo.currentText()
        if nom == "(aucune)":
            return None
        for l in QgsProject.instance().mapLayers().values():
            if l.name() == nom:
                return l
        return None

    def _init_sliders(self):
        poids = get_poids_defaut()
        self.sld_energie.setValue(poids['energie'])
        self.sld_foncier.setValue(poids['foncier'])
        self.sld_connectivite.setValue(poids['connectivite'])
        self.sld_acceptabilite.setValue(poids['acceptabilite'])
        self._update_poids()

    def _connect_signals(self):
        self.sld_energie.valueChanged.connect(self._update_poids)
        self.sld_foncier.valueChanged.connect(self._update_poids)
        self.sld_connectivite.valueChanged.connect(self._update_poids)
        self.sld_acceptabilite.valueChanged.connect(self._update_poids)
        self.btn_calculer.clicked.connect(self._lancer_calcul)
        self.btn_exporter.clicked.connect(self._exporter)
        self.btn_parcourir.clicked.connect(self._parcourir)
        self.btn_fermer.clicked.connect(self.close)

    def _update_poids(self):
        p = self._get_poids()
        self.lbl_energie.setText(f"{p['energie']} %")
        self.lbl_foncier.setText(f"{p['foncier']} %")
        self.lbl_connectivite.setText(f"{p['connectivite']} %")
        self.lbl_acceptabilite.setText(f"{p['acceptabilite']} %")
        total = sum(p.values())
        self.lbl_total_poids.setText(f"Total : {total} %")
        ok = abs(total - 100) <= 1
        self.lbl_total_poids.setStyleSheet(
            "color:green;font-weight:bold" if ok else "color:red;font-weight:bold"
        )
        self.btn_calculer.setEnabled(ok)

    def _get_poids(self):
        return {
            'energie':       self.sld_energie.value(),
            'foncier':       self.sld_foncier.value(),
            'connectivite':  self.sld_connectivite.value(),
            'acceptabilite': self.sld_acceptabilite.value(),
        }

    def _lancer_calcul(self):
        layers = {
            'zones':    self._get_layer(self.cbo_zones),
            'hta':      self._get_layer(self.cbo_hta),
            'ocsge':    self._get_layer(self.cbo_ocsge),
            'fibre':    self._get_layer(self.cbo_fibre),
            'zan':      self._get_layer(self.cbo_zan),
        }
        if not layers['zones'] or not layers['hta'] or not layers['ocsge']:
            QMessageBox.warning(self, "Couches manquantes",
                "Sélectionnez au minimum : Zones, HTA et OCSGE.")
            return
        poids = self._get_poids()
        if not valider_poids(poids):
            QMessageBox.warning(self, "Poids invalides",
                "La somme des poids doit être égale à 100 %.")
            return
        self.btn_calculer.setEnabled(False)
        self.btn_calculer.setText("Calcul en cours...")
        self.progressBar.setVisible(True)
        self.progressBar.setRange(0, 0)
        scorer = DataCenterScorer(weights=poids)
        self.thread = ScoringThread(scorer, layers, 'DENS_POP')
        self.thread.finished.connect(self._on_termine)
        self.thread.error.connect(self._on_erreur)
        self.thread.start()

    def _on_termine(self, result_layer):
        self.result_layer = result_layer
        self.progressBar.setVisible(False)
        self.btn_calculer.setEnabled(True)
        self.btn_calculer.setText("Lancer le calcul")
        QgsProject.instance().addMapLayer(result_layer)
        scores = [f['SC_GLOBAL'] for f in result_layer.getFeatures()
                  if f['SC_GLOBAL'] is not None]
        if scores:
            moy = sum(scores) / len(scores)
            self.lbl_score_moyen.setText(f"{moy:.1f} / 100")
            from ..core.criteria import get_classe_aptitude
            comptage = {}
            for s in scores:
                label = get_classe_aptitude(s)['label']
                comptage[label] = comptage.get(label, 0) + 1
            self.txt_repartition.setPlainText(
                "\n".join(f"• {l} : {n} zone(s)" for l, n in comptage.items())
            )
        self.tabs.setCurrentIndex(2)
        QMessageBox.information(self, "Terminé",
            f"Analyse terminée — {result_layer.featureCount()} zones analysées.")

    def _on_erreur(self, message):
        self.progressBar.setVisible(False)
        self.btn_calculer.setEnabled(True)
        self.btn_calculer.setText("Lancer le calcul")
        QMessageBox.critical(self, "Erreur", message)

    def _parcourir(self):
        dossier = QFileDialog.getExistingDirectory(self, "Dossier d'export")
        if dossier:
            self.txt_dossier_export.setText(dossier)

    def _exporter(self):
        if not self.result_layer:
            QMessageBox.warning(self, "Aucun résultat",
                "Lancez d'abord le calcul.")
            return
        dossier = self.txt_dossier_export.text()
        if not dossier:
            QMessageBox.warning(self, "Dossier manquant",
                "Indiquez un dossier de destination.")
            return
        fmt = self.cbo_format_export.currentText()
        if "CSV" in fmt:
            import csv
            chemin = os.path.join(dossier, "scores_locadata.csv")
            champs = ['SC_ENERGIE','SC_FONCIER','SC_CONNECT',
                      'SC_ACCEPT','SC_GLOBAL','APTITUDE']
            with open(chemin, 'w', newline='', encoding='utf-8') as f:
                w = csv.DictWriter(f, fieldnames=champs)
                w.writeheader()
                for feat in self.result_layer.getFeatures():
                    w.writerow({c: feat[c] for c in champs})
            QMessageBox.information(self, "Export réussi", f"CSV : {chemin}")
        elif "GeoJSON" in fmt:
            from qgis.core import QgsVectorFileWriter
            chemin = os.path.join(dossier, "scores_locadata.geojson")
            QgsVectorFileWriter.writeAsVectorFormat(
                self.result_layer, chemin, "utf-8",
                self.result_layer.crs(), "GeoJSON"
            )
            QMessageBox.information(self, "Export réussi", f"GeoJSON : {chemin}")
        elif "PDF" in fmt:
            from ..outputs.pdf_export import exporter_rapport_pdf
            chemin = os.path.join(dossier, "rapport_locadata.pdf")
            exporter_rapport_pdf(self.result_layer, chemin,
                                 self.txt_titre_rapport.text(),
                                 self._get_poids())
            QMessageBox.information(self, "Export réussi", f"PDF : {chemin}")
        else:
            chemin = os.path.join(dossier, "carte_locadata.png")
            self.iface.mapCanvas().saveAsImage(chemin)
            QMessageBox.information(self, "Export réussi", f"PNG : {chemin}")