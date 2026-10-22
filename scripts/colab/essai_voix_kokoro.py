"""Audition française indépendante ; aucun remplacement du worker MMS ni de ses résultats."""
from pathlib import Path
import hashlib
import json
import time
import urllib.request

MODEL_SOURCE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/"
FILES = {
    "kokoro-v1.0.onnx": "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a",
    "voices-v1.0.bin": "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def generate(text, directory="essai-kokoro-fr"):
    if not isinstance(text, str) or not text.strip() or len(text) > 500:
        raise ValueError("Pour comparer : un texte français de 1 à 500 caractères.")
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / "essai-kokoro-fr.wav"
    if output.exists():
        raise FileExistsError("Essai déjà présent. Changez le dossier pour conserver la comparaison.")
    for name, checksum in FILES.items():
        target = folder / name
        if not target.exists():
            temporary = folder / (name + ".part")
            try:
                with urllib.request.urlopen(MODEL_SOURCE + name, timeout=90) as source, temporary.open("wb") as destination:
                    while chunk := source.read(1024 * 1024):
                        destination.write(chunk)
                if digest(temporary) != checksum:
                    raise ValueError("Empreinte incorrecte : " + name)
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
        if digest(target) != checksum:
            raise ValueError("Fichier modifié : " + name + ". Arrêtez cet essai.")

    import numpy as np
    import onnxruntime as ort
    import soundfile as sf
    from kokoro_onnx import Kokoro

    started = time.perf_counter()
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    session = ort.InferenceSession(str(folder / "kokoro-v1.0.onnx"), sess_options=options, providers=["CPUExecutionProvider"])
    engine = Kokoro.from_session(session, str(folder / "voices-v1.0.bin"))
    loaded = time.perf_counter()
    samples, rate = engine.create(text.strip(), voice="ff_siwis", lang="fr-fr", speed=1.0)
    finished = time.perf_counter()
    if not len(samples) or not np.isfinite(samples).all() or np.max(np.abs(samples)) == 0:
        raise RuntimeError("Audio vide ou invalide.")
    sf.write(str(output), samples, rate, subtype="PCM_16")
    report = {
        "model": "hexgrad/Kokoro-82M", "conversion": MODEL_SOURCE,
        "sha256": FILES, "voice": "ff_siwis", "language": "fr-fr",
        "engine": "kokoro-onnx 0.6.1", "device": "CPU", "speed": 1.0,
        "text": text.strip(), "sample_rate": rate,
        "load_sec": round(loaded - started, 3), "generation_sec": round(finished - loaded, 3),
        "audio_sha256": digest(output), "quality": "À évaluer à l'écoute ; aucune équivalence avec une voix humaine garantie.",
    }
    output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


if __name__ == "__main__":
    print(generate("Bonjour, bienvenue dans notre atelier."))
