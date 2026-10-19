import sys, glob, os, numpy as np, soundfile as sf, sherpa_onnx
from scipy.signal import resample_poly
A = sys.argv[1]; C = sys.argv[2]
r = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=A + '/small-encoder.int8.onnx', decoder=A + '/small-decoder.int8.onnx', tokens=A + '/small-tokens.txt', language='es', task='transcribe', num_threads=2)
for f in sorted(glob.glob(C + '/audio/*.wav')) if len(sys.argv) < 4 else [C + '/audio/' + x + '.wav' for x in sys.argv[3:]]:
    a, sr = sf.read(f, dtype='float32'); a = resample_poly(a, 16000, sr).astype(np.float32)
    s = r.create_stream(); s.accept_waveform(16000, a); r.decode_stream(s); print(os.path.basename(f)[:-4], '|', s.result.text.strip())
