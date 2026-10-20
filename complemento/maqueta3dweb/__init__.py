# -*- coding: utf-8 -*-
def classFactory(iface):
    from .plugin import Maqueta3DWeb
    return Maqueta3DWeb(iface)
