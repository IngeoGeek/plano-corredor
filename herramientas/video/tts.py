"""Narración con Kokoro (voz em_alex). Uso: python3 tts.py CARPETA_CAPITULO  (lee guion.py, escribe audio/<id>.wav y duraciones.json)"""
import sys, os, json, importlib.util, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
C = sys.argv[1]; M = '/tmp/claude-0/-home-claude/502107b1-9fb8-5890-8c10-e38c9a55e00b/scratchpad/kokoro'
spec = importlib.util.spec_from_file_location('g', C + '/guion.py'); g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
k = Kokoro(M + '/kokoro-v1.0.onnx', M + '/voices-v1.0.bin'); os.makedirs(C + '/audio', exist_ok=True)
solo = sys.argv[2:]; dur = json.load(open(C + '/duraciones.json')) if solo and os.path.exists(C + '/duraciones.json') else {}
for sid, sub, voz in g.SEG:
    if solo and sid not in solo: continue
    a, sr = k.create(voz or sub, voice='em_alex', speed=1.0, lang='es')
    a = np.concatenate([np.zeros(int(0.08 * sr)), a, np.zeros(int(0.15 * sr))]).astype(np.float32)
    sf.write(f'{C}/audio/{sid}.wav', a, sr); dur[sid] = round(len(a) / sr, 3); print(sid, dur[sid])
json.dump(dur, open(C + '/duraciones.json', 'w'), indent=1); print('total', round(sum(dur.values()), 1), 's')
