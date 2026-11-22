# -*- coding: utf-8 -*-
"""Ventana del complemento Maqueta 3D Web."""
import os, json, traceback, datetime, unicodedata
from qgis.core import QgsSettings, QgsRasterLayer, QgsProject, QgsMapLayerProxyModel, Qgis
from qgis.gui import QgsFileWidget, QgsColorButton, QgsProjectionSelectionWidget, QgsMapLayerComboBox
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget, QWidget, QRadioButton, QButtonGroup,
                                 QStackedWidget, QComboBox, QDoubleSpinBox, QLineEdit, QTableWidget, QTableWidgetItem, QPushButton,
                                 QLabel, QPlainTextEdit, QCheckBox, QMessageBox, QHeaderView, QApplication, QInputDialog, QGroupBox,
                                 QScrollArea, QFileDialog)

CLAVE = 'maqueta3dweb/perfiles'
PERFIL_INICIAL = {
    'nombre_perfil': 'Osney – INVERCOAL', 'empresa': 'Grupo Invercoal', 'logo': '', 'color': '', 'mostrar_elaboro': True,
    'autor': 'Osney Izaquita',
    'titulos': [['Ingeniero Geólogo', 'Universidad Pedagógica y Tecnológica de Colombia'],
                ['Especialista en Aplicación de TIC para la Enseñanza', 'Universidad de Santander'],
                ['Magíster en Gestión de Cuencas Hidrográficas', 'Universidad Santo Tomás'],
                ['Candidato a Magíster en Recursos Digitales Aplicados a la Educación', 'Universidad de Cartagena'],
                ['Piloto de drones', '']]}
USOS = ['—', 'Etiqueta en la página', 'Chincheta 3D (azul)', 'Chincheta 3D (negra)']
CM = dict(usar=0, capa=1, elem=2, tipo=3, color=4, ancho=5, alto=6, cota=7)          # columnas de la tabla de capas
CG = dict(ver=0, nombre=1, E=2, N=3, Z=4, ch4=5, fecha=6, u=7, Q=8)                    # columnas de la tabla de frentes


def perfiles():
    try: lista = json.loads(QgsSettings().value(CLAVE, '[]'))
    except Exception: lista = []
    return lista or [PERFIL_INICIAL]


def guardar_perfiles(lista): QgsSettings().setValue(CLAVE, json.dumps(lista, ensure_ascii=False))


def _num(t):
    """'1,25' / '1.25' / '' → float o None."""
    t = (t or '').strip().replace('%', '').replace(',', '.')
    try: return float(t) if t else None
    except ValueError: return None


def _llave(t):
    return ''.join(c for c in unicodedata.normalize('NFD', t or '') if unicodedata.category(c) != 'Mn').upper().strip()


def _filtro_raster():
    try: return Qgis.LayerFilter.RasterLayer
    except AttributeError: return QgsMapLayerProxyModel.RasterLayer


class Dialogo(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent); self.iface = iface; self.proyecto = None; self.datos_cad = None; self.mina_prev = None
        self.setWindowTitle('Maqueta 3D Web · plano, vuelo o mina a página con RA y QR'); self.resize(980, 820)
        L = QVBoxLayout(self); tabs = QTabWidget(); L.addWidget(tabs)
        tabs.addTab(self._tab_insumo(), '1 · Insumo'); tabs.addTab(self._tab_autor(), '2 · Autor y empresa')
        tabs.addTab(self._tab_plano(), '3 · Textos del plano'); tabs.addTab(self._tab_publicar(), '4 · Publicar')
        self.log = QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(160); L.addWidget(self.log)
        fila = QHBoxLayout(); fila.addStretch(1)
        self.b_gen = QPushButton('Generar'); self.b_gen.setDefault(True); self.b_gen.clicked.connect(self.generar)
        b_cer = QPushButton('Cerrar'); b_cer.clicked.connect(self.close); fila.addWidget(self.b_gen); fila.addWidget(b_cer); L.addLayout(fila)
        self._cargar_perfil(0)

    # ---------------- 1. Insumo ----------------
    def _tab_insumo(self):
        w = QWidget(); L = QVBoxLayout(w)
        fila = QHBoxLayout(); fila.addWidget(QLabel('<b>Tipo de insumo:</b>'))
        self.r_gpkg = QRadioButton('Plano de QGIS (GeoPackage + DEM)'); self.r_foto = QRadioButton('Vuelo con dron (fotogrametría)')
        self.r_mina = QRadioButton('Mina subterránea (plano DWG o DXF)')
        self.r_gpkg.setChecked(True); g = QButtonGroup(w)
        for r in (self.r_gpkg, self.r_foto, self.r_mina): g.addButton(r); fila.addWidget(r); r.toggled.connect(self._insumo_cambio)
        fila.addStretch(1); L.addLayout(fila)
        self.pila = QStackedWidget(); L.addWidget(self.pila)
        # GeoPackage
        pg = QWidget(); F = QFormLayout(pg)
        self.f_gpkg = QgsFileWidget(); self.f_gpkg.setFilter('GeoPackage o proyecto de QGIS (*.gpkg *.qgz *.qgs)'); self.f_gpkg.fileChanged.connect(self._gpkg_cambio)
        self.c_proy = QComboBox(); self.c_proy.currentTextChanged.connect(self._proy_cambio)
        self.c_dis = QComboBox(); self.c_dis.currentTextChanged.connect(self._dis_cambio)
        self.c_mapa = QComboBox(); self.c_dem = QComboBox(); self.f_dem = QgsFileWidget(); self.f_dem.setFilter('Ráster (*.tif *.tiff *.vrt *.img *.asc)')
        self.f_dem.setEnabled(False); self.c_dem.currentIndexChanged.connect(lambda i: self.f_dem.setEnabled(self.c_dem.currentData() == '__archivo__'))
        self.s_ve = QDoubleSpinBox(); self.s_ve.setRange(1, 10); self.s_ve.setSingleStep(0.5); self.s_ve.setValue(2.5)
        F.addRow('GeoPackage o proyecto (.qgz):', self.f_gpkg); F.addRow('Proyecto guardado:', self.c_proy)
        F.addRow('Diseño de impresión:', self.c_dis); F.addRow('Mapa principal:', self.c_mapa)
        F.addRow('Modelo de elevación (DEM):', self.c_dem); F.addRow('   …o archivo aparte:', self.f_dem)
        F.addRow('Exageración vertical:', self.s_ve)
        self.t_capas = QTableWidget(0, 3); self.t_capas.setHorizontalHeaderLabels(['Capa', 'Usar como', 'Campo del nombre'])
        h = self.t_capas.horizontalHeader(); h.setSectionResizeMode(0, QHeaderView.Stretch); h.setSectionResizeMode(1, QHeaderView.Interactive); h.setSectionResizeMode(2, QHeaderView.Interactive)
        self.t_capas.setColumnWidth(1, 210); self.t_capas.setColumnWidth(2, 150); self.t_capas.setMinimumHeight(180); self.t_capas.verticalHeader().setVisible(False)
        F.addRow(QLabel('Etiquetas y chinchetas (opcional):')); F.addRow(self.t_capas)
        self.pila.addWidget(pg)
        # Fotogrametría
        pf = QWidget(); F2 = QFormLayout(pf)
        self.f_carpeta = QgsFileWidget(); self.f_carpeta.setStorageMode(QgsFileWidget.GetDirectory); self.f_carpeta.fileChanged.connect(self._carpeta_cambio)
        self.l_resumen = QLabel('Elige la carpeta del proyecto procesado (DJI Terra, Pix4D, Metashape o WebODM).\nEl complemento encuentra solo la malla, las texturas, el sistema de coordenadas, la ortofoto y los reportes.')
        self.l_resumen.setWordWrap(True)
        F2.addRow('Carpeta del vuelo:', self.f_carpeta); F2.addRow(self.l_resumen)
        self.pila.addWidget(pf)
        # Mina subterránea
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setWidget(self._pagina_mina()); self.pila.addWidget(sc)
        return w

    def _insumo_cambio(self, *_):
        self.pila.setCurrentIndex(0 if self.r_gpkg.isChecked() else 1 if self.r_foto.isChecked() else 2)

    def _pagina_mina(self):
        from .nucleo import cad
        w = QWidget(); V = QVBoxLayout(w)
        fila = QHBoxLayout(); fila.addWidget(QLabel('Plano de labores (DWG o DXF):'))
        self.f_cad = QgsFileWidget(); self.f_cad.setFilter('Plano de labores (*.dwg *.dxf *.DWG *.DXF)'); fila.addWidget(self.f_cad, 1)
        self.b_leer = QPushButton('Leer el plano'); self.b_leer.clicked.connect(self._leer_cad); fila.addWidget(self.b_leer); V.addLayout(fila)
        self.l_cad = QLabel('Cada capa del plano es un tipo de labor (nivel, inclinado, cruzada, tambor…) y sus líneas son los ejes que levanta el '
                            'topógrafo. Los textos de cota sirven cuando los ejes están en 2D.')
        self.l_cad.setWordWrap(True); V.addWidget(self.l_cad)
        self.t_mina = QTableWidget(0, 8)
        self.t_mina.setHorizontalHeaderLabels(['Usar', 'Capa del plano', 'Contenido', 'Tipo de labor', 'Color', 'Ancho (m)', 'Alto (m)', 'Cota fija (m)'])
        h = self.t_mina.horizontalHeader(); h.setSectionResizeMode(QHeaderView.Interactive); h.setSectionResizeMode(CM['capa'], QHeaderView.Stretch)
        for c, a in ((CM['usar'], 46), (CM['elem'], 130), (CM['tipo'], 170), (CM['color'], 70), (CM['ancho'], 80), (CM['alto'], 80), (CM['cota'], 95)):
            self.t_mina.setColumnWidth(c, a)
        self.t_mina.verticalHeader().setVisible(False); self.t_mina.setMinimumHeight(220); V.addWidget(self.t_mina)
        fila = QHBoxLayout(); fila.addWidget(QLabel('Colores:'))
        self.c_colores = QComboBox(); self.c_colores.addItems(['Los del plano (como los dibujó el topógrafo)',
                                                              'Convención de la empresa (nivel y patio en amarillo, inclinado en gris…)'])
        self.c_colores.currentIndexChanged.connect(lambda *_: self._aplicar_colores()); fila.addWidget(self.c_colores, 1); V.addLayout(fila)
        nota = QLabel('La Resolución 40600 de 2015 recomienda diferenciar con colores los niveles de explotación (numeral 2.6, literal m), '
                      'pero no asigna un color a cada tipo de labor; por eso se puede usar el color del plano o la convención de la empresa.')
        nota.setWordWrap(True); nota.setStyleSheet('color:#56626b'); V.addWidget(nota)
        F = QFormLayout()
        self.c_eje = QComboBox(); self.c_eje.addItems(['En el piso de la labor', 'En el centro de la labor', 'En el techo de la labor'])
        self.w_crs = QgsProjectionSelectionWidget(); self.w_crs.setCrs(QgsProject.instance().crs())
        F.addRow('El eje levantado va:', self.c_eje); F.addRow('Sistema de coordenadas del plano:', self.w_crs)
        self.c_sup = QComboBox(); self.c_sup.addItems(['Sin superficie', 'Modelo de elevación (DEM), con ortofoto si hay', 'Vuelo con dron (carpeta procesada)'])
        self.c_dem_m = QgsMapLayerComboBox(); self.c_dem_m.setFilters(_filtro_raster()); self.c_dem_m.setAllowEmptyLayer(True)
        self.f_dem_m = QgsFileWidget(); self.f_dem_m.setFilter('Ráster (*.tif *.tiff *.vrt *.img *.asc)')
        self.c_orto_m = QgsMapLayerComboBox(); self.c_orto_m.setFilters(_filtro_raster()); self.c_orto_m.setAllowEmptyLayer(True)
        self.f_vuelo_m = QgsFileWidget(); self.f_vuelo_m.setStorageMode(QgsFileWidget.GetDirectory)
        F.addRow('Superficie del terreno:', self.c_sup); F.addRow('   DEM (capa):', self.c_dem_m); F.addRow('   …o DEM en archivo:', self.f_dem_m)
        F.addRow('   Ortofoto (opcional):', self.c_orto_m); F.addRow('   Carpeta del vuelo:', self.f_vuelo_m)
        self.c_sup.currentIndexChanged.connect(self._sup_cambio); self._sup_cambio(0)
        V.addLayout(F)
        gg = QGroupBox('Frentes de trabajo y metano medido (opcional)'); VG = QVBoxLayout(gg)
        self.t_gas = QTableWidget(0, 9)
        self.t_gas.setHorizontalHeaderLabels(['Mostrar', 'Frente', 'Este (m)', 'Norte (m)', 'Cota (m)', 'CH₄ (%)', 'Fecha', 'Velocidad del aire (m/s)', 'Caudal (m³/s)'])
        hg = self.t_gas.horizontalHeader(); hg.setSectionResizeMode(QHeaderView.Interactive); hg.setSectionResizeMode(CG['nombre'], QHeaderView.Stretch)
        for c, a in ((CG['ver'], 60), (CG['E'], 95), (CG['N'], 95), (CG['Z'], 70), (CG['ch4'], 70), (CG['fecha'], 90), (CG['u'], 150), (CG['Q'], 100)):
            self.t_gas.setColumnWidth(c, a)
        self.t_gas.verticalHeader().setVisible(False); self.t_gas.setMinimumHeight(170); VG.addWidget(self.t_gas)
        fb = QHBoxLayout()
        b1 = QPushButton('Volver a detectar frentes'); b1.clicked.connect(self._detectar_frentes); fb.addWidget(b1)
        b2 = QPushButton('Importar mediciones (CSV)…'); b2.clicked.connect(self._importar_csv); fb.addWidget(b2); fb.addStretch(1); VG.addLayout(fb)
        FG = QFormLayout()
        self.c_retorno = QComboBox()
        self.s_E = QDoubleSpinBox(); self.s_E.setRange(0.5, 150); self.s_E.setDecimals(1); self.s_E.setValue(2.0); self.s_E.setSuffix(' m²/s')
        self.s_u = QDoubleSpinBox(); self.s_u.setRange(0.05, 6); self.s_u.setDecimals(2); self.s_u.setSingleStep(0.05); self.s_u.setValue(0.3); self.s_u.setSuffix(' m/s')
        self.s_Qr = QDoubleSpinBox(); self.s_Qr.setRange(0, 500); self.s_Qr.setDecimals(2); self.s_Qr.setSpecialValueText('no medido'); self.s_Qr.setSuffix(' m³/s')
        FG.addRow('Bocamina por donde sale el aire:', self.c_retorno); FG.addRow('Caudal total de retorno:', self.s_Qr)
        FG.addRow('Velocidad del aire donde no se midió:', self.s_u); FG.addRow('Coeficiente de dispersión E:', self.s_E)
        VG.addLayout(FG)
        aviso = QLabel('Modelo ilustrativo para socializar el riesgo: el aire de cada frente se lleva por el camino más corto hasta la bocamina de '
                       'salida y, sin caudales medidos, sin diluirse (caso desfavorable). E ≈ 2 m²/s corresponde a galerías rectas (fórmula de '
                       'Taylor); en redes con curvas y fondos ciegos se han medido valores mayores. No reemplaza la medición con el detector ni '
                       'el estudio de ventilación.')
        aviso.setWordWrap(True); aviso.setStyleSheet('color:#7a1f1f'); VG.addWidget(aviso)
        V.addWidget(gg)
        self.k_carta = QCheckBox('Hacer también el plano tamaño carta con el QR (PDF), para llevar impreso a la visita'); self.k_carta.setChecked(True)
        V.addWidget(self.k_carta)
        return w

    def _sup_cambio(self, i):
        for wdg in (self.c_dem_m, self.f_dem_m, self.c_orto_m): wdg.setEnabled(i == 1)
        self.f_vuelo_m.setEnabled(i == 2)

    # ----- lectura del DWG/DXF -----
    def _asegurar_ezdxf(self):
        from .nucleo import dependencias as D
        falt = D.faltantes(mina=True)
        if not falt: return True
        if QMessageBox.question(self, 'Librerías', 'Para leer planos DWG o DXF hay que instalar: ' + ', '.join(falt) + '.\n¿Instalarlas ahora? (necesita internet)') != QMessageBox.Yes:
            return False
        return D.instalar(falt, self.escribir) and not D.faltantes(mina=True)

    def _leer_cad(self):
        ruta = self.f_cad.filePath()
        if not ruta or not os.path.exists(ruta): QMessageBox.warning(self, 'Falta', 'Elige el plano de labores (.dwg o .dxf).'); return
        if not self._asegurar_ezdxf(): return
        from .nucleo import cad, mina
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.datos_cad = mina.analizar(ruta, self.escribir)
        except cad.FaltaConversor:
            QApplication.restoreOverrideCursor(); self.datos_cad = None
            if os.name == 'nt':
                r = QMessageBox.question(self, 'Abrir un DWG', 'En este equipo no hay con qué abrir el DWG (ni ODA File Converter ni LibreDWG).\n\n'
                                         '¿Descargar LibreDWG (programa libre, licencia GPL-3, unos 13 MB) desde su página oficial en GitHub, '
                                         'dentro de la carpeta del complemento?\n\nSi prefiere no hacerlo, guarde el plano como DXF desde AutoCAD o Civil 3D.')
                if r == QMessageBox.Yes:
                    try:
                        QApplication.setOverrideCursor(Qt.WaitCursor); cad.descargar_libredwg(self.escribir)
                        self.datos_cad = mina.analizar(ruta, self.escribir)
                    except Exception as e:
                        QApplication.restoreOverrideCursor(); QMessageBox.warning(self, 'DWG', f'No se pudo convertir el DWG: {e}\n\nGuárdelo como DXF desde AutoCAD o Civil 3D.'); return
            else:
                QMessageBox.warning(self, 'Abrir un DWG', 'No encontré con qué abrir el DWG. Instale ODA File Converter o LibreDWG (dwg2dxf), '
                                                          'o guarde el plano como DXF desde AutoCAD o Civil 3D.')
                return
        except Exception as e:
            QApplication.restoreOverrideCursor(); self.escribir(traceback.format_exc()); QMessageBox.critical(self, 'Plano', str(e)); return
        finally:
            while QApplication.overrideCursor(): QApplication.restoreOverrideCursor()
        if not self.datos_cad: return
        self._llenar_tabla_mina(); self._aplicar_colores()
        D = self.datos_cad
        self.l_cad.setText(f"<b>{os.path.basename(ruta)}</b>: {len(D['lineas'])} líneas, {len(D['textos'])} textos y {len(D['capas'])} capas · "
                           + ('ejes con cota (3D).' if D['es_3d'] else 'ejes en 2D: la cota sale de los textos de cota o de la cota fija de la capa.')
                           + ' Revise el tipo de cada capa; las que no son labores (curvas de nivel, rótulo, cuadrícula) van sin marcar.')
        if not self.e_titulo.text(): self.e_titulo.setText(os.path.splitext(os.path.basename(ruta))[0].replace('_', ' '))
        self._detectar_frentes()

    def _llenar_tabla_mina(self):
        from .nucleo import cad
        filas = self.datos_cad['tabla']; self.t_mina.setRowCount(len(filas))
        for r, f in enumerate(filas):
            it = QTableWidgetItem(); it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled); it.setCheckState(Qt.Checked if f['usar'] else Qt.Unchecked)
            self.t_mina.setItem(r, CM['usar'], it)
            it = QTableWidgetItem(f['nombre']); it.setFlags(it.flags() & ~Qt.ItemIsEditable); it.setData(Qt.UserRole, f['color'])
            if not f['visible']: it.setToolTip('Capa apagada o congelada en el plano')
            self.t_mina.setItem(r, CM['capa'], it)
            partes = [f"{f['lineas']} líneas" if f['lineas'] else '', f"{f['textos']} textos" if f['textos'] else '', f"{f['puntos']} bloques" if f['puntos'] else '']
            it = QTableWidgetItem(' · '.join(p for p in partes if p) or '—'); it.setFlags(it.flags() & ~Qt.ItemIsEditable); self.t_mina.setItem(r, CM['elem'], it)
            ct = QComboBox()
            for k in cad.TIPOS: ct.addItem(cad.NOMBRES[k], k)
            ct.setCurrentIndex(cad.TIPOS.index(f['tipo'])); ct.currentIndexChanged.connect(lambda _i, fila=r: self._tipo_cambio(fila))
            self.t_mina.setCellWidget(r, CM['tipo'], ct)
            bc = QgsColorButton(); bc.setColor(QColor(f['color'])); self.t_mina.setCellWidget(r, CM['color'], bc)
            for col, val in ((CM['ancho'], f['ancho']), (CM['alto'], f['alto'])):
                s = QDoubleSpinBox(); s.setRange(0.3, 15); s.setDecimals(1); s.setSingleStep(0.1); s.setValue(val); self.t_mina.setCellWidget(r, col, s)
            e = QLineEdit(); e.setPlaceholderText('—'); e.setToolTip('Solo si toda la capa está a una misma cota y sus ejes no la traen'); self.t_mina.setCellWidget(r, CM['cota'], e)

    def _tipo_cambio(self, r):
        from .nucleo import cad
        tipo = self.t_mina.cellWidget(r, CM['tipo']).currentData()
        an, al = cad.SECCION.get(tipo, (2.0, 1.8))
        self.t_mina.cellWidget(r, CM['ancho']).setValue(an); self.t_mina.cellWidget(r, CM['alto']).setValue(al)
        self.t_mina.item(r, CM['usar']).setCheckState(Qt.Unchecked if tipo in ('ignorar', 'otra') else Qt.Checked)
        if self.c_colores.currentIndex() == 1: self._aplicar_colores()

    def _aplicar_colores(self):
        from .nucleo import cad
        for r in range(self.t_mina.rowCount()):
            tipo = self.t_mina.cellWidget(r, CM['tipo']).currentData()
            col = cad.CONVENCION.get(tipo) if self.c_colores.currentIndex() == 1 else None
            self.t_mina.cellWidget(r, CM['color']).setColor(QColor(col or self.t_mina.item(r, CM['capa']).data(Qt.UserRole)))

    def _tabla_mina(self):
        out = []
        for r in range(self.t_mina.rowCount()):
            out.append({'nombre': self.t_mina.item(r, CM['capa']).text(), 'usar': self.t_mina.item(r, CM['usar']).checkState() == Qt.Checked,
                        'tipo': self.t_mina.cellWidget(r, CM['tipo']).currentData(), 'color': self.t_mina.cellWidget(r, CM['color']).color().name(),
                        'ancho': self.t_mina.cellWidget(r, CM['ancho']).value(), 'alto': self.t_mina.cellWidget(r, CM['alto']).value(),
                        'cota': _num(self.t_mina.cellWidget(r, CM['cota']).text())})
        return out

    def _eje(self): return ('piso', 'centro', 'techo')[self.c_eje.currentIndex()]

    def _detectar_frentes(self):
        if not self.datos_cad: return
        from .nucleo import mina
        previo = self._frentes_cfg()
        try:
            M = mina.preparar(self.datos_cad, self._tabla_mina(), {'eje': self._eje()}, self.escribir)
        except Exception as e:
            self.escribir(f'No se pudieron detectar los frentes: {e}'); return
        self.mina_prev = M
        hoy = datetime.date.today().strftime('%d/%m/%Y')
        self.t_gas.setRowCount(len(M['frentes']))
        for r, f in enumerate(M['frentes']):
            p = min(previo, key=lambda x: (x['E'] - f['E']) ** 2 + (x['N'] - f['N']) ** 2, default=None)
            if p and ((p['E'] - f['E']) ** 2 + (p['N'] - f['N']) ** 2) ** 0.5 > 5: p = None
            it = QTableWidgetItem(); it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            it.setCheckState(Qt.Unchecked if p and p.get('mostrar') is False else Qt.Checked); self.t_gas.setItem(r, CG['ver'], it)
            self.t_gas.setItem(r, CG['nombre'], QTableWidgetItem(p['nombre'] if p and p.get('nombre') else f['nombre']))
            for col, v in ((CG['E'], f['E']), (CG['N'], f['N']), (CG['Z'], f['Z'])):
                it = QTableWidgetItem(f'{v:,.1f}'.replace(',', ' ')); it.setData(Qt.UserRole, v); it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                it.setTextAlignment(int(Qt.AlignRight | Qt.AlignVCenter)); self.t_gas.setItem(r, col, it)
            for col, k, defecto in ((CG['ch4'], 'ch4', ''), (CG['fecha'], 'fecha', hoy), (CG['u'], 'u', ''), (CG['Q'], 'Q', '')):
                v = p.get(k) if p else None
                self.t_gas.setItem(r, col, QTableWidgetItem('' if v in (None, '') else str(v).replace('.', ',') if k != 'fecha' else str(v)) if v not in (None, '') else QTableWidgetItem(defecto))
        actual = self.c_retorno.currentText(); self.c_retorno.clear()
        for b in M['bocaminas']: self.c_retorno.addItem(b['nombre'], (b['E'], b['N']))
        j = self.c_retorno.findText(actual)
        if j >= 0: self.c_retorno.setCurrentIndex(j)
        else:   # por defecto, la bocamina cuyo nombre sugiere ventilación o retorno
            for i in range(self.c_retorno.count()):
                if any(k in _llave(self.c_retorno.itemText(i)) for k in ('VENTIL', 'RETORNO', 'SALIDA', 'CHIMENEA')): self.c_retorno.setCurrentIndex(i); break
        self.escribir(f"Frentes listos para anotar el metano: {len(M['frentes'])}.")

    def _frentes_cfg(self):
        out = []
        for r in range(self.t_gas.rowCount()):
            g = lambda c: self.t_gas.item(r, c).text() if self.t_gas.item(r, c) else ''
            out.append({'E': self.t_gas.item(r, CG['E']).data(Qt.UserRole), 'N': self.t_gas.item(r, CG['N']).data(Qt.UserRole),
                        'mostrar': self.t_gas.item(r, CG['ver']).checkState() == Qt.Checked, 'nombre': g(CG['nombre']).strip(),
                        'ch4': _num(g(CG['ch4'])), 'fecha': g(CG['fecha']).strip() if _num(g(CG['ch4'])) is not None else '',
                        'u': _num(g(CG['u'])), 'Q': _num(g(CG['Q']))})
        return out

    def _importar_csv(self):
        """CSV con columnas frente (nombre como en la tabla, o F1, F2…), ch4, fecha, velocidad y caudal; separado por ; o ,"""
        import csv
        ruta, _ = QFileDialog.getOpenFileName(self, 'Mediciones de metano', '', 'CSV (*.csv *.txt)')
        if not ruta: return
        texto = open(ruta, encoding='utf-8-sig', errors='replace').read()
        try: dialecto = csv.Sniffer().sniff(texto.splitlines()[0], delimiters=';,\t')
        except Exception: dialecto = csv.excel
        filas = list(csv.DictReader(texto.splitlines(), dialect=dialecto))
        if not filas: return
        cab = {_llave(k): k for k in filas[0].keys() if k}
        busca = lambda *ops: next((cab[k] for k in cab if any(o in k for o in ops)), None)
        cf, cc, cd, cu, cq = busca('FRENTE', 'NOMBRE', 'ID'), busca('CH4', 'METANO'), busca('FECHA'), busca('VELOC', 'U'), busca('CAUDAL', 'Q')
        if not cf or not cc: QMessageBox.warning(self, 'CSV', 'El CSV necesita al menos las columnas «frente» y «ch4».'); return
        nombres = {_llave(self.t_gas.item(r, CG['nombre']).text()): r for r in range(self.t_gas.rowCount())}
        n = 0
        for f in filas:
            k = _llave(f.get(cf, '')); r = nombres.get(k)
            if r is None and k.startswith('F') and k[1:].isdigit() and int(k[1:]) <= self.t_gas.rowCount(): r = int(k[1:]) - 1
            if r is None: continue
            for col, c in ((CG['ch4'], cc), (CG['fecha'], cd), (CG['u'], cu), (CG['Q'], cq)):
                if c and (f.get(c) or '').strip(): self.t_gas.setItem(r, col, QTableWidgetItem(f[c].strip()))
            n += 1
        self.escribir(f'Mediciones importadas: {n} de {len(filas)} filas del CSV.')

    def _superficie(self):
        i = self.c_sup.currentIndex()
        if i == 1:
            dem = self.f_dem_m.filePath() or (self.c_dem_m.currentLayer().source() if self.c_dem_m.currentLayer() else None)
            if not dem: raise RuntimeError('Elige el modelo de elevación (DEM) de la superficie, o marca «Sin superficie».')
            orto = self.c_orto_m.currentLayer().source() if self.c_orto_m.currentLayer() else None
            return {'dem': dem, 'orto': orto}
        if i == 2:
            if not self.f_vuelo_m.filePath(): raise RuntimeError('Elige la carpeta del vuelo procesado, o marca «Sin superficie».')
            return {'carpeta': self.f_vuelo_m.filePath()}
        return None

    def _gpkg_cambio(self, ruta):
        from .nucleo import gpkg as G
        self.c_proy.clear()
        if ruta and os.path.exists(ruta):
            ps = G.proyectos_en(ruta)
            if not ps: QMessageBox.warning(self, 'Sin proyecto', 'No encontré un proyecto de QGIS para ese GeoPackage: ni guardado dentro de él ni un .qgz/.qgs en la misma carpeta que lo use.\nElige el .qgz directamente, o en QGIS: Proyecto → Guardar en → GeoPackage.')
            self.c_proy.addItems(ps)

    def _proy_cambio(self, nombre):
        from .nucleo import gpkg as G
        self.c_dis.clear(); self.c_dem.clear(); self.t_capas.setRowCount(0); self.proyecto = None
        if not nombre: return
        try: self.proyecto = G.abrir(self.f_gpkg.filePath(), nombre)
        except Exception as e: QMessageBox.warning(self, 'Error', str(e)); return
        self.c_dis.addItems(G.disenos(self.proyecto))
        for l in G.capas(self.proyecto, 'raster'):
            if l.bandCount() == 1: self.c_dem.addItem(l.name(), l.id())
        usados = {l.source().split('|')[0].lower() for l in G.capas(self.proyecto, 'raster')}
        for nombre, uri, tipo in G.rasters_en_gpkg(self.f_gpkg.filePath()):   # DEM guardado en el GeoPackage aunque no esté en el mapa
            if uri.lower() not in usados: self.c_dem.addItem(f'{nombre} (dentro del GeoPackage)', '__gpkg__' + uri + '|' + tipo)
        self.c_dem.addItem('Archivo aparte…', '__archivo__')

        def puntaje(j):   # el DEM se elige solo: nombre de elevación y datos de cotas (no un sombreado de 0 a 255)
            dato = self.c_dem.itemData(j)
            if dato == '__archivo__': return -1
            n = self.c_dem.itemText(j).lower(); p = 0
            if any(k in n for k in ('dem', 'elev', 'mde', 'mdt', 'dsm', 'srtm', 'alos', 'cota', 'altur')): p += 5
            if any(k in n for k in ('sombr', 'hillshade', 'pendiente', 'slope', 'aspect', 'textura', 'brillo', 'gris')): p -= 10
            if dato.startswith('__gpkg__'):
                if dato.rsplit('|', 1)[1] != 'Byte': p += 3
            else:
                try:
                    if self.proyecto.mapLayer(dato).dataProvider().dataType(1) not in (Qgis.DataType.Byte, Qgis.DataType.UnknownDataType): p += 3
                except Exception: pass
            return p
        if self.c_dem.count() > 1: self.c_dem.setCurrentIndex(max(range(self.c_dem.count()), key=puntaje))
        capas = sorted(G.capas(self.proyecto, 'vector'), key=lambda l: l.name().lower())
        self.t_capas.setRowCount(len(capas))
        for r, l in enumerate(capas):
            it = QTableWidgetItem(l.name()); it.setData(Qt.UserRole, l.id()); it.setFlags(it.flags() & ~Qt.ItemIsEditable)
            self.t_capas.setItem(r, 0, it)
            cu = QComboBox(); cu.addItems(USOS); self.t_capas.setCellWidget(r, 1, cu)
            cc = QComboBox(); campos = [f.name() for f in l.fields()]; cc.addItems(campos)
            for pref in ('nombre', 'name', 'NOMBRE', 'etiqueta', 'codigo'):
                if pref in campos: cc.setCurrentText(pref); break
            self.t_capas.setCellWidget(r, 2, cc)

    def _dis_cambio(self, nombre):
        from .nucleo import gpkg as G
        self.c_mapa.clear()
        if self.proyecto and nombre:
            ms = G.mapas(self.proyecto, nombre); self.c_mapa.addItems(ms)
            lay = self.proyecto.layoutManager().layoutByName(nombre)
            from qgis.core import QgsLayoutItemMap
            grande = max((i for i in lay.items() if isinstance(i, QgsLayoutItemMap)), key=lambda i: i.rect().width() * i.rect().height(), default=None)
            if grande: self.c_mapa.setCurrentText(grande.displayName())
            if not self.e_titulo.text(): self.e_titulo.setText(nombre.replace('_', ' '))

    def _carpeta_cambio(self, ruta):
        try:
            from .nucleo import fotogrametria as FG
            self.analisis = FG.analizar(ruta); self.l_resumen.setText(FG.resumen(self.analisis))
        except ImportError:
            self.l_resumen.setText('Falta una librería: pulsa «Generar» y el complemento la instala.')
        except Exception as e:
            self.l_resumen.setText(f'No se pudo analizar la carpeta: {e}')

    # ---------------- 2. Autor y empresa ----------------
    def _tab_autor(self):
        w = QWidget(); L = QVBoxLayout(w)
        fila = QHBoxLayout(); fila.addWidget(QLabel('Perfil:')); self.c_perfil = QComboBox(); fila.addWidget(self.c_perfil, 1)
        for t, f in (('Guardar', self._guardar_perfil), ('Guardar como nuevo…', self._nuevo_perfil), ('Eliminar', self._borrar_perfil)):
            b = QPushButton(t); b.clicked.connect(f); fila.addWidget(b)
        L.addLayout(fila); self.c_perfil.addItems([p['nombre_perfil'] for p in perfiles()]); self.c_perfil.currentIndexChanged.connect(self._cargar_perfil)
        ge = QGroupBox('Empresa (pie de la página)'); F = QFormLayout(ge)
        self.e_empresa = QLineEdit(); self.f_logo = QgsFileWidget(); self.f_logo.setFilter('Imagen (*.png *.jpg *.jpeg *.svg)')
        self.k_color_logo = QCheckBox('Tomar el color principal del logo'); self.k_color_logo.setChecked(True)
        self.b_color = QgsColorButton(); self.b_color.setColor(QColor('#014f7d')); self.k_color_logo.toggled.connect(lambda on: self.b_color.setEnabled(not on)); self.b_color.setEnabled(False)
        F.addRow('Nombre de la empresa:', self.e_empresa); F.addRow('Logo (opcional):', self.f_logo); F.addRow(self.k_color_logo); F.addRow('Color de la página:', self.b_color)
        L.addWidget(ge)
        ga = QGroupBox('Autor (recuadro «Elaboró»)'); V = QVBoxLayout(ga)
        self.k_elaboro = QCheckBox('Mostrar el recuadro «Elaboró»'); V.addWidget(self.k_elaboro)
        f2 = QFormLayout(); self.e_autor = QLineEdit(); f2.addRow('Nombre:', self.e_autor); V.addLayout(f2)
        self.t_tit = QTableWidget(0, 2); self.t_tit.setHorizontalHeaderLabels(['Título', 'Institución'])
        self.t_tit.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); V.addWidget(self.t_tit)
        fb = QHBoxLayout()
        for t, f in (('Agregar', lambda: self.t_tit.insertRow(self.t_tit.rowCount())), ('Quitar', lambda: self.t_tit.removeRow(self.t_tit.currentRow())),
                     ('Subir', lambda: self._mover(-1)), ('Bajar', lambda: self._mover(1))):
            b = QPushButton(t); b.clicked.connect(f); fb.addWidget(b)
        fb.addStretch(1); V.addLayout(fb); L.addWidget(ga)
        return w

    def _mover(self, d):
        r = self.t_tit.currentRow(); s = r + d
        if r < 0 or s < 0 or s >= self.t_tit.rowCount(): return
        for c in range(2):
            a, b = self.t_tit.takeItem(r, c), self.t_tit.takeItem(s, c); self.t_tit.setItem(r, c, b); self.t_tit.setItem(s, c, a)
        self.t_tit.setCurrentCell(s, 0)

    def _perfil_actual(self):
        tit = []
        for r in range(self.t_tit.rowCount()):
            a, b = self.t_tit.item(r, 0), self.t_tit.item(r, 1)
            if a and a.text().strip(): tit.append([a.text().strip(), b.text().strip() if b else ''])
        return {'nombre_perfil': self.c_perfil.currentText(), 'empresa': self.e_empresa.text(), 'logo': self.f_logo.filePath(),
                'color': '' if self.k_color_logo.isChecked() else self.b_color.color().name(), 'mostrar_elaboro': self.k_elaboro.isChecked(),
                'autor': self.e_autor.text(), 'titulos': tit}

    def _cargar_perfil(self, i):
        ps = perfiles()
        if i < 0 or i >= len(ps): return
        p = ps[i]; self.e_empresa.setText(p.get('empresa', '')); self.f_logo.setFilePath(p.get('logo', ''))
        self.k_color_logo.setChecked(not p.get('color')); self.b_color.setColor(QColor(p.get('color') or '#014f7d'))
        self.k_elaboro.setChecked(p.get('mostrar_elaboro', True)); self.e_autor.setText(p.get('autor', ''))
        self.t_tit.setRowCount(0)
        for t, ins in p.get('titulos', []):
            r = self.t_tit.rowCount(); self.t_tit.insertRow(r); self.t_tit.setItem(r, 0, QTableWidgetItem(t)); self.t_tit.setItem(r, 1, QTableWidgetItem(ins))

    def _guardar_perfil(self):
        ps = perfiles(); i = self.c_perfil.currentIndex(); ps[i] = self._perfil_actual(); guardar_perfiles(ps)
        self.log.appendPlainText(f'Perfil «{ps[i]["nombre_perfil"]}» guardado.')

    def _nuevo_perfil(self):
        n, ok = QInputDialog.getText(self, 'Nuevo perfil', 'Nombre del perfil (p. ej. «Osney – independiente»):')
        if not ok or not n.strip(): return
        ps = perfiles(); p = self._perfil_actual(); p['nombre_perfil'] = n.strip(); ps.append(p); guardar_perfiles(ps)
        self.c_perfil.blockSignals(True); self.c_perfil.addItem(n.strip()); self.c_perfil.setCurrentIndex(self.c_perfil.count() - 1); self.c_perfil.blockSignals(False)

    def _borrar_perfil(self):
        ps = perfiles()
        if len(ps) <= 1: return
        i = self.c_perfil.currentIndex(); ps.pop(i); guardar_perfiles(ps); self.c_perfil.removeItem(i)

    # ---------------- 3. Textos ----------------
    def _tab_plano(self):
        w = QWidget(); F = QFormLayout(w)
        self.e_titulo = QLineEdit(); self.e_subtitulo = QLineEdit()
        F.addRow('Título de la página:', self.e_titulo); F.addRow('Subtítulo:', self.e_subtitulo)
        F.addRow(QLabel('La ficha técnica (escala, exageración, sistema, tamaño; en fotogrametría fotos, RTK y GSD; en una mina, cotas,\n'
                        'superficie y plano fuente) se llena sola con los valores calculados. Se puede editar después en config.js.'))
        return w

    # ---------------- 4. Publicar ----------------
    def _tab_publicar(self):
        w = QWidget(); L = QVBoxLayout(w)
        self.r_zip = QRadioButton('Solo carpeta y .zip (subirlo yo a donde quiera)'); self.r_gh = QRadioButton('GitHub Pages (crea el repositorio, sube y publica)')
        self.r_zip.setChecked(True); L.addWidget(self.r_zip); L.addWidget(self.r_gh)
        F = QFormLayout(); self.f_salida = QgsFileWidget(); self.f_salida.setStorageMode(QgsFileWidget.GetDirectory)
        self.e_url = QLineEdit(); self.e_url.setPlaceholderText('https://… (opcional: si ya sabes dónde va a quedar, se genera el QR)')
        self.e_repo = QLineEdit(); self.e_repo.setPlaceholderText('nombre-del-repositorio'); self.e_repo.setEnabled(False)
        self.r_gh.toggled.connect(self.e_repo.setEnabled); self.r_gh.toggled.connect(lambda on: self.e_url.setEnabled(not on))
        F.addRow('Carpeta de salida:', self.f_salida); F.addRow('Dirección de la página (para el QR):', self.e_url); F.addRow('Repositorio de GitHub:', self.e_repo)
        L.addLayout(F)
        self.b_conectar = QPushButton('Conectar con GitHub…'); self.b_conectar.clicked.connect(self._conectar_github); L.addWidget(self.b_conectar)
        gf = QGroupBox('Qué ofrece la página (la maqueta 3D, el plano 2D y la realidad aumentada siempre están)'); V = QVBoxLayout(gf)
        guard = json.loads(QgsSettings().value('maqueta3dweb/funciones', '{}') or '{}')
        self.k_fx = {}
        for clave, texto in (('gps', 'Botón «Mi ubicación» (GPS: la persona se ve en el plano y en la maqueta)'),
                             ('recorrido', 'Guardar el recorrido y descargarlo en GPX'),
                             ('sin_internet', 'Guardar para usar sin internet'),
                             ('instalar', 'Instalar como aplicación')):
            k = QCheckBox(texto); k.setChecked(bool(guard.get(clave, True))); V.addWidget(k); self.k_fx[clave] = k
        self.k_fx['gps'].toggled.connect(self.k_fx['recorrido'].setEnabled); self.k_fx['recorrido'].setEnabled(self.k_fx['gps'].isChecked())
        b = QPushButton('Solo mostrar el resultado y ubicar a la persona'); b.setFlat(True); b.setStyleSheet('text-align:left;color:#0b5394;text-decoration:underline')
        b.clicked.connect(lambda: [self.k_fx[c].setChecked(c == 'gps') for c in self.k_fx]); V.addWidget(b)
        L.addWidget(gf)
        L.addStretch(1)
        return w

    def funciones(self):
        f = {c: k.isChecked() for c, k in self.k_fx.items()}
        if not f['gps']: f['recorrido'] = False
        QgsSettings().setValue('maqueta3dweb/funciones', json.dumps(f))
        return f

    def _conectar_github(self):
        try:
            from .nucleo import github as GH
            login = GH.conectar(self)
            if login: self.b_conectar.setText(f'Conectado con GitHub como «{login}» (cambiar…)')
        except Exception as e:
            QMessageBox.warning(self, 'GitHub', str(e))

    # ---------------- Generar ----------------
    def escribir(self, t):
        self.log.appendPlainText(t); QApplication.processEvents()

    def generar(self):
        from .nucleo import dependencias as D
        es_mina = self.r_mina.isChecked()
        falt = D.faltantes(mina=es_mina)
        if falt:
            if QMessageBox.question(self, 'Librerías', 'La primera vez hay que instalar: ' + ', '.join(falt) + '.\n¿Instalarlas ahora? (necesita internet)') != QMessageBox.Yes: return
            if not D.instalar(falt, self.escribir) or D.faltantes(mina=es_mina):
                QMessageBox.critical(self, 'Librerías', 'No se pudieron instalar. Revisa el registro de abajo.'); return
            if D.faltantes(True): D.instalar(['usd-core'], self.escribir)   # opcional, para iPhone
        salida = self.f_salida.filePath()
        if not salida: QMessageBox.warning(self, 'Falta', 'Elige la carpeta de salida (pestaña 4).'); return
        if es_mina and self.r_gh.isChecked():
            r = QMessageBox.warning(self, 'Plano de una mina en internet',
                                    'GitHub Pages deja la página a la vista de cualquiera que tenga el enlace o la encuentre.\n\n'
                                    '¿La empresa autorizó publicar el plano de esta mina? Si no, use «Solo carpeta y .zip» y alójela en un '
                                    'servidor propio o en la red interna.', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if r != QMessageBox.Yes: return
        p = self._perfil_actual()
        comunes = dict(titulo=self.e_titulo.text(), subtitulo=self.e_subtitulo.text(), salida=salida, url=self.e_url.text().strip() if self.r_zip.isChecked() else '',
                       elaboro={'nombre': p['autor'] if p['mostrar_elaboro'] else '', 'titulos': p['titulos']},
                       pie=p['empresa'], logo=p['logo'] or None, color=p['color'] or None, funciones=self.funciones())
        self.b_gen.setEnabled(False); QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if self.r_gpkg.isChecked():
                from .nucleo import gpkg as G
                if not self.proyecto: raise RuntimeError('Elige el GeoPackage y el proyecto (pestaña 1).')
                cd = self.c_dem.currentData()
                dem = self.f_dem.filePath() if cd == '__archivo__' else cd[8:].rsplit('|', 1)[0] if cd.startswith('__gpkg__') else self.proyecto.mapLayer(cd)
                if not dem: raise RuntimeError('Elige el modelo de elevación (DEM) en la pestaña 1.')
                et, ch = [], []
                colores = ['#c62828', '#6a1b9a', '#e65100', '#2e7d32', '#00838f', '#f2b705']
                for r in range(self.t_capas.rowCount()):
                    uso = self.t_capas.cellWidget(r, 1).currentIndex()
                    if uso == 0: continue
                    capa = self.proyecto.mapLayer(self.t_capas.item(r, 0).data(Qt.UserRole)); campo = self.t_capas.cellWidget(r, 2).currentText()
                    if uso == 1: et.append((capa, campo, capa.name(), colores[len(et) % len(colores)]))
                    else: ch.append((capa, campo, 0 if uso == 2 else 1))
                res = G.procesar(dict(comunes, gpkg=self.f_gpkg.filePath(), proyecto=self.c_proy.currentText(), diseno=self.c_dis.currentText(),
                                      mapa=self.c_mapa.currentText(), dem=dem, ve=self.s_ve.value(), etiquetas_pagina=et, chinchetas=ch), self.escribir)
            elif self.r_foto.isChecked():
                from .nucleo import fotogrametria as FG
                res = FG.procesar(dict(comunes, carpeta=self.f_carpeta.filePath()), self.escribir)
            else:
                from .nucleo import mina as MN
                if not self.datos_cad: raise RuntimeError('Lee primero el plano de labores (pestaña 1, botón «Leer el plano»).')
                crs = self.w_crs.crs(); ok = crs.isValid()
                res = MN.procesar(dict(comunes, plano=self.f_cad.filePath(), datos=self.datos_cad, tabla=self._tabla_mina(), eje=self._eje(),
                                       crs_wkt=crs.toWkt() if ok else None, crs_nombre=crs.userFriendlyIdentifier() if ok else '',
                                       proyeccion=crs if ok else None, superficie=self._superficie(), frentes_cfg=self._frentes_cfg(),
                                       metano={'E': self.s_E.value(), 'u': self.s_u.value(), 'retorno': self.c_retorno.currentData(),
                                               'Q_retorno': self.s_Qr.value() or None},
                                       plano_carta=self.k_carta.isChecked()), self.escribir)
            if self.r_gh.isChecked():
                from .nucleo import github as GH
                url = GH.publicar(self, res['sitio'], self.e_repo.text().strip(), self.escribir)
                res['url'] = url
            self.escribir('LISTO.'); QMessageBox.information(self, 'Listo', f'Página generada en:\n{res["sitio"]}' + (f'\n\nPublicada en:\n{res["url"]}' if res.get('url') else ''))
        except Exception as e:
            self.escribir(traceback.format_exc()); QMessageBox.critical(self, 'Error', str(e))
        finally:
            QApplication.restoreOverrideCursor(); self.b_gen.setEnabled(True)
