# -*- coding: utf-8 -*-
import os
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction


class Maqueta3DWeb:
    def __init__(self, iface):
        self.iface = iface; self.accion = None; self.dlg = None

    def initGui(self):
        self.accion = QAction(QIcon(os.path.join(os.path.dirname(__file__), 'icono.png')), 'Maqueta 3D Web…', self.iface.mainWindow())
        self.accion.setToolTip('Plano de QGIS o vuelo de fotogrametría → página web con maqueta 3D, RA, GPS y QR')
        self.accion.triggered.connect(self.abrir)
        self.iface.addPluginToMenu('Maqueta 3D Web', self.accion); self.iface.addToolBarIcon(self.accion)

    def unload(self):
        self.iface.removePluginMenu('Maqueta 3D Web', self.accion); self.iface.removeToolBarIcon(self.accion)

    def abrir(self):
        from .dialogo import Dialogo
        if self.dlg is None: self.dlg = Dialogo(self.iface, self.iface.mainWindow())
        self.dlg.show(); self.dlg.raise_(); self.dlg.activateWindow()
