"""Audition arabe Chatterbox Multilingual, voix fournie par le modèle, sans clonage."""
from pathlib import Path
import argparse
import hashlib
import json
import random
import re
import time

MODEL_ID = "ResembleAI/chatterbox"
MODEL_FILES = [
    "ve.pt", "t3_mtl23ls_v2.safetensors", "s3gen.pt",
    "grapheme_mtl_merged_expanded_v1.json", "conds.pt", "Cangjie5_TC.json",
]
DEFAULT_TEXT = "مَرْحَبًا بِكُمْ فِي وَرْشَتِنَا. عَلِمَ الطَّالِبُ. عُلِمَ الْخَبَرُ. دَرَسَ الطَّالِبُ. دَرَّسَ الْمُعَلِّمُ."


def validate_text(text):
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 500:
        raise ValueError("Essai : un texte de 1 à 500 caractères.")
    if not re.search(r"[\u0621-\u064a]", text) or not re.search(r"[\u064b-\u0652]", text):
        raise ValueError("Utilisez un texte arabe vocalisé pour comparer la diction.")
    return text.strip()


def phoneme_checks(tokenizer):
    """Vérifie la distinction dans les tokens, sans prétendre valider la diction."""
    checks = []
    for left, right in [("عَلِمَ", "عُلِمَ"), ("دَرَسَ", "دَرَّسَ"), ("قَلَمٌ", "قَلَمٍ")]:
        a = tokenizer.text_to_tokens(left, language_id="ar").tolist()
        b = tokenizer.text_to_tokens(right, language_id="ar").tolist()
        checks.append({"left": left, "right": right, "distinct_tokens": a != b})
    return checks


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def generate(text, directory, seed=42, device="cuda"):
    text = validate_text(text)
    if device not in ("cuda", "cpu"):
        raise ValueError("Périphérique non pris en charge.")
    import numpy as np
    import torch
    import soundfile as sf
    import perth
    if not callable(perth.PerthImplicitWatermarker):
        raise RuntimeError("Perth incomplet. Installez setuptools==80.9.0 dans l'environnement isolé, puis relancez ce programme.")
    from huggingface_hub import model_info, snapshot_download
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    from importlib.metadata import version

    if version("chatterbox-tts") != "0.1.7":
        raise RuntimeError("Ce notebook nécessite chatterbox-tts 0.1.7 dans son environnement isolé.")
    if device == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("GPU absent. Sélectionnez votre session L4 existante, sans souscrire d'offre supplémentaire.")
        free, _ = torch.cuda.mem_get_info()
        if free < 6 * 1024**3:
            raise RuntimeError("Moins de 6 Go de VRAM libres. Arrêtez les anciens calculs avant l'essai.")
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=False)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if device == "cuda":
        torch.cuda.manual_seed_all(seed)
    started = time.perf_counter()
    revision = model_info(MODEL_ID, token=False).sha
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise RuntimeError("Révision officielle du modèle introuvable.")
    print("Téléchargement du modèle officiel, révision :", revision, flush=True)
    checkpoint = Path(snapshot_download(repo_id=MODEL_ID, revision=revision,
                                        allow_patterns=MODEL_FILES, token=False))
    required = set(MODEL_FILES) - {"Cangjie5_TC.json"}
    if any(not (checkpoint / name).is_file() for name in required):
        raise RuntimeError("Fichiers du modèle incomplets, y compris la voix fournie par le modèle.")
    print("Chargement de Chatterbox Multilingual V2...", flush=True)
    model = ChatterboxMultilingualTTS.from_local(checkpoint, device=device)
    checks = phoneme_checks(model.tokenizer)
    if not all(check["distinct_tokens"] for check in checks):
        raise RuntimeError("Ce tokenizer ne distingue pas tous les signes testés. Ne pas retenir cet essai pour l'arabe vocalisé.")
    loaded = time.perf_counter()
    print("Synthèse en arabe, avec la voix par défaut, sans audio de référence...", flush=True)
    # cfg_weight=0 suit la recommandation du mainteneur pour limiter le transfert
    # d'accent depuis une voix de référence d'une autre langue. Résultat à écouter.
    with torch.inference_mode():
        waveform = model.generate(text, language_id="ar", exaggeration=0.5,
                                  cfg_weight=0.0, temperature=0.8)
    if device == "cuda":
        torch.cuda.synchronize()
    finished = time.perf_counter()
    samples = waveform.detach().cpu().float().numpy().squeeze()
    if samples.ndim != 1 or not samples.size or not np.isfinite(samples).all() or not np.max(np.abs(samples)):
        raise RuntimeError("Résultat audio vide ou invalide.")
    output = folder / "essai-chatterbox-ar.wav"
    sf.write(str(output), samples, model.sr, subtype="PCM_16")
    report = {
        "model_id": MODEL_ID, "model_revision": revision, "variant": "Multilingual V2",
        "engine": "chatterbox-tts 0.1.7", "torch_version": torch.__version__,
        "device": device, "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None,
        "language": "ar", "text": text, "automatic_vowelizer": None,
        "voice": "Conditionnement fourni avec le modèle ; aucun audio personnel de référence.",
        "seed": seed, "exaggeration": 0.5, "cfg_weight": 0.0, "temperature": 0.8,
        "sample_rate": model.sr, "duration_sec": len(samples) / model.sr,
        "load_sec_including_download": round(loaded-started, 3),
        "generation_sec": round(finished-loaded, 3), "token_checks": checks,
        "model_sha256_observed": {name: digest(checkpoint / name) for name in sorted(required)},
        "audio_sha256": digest(output), "watermark": "Filigrane natif Chatterbox conservé.",
        "quality": "Naturel, accent, harakat, mots omis ou répétés à vérifier à l'écoute. Aucune diction parfaite garantie.",
    }
    output.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Audio produit :", output, flush=True)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--text-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    args = parser.parse_args()
    generate(args.text_file.read_text(encoding="utf-8"), args.output_dir, device=args.device)
