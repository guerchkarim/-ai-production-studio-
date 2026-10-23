"""Rangement des WAV et JSON par profil/variante, indépendant des moteurs."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import shutil
import uuid
import zipfile


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save_voice(root, reference_dir, audition=None):
    root, reference_dir = Path(root), Path(reference_dir)
    voice = json.loads((reference_dir / "voix.json").read_text(encoding="utf-8"))
    profile, variant = voice.get("profile_id"), voice.get("variant")
    if not isinstance(profile, str) or not re.fullmatch(r"[FM]-(?:petit|enfant|ado|20|30|40|50|senior)", profile):
        raise ValueError("Profil vocal invalide.")
    if isinstance(variant, bool) or not isinstance(variant, int) or not 1 <= variant <= 99:
        raise ValueError("Variante invalide.")
    reference = reference_dir / "reference.wav"
    sha = digest(reference)
    if sha != voice.get("reference_sha256"):
        raise ValueError("Référence modifiée : sauvegarde arrêtée.")
    report = None
    if audition is not None:
        audition = Path(audition)
        report = json.loads(audition.with_suffix(".json").read_text(encoding="utf-8"))
        if report.get("reference_sha256") != sha or report.get("language") not in ("ar", "fr"):
            raise ValueError("La réplique ne correspond pas à cette voix.")
        if digest(audition) != report.get("audio_sha256"):
            raise ValueError("Réplique modifiée : sauvegarde arrêtée.")
    prefix = profile + "_var" + str(variant)
    folder = root / (prefix + "_" + sha[:12])
    folder.mkdir(parents=True, exist_ok=True)
    saved_reference = folder / (prefix + "_reference.wav")
    if saved_reference.exists():
        if digest(saved_reference) != sha:
            raise ValueError("Une référence différente existe déjà dans ce dossier.")
    else:
        shutil.copy2(reference, saved_reference)
    # Cette fiche reflète la dernière révision/les auditions ; les WAV restent immuables.
    (folder / (prefix + "_reference.json")).write_text(json.dumps(voice, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    with zipfile.ZipFile(folder / "voix-fictive.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.write(saved_reference, "reference.wav")
        z.writestr("voix.json", json.dumps(voice, ensure_ascii=False, indent=2))
    saved_audition = None
    if report is not None:
        base = prefix + "_" + report["language"].upper()
        take = 1
        while True:
            destination = folder / (base + "_prise" + str(take).zfill(2) + ".wav")
            metadata = destination.with_suffix(".json")
            if not destination.exists() and not metadata.exists():
                shutil.copy2(audition, destination)
                metadata.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
                break
            if destination.is_file() and metadata.is_file() and digest(destination) == report["audio_sha256"]:
                if json.loads(metadata.read_text(encoding="utf-8")) == report:
                    break
            take += 1
        saved_audition = destination
    # Inventaire du dossier persistant ; ne pas déclarer une voix validée à l'écoute.
    entries = []
    for voice_folder in sorted(root.iterdir()):
        if not voice_folder.is_dir():
            continue
        manifests = list(voice_folder.glob("*_reference.json"))
        if len(manifests) != 1:
            continue
        info = json.loads(manifests[0].read_text(encoding="utf-8"))
        entries.append({"profile": info.get("profile_id"), "variant": info.get("variant"),
            "reference_sha256": info.get("reference_sha256"), "folder": voice_folder.name,
            "label": info.get("label"), "status": "Créée ; validation d'écoute à conserver séparément",
            "files": [p.name for p in sorted(voice_folder.iterdir()) if p.is_file()]})
    catalogue = {"schema_version": 1, "voices_count": len(entries), "entries": entries}
    temporary = root / (".catalogue-" + uuid.uuid4().hex + ".json")
    temporary.write_text(json.dumps(catalogue, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    temporary.replace(root / "catalogue_voix.json")
    # Un fichier ZIP téléchargeable conserve exactement la même arborescence.
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    archive = root / (prefix + "_" + stamp + ".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(folder.iterdir()):
            if path.is_file():
                z.write(path, folder.name + "/" + path.name)
    return folder, archive, saved_audition
