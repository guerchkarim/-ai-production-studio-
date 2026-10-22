"""Contrats de conservation des voix, sans GPU ni dépendances de synthèse."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import wave
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts/colab" / filename)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


casting = module("casting", "casting_voix.py")
chatterbox = module("audition", "essai_voix_chatterbox_ar.py")


def wav_bytes():
    stream = io.BytesIO()
    with wave.open(stream, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"\x00\x00" * 24000 * 4)
    return stream.getvalue()


class VoiceCastingTest(unittest.TestCase):
    def package(self, directory, audio=None, checksum=None, extra=None):
        audio = wav_bytes() if audio is None else audio
        doc = {"schema_version": 1, "source_type": "fictional_voice_design", "label": "Enfant fictif",
               "reference_sha256": checksum or hashlib.sha256(audio).hexdigest(),
               "chatterbox_revision": "a" * 40, "auditions": {"ar": {"status": "À écouter"}}}
        archive = Path(directory) / "voice.zip"
        with zipfile.ZipFile(archive, "w") as z:
            z.writestr("reference.wav", audio)
            z.writestr("voix.json", json.dumps(doc))
            if extra:
                z.writestr(extra, b"unexpected")
        return archive, doc, audio

    def test_roundtrip_preserves_reference_revision_and_audition_state(self):
        with tempfile.TemporaryDirectory() as d:
            archive, doc, audio = self.package(d)
            path = casting.restore_reference(archive, Path(d) / "restored")
            self.assertEqual(path.read_bytes(), audio)
            self.assertEqual(json.loads(path.with_name("voix.json").read_text()), doc)

    def test_corruption_and_fake_wav_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as d:
            archive, _, _ = self.package(d, checksum="0" * 64)
            with self.assertRaises(ValueError):
                casting.restore_reference(archive, Path(d) / "restored")
            self.assertFalse((Path(d) / "restored").exists())
            archive, _, _ = self.package(d, audio=b"not an audio file")
            with self.assertRaises(ValueError):
                casting.restore_reference(archive, Path(d) / "restored")

    def test_unexpected_paths_and_existing_reference_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            archive, _, _ = self.package(d, extra="../escaped")
            with self.assertRaises(ValueError):
                casting.restore_reference(archive, Path(d) / "restored")
            self.assertFalse((Path(d) / "escaped").exists())
            archive, _, _ = self.package(d)
            path = casting.restore_reference(archive, Path(d) / "restored")
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                casting.restore_reference(archive, path.parent)
            self.assertEqual(path.read_bytes(), before)

    def test_language_validation_preserves_supplied_vowels(self):
        text = "عَلِمَ الطَّالِبُ. عُلِمَ الْخَبَرُ."
        self.assertEqual(chatterbox.validate_text(text, "ar"), text)
        self.assertEqual(chatterbox.validate_text("Une très belle journée.", "fr"), "Une très belle journée.")
        for text, language in [("مرحبا", "ar"), ("Hello", "de")]:
            with self.assertRaises(ValueError):
                chatterbox.validate_text(text, language)

    def test_catalogue_marks_targets_as_uncreated(self):
        profiles = casting.profiles()
        self.assertEqual(len({p["id"] for p in profiles}), 16)
        for p in profiles:
            self.assertIsNone(p["reference_sha256"])
            self.assertEqual(p["status"], "À créer et auditionner")
            self.assertEqual(p["languages_to_audition"], ["fr", "ar"])


if __name__ == "__main__":
    unittest.main()
