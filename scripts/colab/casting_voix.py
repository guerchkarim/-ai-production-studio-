"""Création de références fictives par description ; un candidat à la fois."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import time
import zipfile

MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign"
REFERENCE_TEXT = "Bonjour. Une nouvelle histoire commence. Aujourd’hui, nous allons découvrir un endroit merveilleux, et partager cette aventure ensemble."
AGE_GROUPS = [
    ("petit", "Petite enfance · environ 5 ans", "a young child, around five years old, with light natural articulation"),
    ("enfant", "Enfant · environ 10 ans", "a child, around ten years old, with clear lively articulation"),
    ("ado", "Adolescent · environ 15 ans", "a teenager, around fifteen years old, with a natural youthful timbre"),
    ("20", "Jeune adulte · environ 20 ans", "a young adult, around twenty years old"),
    ("30", "Adulte · environ 30 ans", "an adult, around thirty years old"),
    ("40", "Adulte · environ 40 ans", "an adult, around forty years old"),
    ("50", "Adulte · environ 50 ans", "an adult, around fifty years old"),
    ("senior", "Senior · environ 70 ans", "an elderly adult, around seventy years old, with a gently aged timbre and clear diction"),
]


def profiles():
    return [{"id": sex+"-"+key, "label": label+" · "+age,
             "age_target": age, "gender_target": label, "languages_to_audition": ["fr", "ar"],
             "status": "À créer et auditionner", "reference_sha256": None,
             "instruction": "A fictional "+gender+" voice of "+description+
             ". Speak French naturally, with clear pronunciation, a calm friendly tone, and normal conversational pace. Dry close-microphone recording, no music, no background noise. Avoid caricature or exaggerated pitch."}
            for sex, label, gender in [("F", "Féminine", "female"), ("M", "Masculine", "male")]
            for key, age, description in AGE_GROUPS]


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def design(profile_id, directory, variant=1):
    candidates = {p["id"]: p for p in profiles()}
    if profile_id not in candidates or isinstance(variant, bool) or not isinstance(variant, int) or not 1 <= variant <= 99:
        raise ValueError("Choisissez un profil du casting et une variante entre 1 et 99.")
    import numpy as np
    import torch
    import soundfile as sf
    from qwen_tts import Qwen3TTSModel
    from huggingface_hub import model_info, snapshot_download
    if not torch.cuda.is_available():
        raise RuntimeError("Choisissez votre session L4 existante pour cet essai.")
    free, _ = torch.cuda.mem_get_info()
    if free < 10 * 1024**3:
        raise RuntimeError("Moins de 10 Go de VRAM libres. Arrêtez les autres calculs avant cet essai.")
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=False)
    seed = 4200 + variant
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    started = time.perf_counter()
    revision = model_info(MODEL_ID, token=False).sha
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise RuntimeError("Révision officielle Qwen introuvable.")
    checkpoint = Path(snapshot_download(MODEL_ID, revision=revision, token=False,
        allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "*.tiktoken"]))
    model = Qwen3TTSModel.from_pretrained(str(checkpoint), device_map="cuda:0",
        dtype=torch.bfloat16, attn_implementation="sdpa", use_safetensors=True,
        local_files_only=True)
    profile = candidates[profile_id]
    print("Création d'un candidat :", profile["label"], "variante", variant, flush=True)
    with torch.inference_mode():
        waves, rate = model.generate_voice_design(text=REFERENCE_TEXT, language="French",
            instruct=profile["instruction"], max_new_tokens=256)
    torch.cuda.synchronize()
    audio = np.asarray(waves[0], dtype=np.float32).squeeze()
    if audio.ndim != 1 or not audio.size or not np.isfinite(audio).all() or not np.max(np.abs(audio)):
        raise RuntimeError("La référence produite est vide ou invalide.")
    duration = len(audio) / rate
    if not 3 <= duration <= 20:
        raise RuntimeError("Durée de référence hors plage 3–20 s : " + str(round(duration, 1)))
    reference = folder / "reference.wav"
    sf.write(str(reference), audio, rate, subtype="PCM_16")
    report = {"schema_version": 1, "source_type": "fictional_voice_design",
        "profile_id": profile_id, "label": profile["label"], "variant": variant,
        "age_target": profile["age_target"], "gender_target": profile["gender_target"],
        "instruction": profile["instruction"], "reference_text": REFERENCE_TEXT,
        "reference_language": "fr", "reference_sha256": digest(reference),
        "reference_duration_sec": duration, "model_id": MODEL_ID, "model_revision": revision,
        "seed": seed, "dtype": "bfloat16", "attention": "sdpa", "max_new_tokens": 256,
        "total_sec_including_download": round(time.perf_counter()-started, 3),
        "audition_status": {"reference": "À écouter", "fr": "Non auditionnée", "ar": "Non auditionnée"},
        "limits": "Âge/timbre demandés, pas garantis. Identité, accent et diction à approuver dans chaque langue.",
        "model_sha256_observed": {str(p.relative_to(checkpoint)): digest(p) for p in checkpoint.rglob("*.safetensors")}}
    manifest = folder / "voix.json"
    manifest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    archive = folder / "voix-fictive.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(reference, "reference.wav")
        z.write(manifest, "voix.json")
    print("Référence à écouter :", reference, flush=True)
    return reference


def restore_reference(archive, directory):
    """Restaure seulement une référence de ce casting, sans extraire de chemins fournis."""
    archive = Path(archive)
    if archive.stat().st_size > 12 * 1024**2:
        raise ValueError("Archive de voix : 12 Mo maximum.")
    with zipfile.ZipFile(archive) as z:
        entries = z.infolist()
        if len(entries) != 2 or set(z.namelist()) != {"voix.json", "reference.wav"}:
            raise ValueError("Archive de référence invalide.")
        if sum(e.file_size for e in entries) > 12 * 1024**2 or z.getinfo("voix.json").file_size > 100000:
            raise ValueError("Archive de voix trop volumineuse.")
        report = json.loads(z.read("voix.json"))
        audio = z.read("reference.wav")
    if report.get("schema_version") != 1 or report.get("source_type") != "fictional_voice_design":
        raise ValueError("Ce casting attend une référence fictive créée par le notebook.")
    if hashlib.sha256(audio).hexdigest() != report.get("reference_sha256"):
        raise ValueError("Empreinte de la référence incorrecte.")
    if not (audio.startswith(b"RIFF") and audio[8:12] == b"WAVE"):
        raise ValueError("La référence n'est pas un fichier WAV.")
    folder = Path(directory)
    folder.mkdir(parents=True, exist_ok=False)
    reference = folder / "reference.wav"
    reference.write_bytes(audio)
    (folder / "voix.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return reference


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=[p["id"] for p in profiles()], required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--variant", type=int, default=1)
    args = parser.parse_args()
    design(args.profile, args.output_dir, args.variant)
