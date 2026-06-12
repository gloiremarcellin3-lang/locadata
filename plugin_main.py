import os
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from .ui.dialog import LocaDataDialog

class LocaData:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):
        icon_path = os.path.join(
            os.path.dirname(__file__), 'resources', 'icon.png'
        )
        self.action = QAction(
            QIcon(icon_path),
            "LocaData",
            self.iface.mainWindow()
        )
        self.action.setToolTip(
            "LocaData — Localisation optimale des data centers"
        )
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&LocaData", self.action)

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginMenu("&LocaData", self.action)
        del self.action

    def run(self):
        if not self.dialog:
            self.dialog = LocaDataDialog(
                self.iface, self.iface.mainWindow()
            )
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()