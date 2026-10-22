"""Audition spécialisée MSA vocalisée. Dépendance nipponjo/tts_arabic épinglée dans le notebook."""
from pathlib import Path
import hashlib
import json
import re
import time

SOURCE_REVISION = "eae130c8b94ebf88d3fa727db63c740859106327"
SENTENCES = [
    "مَرْحَبًا بِكُمْ فِي وَرْشَتِنَا.",
    "عَلِمَ الطَّالِبُ. عُلِمَ الْخَبَرُ.",
    "دَرَسَ الطَّالِبُ. دَرَّسَ الْمُعَلِّمُ.",
    "هَذَا قَلَمٌ. كَتَبْتُ بِقَلَمٍ.",
]


def verify_phonemizer():
    from tts_arabic.text import arabic_to_tokens
    pairs = [("عَلِمَ", "عُلِمَ"), ("دَرَسَ", "دَرَّسَ"), ("قَلَمٌ", "قَلَمٍ")]
    evidence = []
    for left, right in pairs:
        a, b = arabic_to_tokens(left), arabic_to_tokens(right)
        if a == b:
            raise RuntimeError("Les signes ne sont pas distingués : " + left + " / " + right)
        evidence.append({"left": left, "right": right, "left_tokens": a, "right_tokens": b})
    return evidence


def generate(text, directory):
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 500:
        raise ValueError("Un texte de 1 à 500 caractères est nécessaire pour cet essai.")
    if not re.search(r"[\u064b-\u0652]", text):
        raise ValueError("Cet essai attend un texte arabe vocalisé, à vérifier avant synthèse.")
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / "essai-arabe.wav"
    if output.exists():
        raise FileExistsError("Changez de dossier pour conserver l'ancien essai.")
    from tts_arabic import tts
    import tts_arabic
    import numpy as np
    import soundfile as sf

    evidence = verify_phonemizer()
    started = time.perf_counter()
    samples = tts(text, speaker=0, pace=1.0, denoise=0.005, volume=0.9,
                  play=False, vowelizer=None, cuda=None,
                  model_id="fastpitch", vocoder_id="hifigan")
    elapsed = time.perf_counter() - started
    samples = np.asarray(samples)
    if not samples.size or not np.isfinite(samples).all() or not np.max(np.abs(samples)):
        raise RuntimeError("Le moteur n'a pas produit d'audio valide.")
    sf.write(str(output), samples, 22050, subtype="PCM_16")
    model_dir = Path(tts_arabic.__file__).parent / "data"
    hashes = {}
    for name in ["fp_ms.onnx", "hifigan.onnx", "denoiser.onnx"]:
        with (model_dir / name).open("rb") as stream:
            hashes[name] = hashlib.file_digest(stream, "sha256").hexdigest()
    report = {
        "source": "https://github.com/nipponjo/tts_arabic", "source_revision": SOURCE_REVISION,
        "model": "fastpitch", "vocoder": "hifigan", "speaker": 0,
        "language": "ar-MSA", "device": "CPU", "sample_rate": 22050,
        "text": text, "automatic_vowelizer": None, "pace": 1.0, "denoise": 0.005,
        "total_sec_including_first_download": round(elapsed, 3), "model_sha256_observed": hashes,
        "phonemizer_checks": evidence,
        "validation": "Signes distingués dans les tokens ; prononciation et naturel à contrôler à l'écoute.",
    }
    output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return output
