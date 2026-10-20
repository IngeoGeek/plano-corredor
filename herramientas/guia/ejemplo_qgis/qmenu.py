import sys; sys.path.insert(0, '/tmp/claude-0/-home-claude/502107b1-9fb8-5890-8c10-e38c9a55e00b/scratchpad/gm')
from qcap_base import *
from qgis.PyQt.QtWidgets import QToolButton
import processing
@paso(4000)
def p0():
    d = processing.createAlgorithmDialog('qgis:tininterpolation', {}); d.show()
    out = []
    for b in d.findChildren(QToolButton):
        if b.objectName() == 'mCondensedToolButton' and b.menu():
            m = b.menu(); m.aboutToShow.emit()
            def walk(mm, p=''):
                for a in mm.actions():
                    out.append(p + a.text())
                    if a.menu(): a.menu().aboutToShow.emit(); walk(a.menu(), p + '  ')
            walk(m)
    open(OUT + 'menu.txt', 'w').write('\n'.join(out))
arrancar()
