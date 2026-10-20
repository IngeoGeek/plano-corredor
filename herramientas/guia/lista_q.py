import json
def dock(n, arriba=120, abajo=160):
    ms = [[round(v * 1.0425) for v in m[:4]] for m in M[n]]
    y0 = max(0, min(m[1] for m in ms) - arriba); y1 = min(1043, max(m[1] + m[3] for m in ms) + abajo)
    return anotar(n, [1160, y0, 508, y1 - y0])
print(anotar('q01_proyecto', [668, 543, 1000, 500]))
print(anotar('q02_src', None, pad=40))
print(dock('q03_extension', 200, 60)); print(dock('q04_posicion', 120, 80)); print(dock('q05_pagina', 120, 120))
print(dock('q11b_cuadricula', 160, 160)); print(dock('q11c_ajustar', 100, 60))
print(anotar('q06_tin', 'todo')); print(anotar('q07_combar90', [0, 0, 1022, 400])); print(anotar('q08_combar30', 'todo'))
print(anotar('q10_traducir', 'todo')); print(anotar('q13_punto_superficie', [0, 0, 1022, 300])); print(anotar('q12_opciones', 'todo'))
print(anotar('q09_minmax', [0, 0, 850, 300])); print(anotar('q14_csv', [0, 0, 792, 640])); print(anotar('q12_exportar_boton', [0, 0, 760, 110]))
print(anotar('q11d_textura_lista', [0, 0, 1668, 1043], escala=0.6))
