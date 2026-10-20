# -*- coding: utf-8 -*-
"""Ventana del complemento Maqueta 3D Web."""
import os, json, traceback
from qgis.core import QgsSettings, QgsRasterLayer, Qgis
from qgis.gui import QgsFileWidget, QgsColorButton
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget, QWidget, QRadioButton, QButtonGroup,
                                 QStackedWidget, QComboBox, QDoubleSpinBox, QLineEdit, QTableWidget, QTableWidgetItem, QPushButton,
                                 QLabel, QPlainTextEdit, QCheckBox, QMessageBox, QHeaderView, QApplication, QInputDialog, QGroupBox)

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


def perfiles():
    try: lista = json.loads(QgsSettings().value(CLAVE, '[]'))
    except Exception: lista = []
    return lista or [PERFIL_INICIAL]


def guardar_perfiles(lista): QgsSettings().setValue(CLAVE, json.dumps(lista, ensure_ascii=False))


class Dialogo(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent); self.iface = iface; self.proyecto = None
        self.setWindowTitle('Maqueta 3D Web · plano o vuelo a página con RA y QR'); self.resize(860, 760)
        L = QVBoxLayout(self); tabs = QTabWidget(); L.addWidget(tabs)
        tabs.addTab(self._tab_insumo(), '1 · Insumo'); tabs.addTab(self._tab_autor(), '2 · Autor y empresa')
        tabs.addTab(self._tab_plano(), '3 · Textos del plano'); tabs.addTab(self._tab_publicar(), '4 · Publicar')
        self.log = QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumHeight(170); L.addWidget(self.log)
        fila = QHBoxLayout(); fila.addStretch(1)
        self.b_gen = QPushButton('Generar'); self.b_gen.setDefault(True); self.b_gen.clicked.connect(self.generar)
        b_cer = QPushButton('Cerrar'); b_cer.clicked.connect(self.close); fila.addWidget(self.b_gen); fila.addWidget(b_cer); L.addLayout(fila)
        self._cargar_perfil(0)

    # ---------------- 1. Insumo ----------------
    def _tab_insumo(self):
        w = QWidget(); L = QVBoxLayout(w)
        fila = QHBoxLayout(); fila.addWidget(QLabel('<b>Tipo de insumo:</b>'))
        self.r_gpkg = QRadioButton('GeoPackage (plano de QGIS + DEM)'); self.r_foto = QRadioButton('Fotogrametría (carpeta del vuelo procesado)')
        self.r_gpkg.setChecked(True); g = QButtonGroup(w); g.addButton(self.r_gpkg); g.addButton(self.r_foto)
        fila.addWidget(self.r_gpkg); fila.addWidget(self.r_foto); fila.addStretch(1); L.addLayout(fila)
        self.pila = QStackedWidget(); L.addWidget(self.pila)
        self.r_gpkg.toggled.connect(lambda on: self.pila.setCurrentIndex(0 if on else 1))
        # GeoPackage
        pg = QWidget(); F = QFormLayout(pg)
        self.f_gpkg = QgsFileWidget(); self.f_gpkg.setFilter('GeoPackage (*.gpkg)'); self.f_gpkg.fileChanged.connect(self._gpkg_cambio)
        self.c_proy = QComboBox(); self.c_proy.currentTextChanged.connect(self._proy_cambio)
        self.c_dis = QComboBox(); self.c_dis.currentTextChanged.connect(self._dis_cambio)
        self.c_mapa = QComboBox(); self.c_dem = QComboBox(); self.f_dem = QgsFileWidget(); self.f_dem.setFilter('Ráster (*.tif *.tiff *.vrt *.img *.asc)')
        self.f_dem.setEnabled(False); self.c_dem.currentIndexChanged.connect(lambda i: self.f_dem.setEnabled(self.c_dem.currentData() == '__archivo__'))
        self.s_ve = QDoubleSpinBox(); self.s_ve.setRange(1, 10); self.s_ve.setSingleStep(0.5); self.s_ve.setValue(2.5)
        F.addRow('GeoPackage con el proyecto:', self.f_gpkg); F.addRow('Proyecto guardado:', self.c_proy)
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
        return w

    def _gpkg_cambio(self, ruta):
        from .nucleo import gpkg as G
        self.c_proy.clear()
        if ruta and os.path.exists(ruta):
            ps = G.proyectos_en(ruta)
            if not ps: QMessageBox.warning(self, 'Sin proyecto', 'Ese GeoPackage no tiene ningún proyecto de QGIS guardado.\nEn QGIS: Proyecto → Guardar en → GeoPackage.')
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
        self.c_dem.addItem('Archivo aparte…', '__archivo__')
        for i, nm in enumerate(['dem', 'elev', 'mde', 'mdt', 'dsm']):
            k = next((j for j in range(self.c_dem.count()) if nm in self.c_dem.itemText(j).lower()), -1)
            if k >= 0: self.c_dem.setCurrentIndex(k); break
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
        F.addRow(QLabel('La ficha técnica (escala, exageración, sistema, tamaño; en fotogrametría fotos, RTK y GSD)\nse llena sola con los valores calculados. Se puede editar después en config.js.'))
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
        L.addStretch(1)
        return w

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
        falt = D.faltantes()
        if falt:
            if QMessageBox.question(self, 'Librerías', 'La primera vez hay que instalar: ' + ', '.join(falt) + '.\n¿Instalarlas ahora? (necesita internet)') != QMessageBox.Yes: return
            if not D.instalar(falt, self.escribir) or D.faltantes():
                QMessageBox.critical(self, 'Librerías', 'No se pudieron instalar. Revisa el registro de abajo.'); return
            if D.faltantes(True): D.instalar(['usd-core'], self.escribir)   # opcional, para iPhone
        salida = self.f_salida.filePath()
        if not salida: QMessageBox.warning(self, 'Falta', 'Elige la carpeta de salida (pestaña 4).'); return
        p = self._perfil_actual()
        comunes = dict(titulo=self.e_titulo.text(), subtitulo=self.e_subtitulo.text(), salida=salida, url=self.e_url.text().strip() if self.r_zip.isChecked() else '',
                       elaboro={'nombre': p['autor'] if p['mostrar_elaboro'] else '', 'titulos': p['titulos']},
                       pie=p['empresa'], logo=p['logo'] or None, color=p['color'] or None)
        self.b_gen.setEnabled(False); QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if self.r_gpkg.isChecked():
                from .nucleo import gpkg as G
                if not self.proyecto: raise RuntimeError('Elige el GeoPackage y el proyecto (pestaña 1).')
                dem = self.f_dem.filePath() if self.c_dem.currentData() == '__archivo__' else self.proyecto.mapLayer(self.c_dem.currentData())
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
            else:
                from .nucleo import fotogrametria as FG
                res = FG.procesar(dict(comunes, carpeta=self.f_carpeta.filePath()), self.escribir)
            if self.r_gh.isChecked():
                from .nucleo import github as GH
                url = GH.publicar(self, res['sitio'], self.e_repo.text().strip(), self.escribir)
                res['url'] = url
            self.escribir('LISTO.'); QMessageBox.information(self, 'Listo', f'Página generada en:\n{res["sitio"]}' + (f'\n\nPublicada en:\n{res["url"]}' if res.get('url') else ''))
        except Exception as e:
            self.escribir(traceback.format_exc()); QMessageBox.critical(self, 'Error', str(e))
        finally:
            QApplication.restoreOverrideCursor(); self.b_gen.setEnabled(True)
